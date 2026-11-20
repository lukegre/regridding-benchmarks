#!/usr/bin/env bash
# Run a benchmark profile and commit the JSON run bundle to the `results` branch.
# Also pushes a compact summary (docs/data) to main; remote override BENCH_MAIN_REMOTE.
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
# The edition page links to results/<run-id>/ beside it, so it is stored next to the bundle.
report_ok=0
regridding-benchmarks build-report "$out/$run_id" --output-dir "$scratch/site" --repo "$repo" && report_ok=1 \
  || echo "build-report failed; committing the bundle without a page" >&2

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
[[ "$report_ok" == 1 ]] && cp "$scratch/site/editions/$run_id.html" "$push/results/$run_id.html"
# Push with the token for https remotes (never printed); local remotes need none.
# usage: push_branch <clone-dir> <remote-url> <ref> <exit-code-on-missing-token> <exit-code-on-failure>
push_branch() {
  local dir=$1 url=$2 ref=$3 no_token=$4 fail=$5
  if [[ "$url" == https://* ]]; then
    [[ -n "$token_file" && -r "$token_file" ]] || { echo "No GitHub token (looked for /secrets/github, /secrets/github_token); $ref committed locally only: $dir" >&2; return "$no_token"; }
    local askpass="$scratch/askpass.sh"
    printf '#!/bin/sh\ncase "$1" in Username*) echo x-access-token;; *) cat "%s";; esac\n' "$token_file" > "$askpass"
    chmod 700 "$askpass"
    GIT_ASKPASS="$askpass" GIT_TERMINAL_PROMPT=0 git -C "$dir" push --quiet origin "$ref" || { rm -f "$askpass"; return "$fail"; }
    rm -f "$askpass"
  else
    git -C "$dir" push --quiet origin "$ref" || return "$fail"
  fi
}
commit_as_job() { git -C "$1" -c user.name="renku-benchmark-job" -c user.email="noreply@renkulab.io" commit --quiet -m "$2"; }

git -C "$push" add results
if git -C "$push" diff --cached --quiet; then
  echo "Nothing to commit on $branch"
else
  commit_as_job "$push" "Add benchmark results $run_id (profile $profile, exit status $status)"
  push_branch "$push" "$remote" "$branch" 3 4 || exit $?
  echo "Pushed results/$run_id to $branch"
fi

# Compact JSON summary for the results page: docs/data on main (a push there rebuilds Pages).
main_remote=${BENCH_MAIN_REMOTE:-$remote}
main_branch=${BENCH_MAIN_BRANCH:-main}
mainclone="$scratch/main-push"
rm -rf "$mainclone"
git clone --quiet --depth 1 --branch "$main_branch" "$main_remote" "$mainclone" || exit 5
python -m regridding_benchmarks.summary "$out/$run_id" "$mainclone/docs/data" || exit 5
git -C "$mainclone" add docs/data/runs/"$run_id".json docs/data/index.json
if git -C "$mainclone" diff --cached --quiet; then
  echo "No data changes for $main_branch"
else
  commit_as_job "$mainclone" "Add benchmark summary $run_id (profile $profile)"
  # A concurrent push to main must not fail the job: rebase onto it and retry once.
  for attempt in 1 2 3; do
    git -C "$mainclone" fetch --quiet origin "$main_branch" && git -C "$mainclone" -c user.name="renku-benchmark-job" -c user.email="noreply@renkulab.io" rebase --quiet "origin/$main_branch" || exit 5
    push_branch "$mainclone" "$main_remote" "HEAD:$main_branch" 5 6 && break
    [[ "$attempt" == 3 ]] && exit 6
  done
  echo "Pushed docs/data/runs/$run_id.json and index.json to $main_branch"
fi
[[ "$status" -eq 0 ]] && touch "$done_marker"
exit "$status"
