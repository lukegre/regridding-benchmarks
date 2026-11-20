#!/usr/bin/env bash
# Run a benchmark profile and commit the JSON run bundle to the `results` branch.
# Meant for a Renku job on the build-from-code image; unlike job.sh it does not need a pinned image.
# GitHub push token: Renku project secret file, $BENCH_GITHUB_TOKEN_FILE or /secrets/github or /secrets/github_token.
set -uo pipefail

repo=${BENCH_REPO:-/home/renku/work/regridding-benchmarks}
profile=${BENCH_PROFILE:-smoke}
run_id=${BENCH_RUN_ID:-renku-$profile-$(date -u +%Y%m%dT%H%M%SZ)}
branch=${BENCH_RESULTS_BRANCH:-results}
scratch=${BENCH_SCRATCH_DIR:-$HOME/scratch}
token_file=${BENCH_GITHUB_TOKEN_FILE:-}
if [[ -z "$token_file" ]]; then
  for f in /secrets/github /secrets/github_token; do [[ -r "$f" ]] && token_file=$f && break; done
fi
remote=${BENCH_RESULTS_REMOTE:-$(git -C "$repo" remote get-url origin)}
# Renku restarts the container after a clean exit; the pod volume survives, so a marker stops reruns.
done_marker=${BENCH_DONE_MARKER:-$(dirname "$repo")/.benchmark-done-$profile}
[[ -e "$done_marker" ]] && { echo "Already completed in this pod ($done_marker); delete the job to rerun."; exit 0; }
out="$scratch/runs"
mkdir -p "$out" "$scratch/cache"
export TMPDIR="$scratch"

if [[ -n "${BENCH_ENV_ROOT:-}" ]]; then
  # Benchmark image: engines and interpreters are preinstalled; run the checkout's code.
  export PYTHONPATH="$repo/src${PYTHONPATH:+:$PYTHONPATH}"
else
  # Build-from-code image: install the package into a venv that reuses its numpy/scipy/xarray.
  uv venv --quiet --system-site-packages "$scratch/venv"
  uv pip install --quiet --python "$scratch/venv/bin/python" -e "$repo"
  export PATH="$scratch/venv/bin:$PATH"
fi

status=0
regridding-benchmarks fetch --profile "$profile" --cache-dir "$scratch/cache" --repo "$repo" || status=$?
regridding-benchmarks run --profile "$profile" --output-dir "$out" --run-id "$run_id" \
  --cache-dir "$scratch/cache" --scratch-dir "$scratch/work" --series "${BENCH_SERIES:-renkulab}" --repo "$repo" || status=$?
regridding-benchmarks validate-bundle "$out/$run_id" || status=$?

# Save whatever was produced, even after a failure, so the evidence is not lost.
[[ -d "$out/$run_id" ]] || { echo "No bundle produced" >&2; exit "${status:-1}"; }
push="$scratch/push"
rm -rf "$push"
if ! git clone --quiet --depth 1 --branch "$branch" "$remote" "$push" 2>/dev/null; then
  git clone --quiet --depth 1 "$remote" "$push"
  git -C "$push" checkout --quiet --orphan "$branch"
  git -C "$push" rm -rfq . 2>/dev/null || true
fi
mkdir -p "$push/results"
rm -rf "$push/results/$run_id"
cp -R "$out/$run_id" "$push/results/$run_id"
git -C "$push" add results
if git -C "$push" diff --cached --quiet; then
  echo "Nothing to commit"; [[ "$status" -eq 0 ]] && touch "$done_marker"; exit "$status"
fi
git -C "$push" -c user.name="renku-benchmark-job" -c user.email="noreply@renkulab.io" \
  commit --quiet -m "Add benchmark results $run_id (profile $profile, exit status $status)"

if [[ "$remote" == https://* ]]; then
  [[ -n "$token_file" && -r "$token_file" ]] || { echo "No GitHub token (looked for /secrets/github, /secrets/github_token); results committed locally only: $push" >&2; exit 3; }
  askpass="$scratch/askpass.sh"
  printf '#!/bin/sh\ncase "$1" in Username*) echo x-access-token;; *) cat "%s";; esac\n' "$token_file" > "$askpass"
  chmod 700 "$askpass"
  GIT_ASKPASS="$askpass" GIT_TERMINAL_PROMPT=0 git -C "$push" push --quiet origin "$branch" || { rm -f "$askpass"; exit 4; }
  rm -f "$askpass"
else
  git -C "$push" push --quiet origin "$branch"
fi
echo "Pushed results/$run_id to $branch"
[[ "$status" -eq 0 ]] && touch "$done_marker"
exit "$status"
