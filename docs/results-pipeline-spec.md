# Spec: Renku standard job → JSON results → self-aggregating web page

Status: ready to implement. Nothing below is built yet. Written 2026-11-20. This brief is self-contained: read it, then `CLAUDE.md`, then start.

## 1. Problem

Benchmark results exist but are invisible on the website, and the website cannot update itself.

- A Renku job ("Benchmark job (standard)", launcher `01M7WQEWQXJNMT16VREM7DSNEW`, project `gregorl/regridding-benchmarks`, id `01M7TAYV0E27TT6DWN75BN0DQ3`) runs the standard profile. `deploy/renku/job_commit.sh` then pushes the run bundle to the `results` branch as `results/<run-id>/` (`manifest.json`, `checksums.json`, `samples/*.json`, `logs/`) and a generated `results/<run-id>.html` edition page.
- GitHub Pages serves `main` → `/docs`, which is still the legacy edition. No page reads the Renku runs, and GitHub shows the `results/*.html` files as source, not rendered.
- The generated edition page is rendered in Python per run, so it cannot compare runs or aggregate across them.
- The `results` branch holds 8 smoke and 5 standard bundles. Most are duplicates from a container-restart loop that is now fixed. The reference run is `renku-standard-20261120T155209Z`: 72 samples, 57 `ok`, 3 `expected_rejection`, 12 `unavailable`.
- These runs are not publishable editions (unpinned Python environment on the build image, no image digest, not the designated native-Linux resource). The page must say so.

## 2. Goal

1. Run the standard profile as a Renku job.
2. The job writes compact JSON into `docs/data/` on `main` (decided: same-origin for the page, no CORS question; each push triggers a Pages rebuild). It also keeps pushing the full bundle to the `results` branch as now.
3. A static page in `docs/` fetches that JSON in the browser and does all aggregation in JavaScript. A new run appears without regenerating any HTML.

## 3. Data contract

Source data, do not change. Sample file `samples/<case_id>.<NNNN>.json`: `case_id`, `repeat`, `sample_id`, `started_at`, `finished_at`, `geometry`, and `result` = `{status, reason, timings: {<phase>: seconds}, metrics: {...}, resources: {worker_peak_rss_bytes, child_peak_rss_bytes}}`. Statuses: `ok`, `expected_rejection`, `unsupported`, `unavailable`, `timeout`, `crash`, `failed_validation`. `manifest.json`: `run_id`, `profile`, `repeats`, `series`, `state`, `started_at`, `finished_at`, `publishable_profile`, `full_profile`, `source.commit`, `environment` (`executables`, `interpreters`, `image_digest`, `resources`, …), and `cases[]` with `id`, `family`, `method`, `quantity`, `expected`. Families seen: `adversarial`, `storage`, `published_workloads`, `chunked`, `common-support`, `shared-grid`. Timing phases seen: `application`, `apply`, `fixture`, `imports`, `io_prepare`, `load`, `output_read`, `scipy_application`, `setup`, `xarray_application`.

New files (paths relative to `docs/data/`):

- `runs/<run-id>.json`:
  ```json
  {"schema": 1, "run_id": "...", "profile": "standard", "series": "renkulab",
   "started_at": "...", "finished_at": "...", "repeats": 3, "publishable": false,
   "source_commit": "...", "engines": {"cdo": "2.6.5", "numpy": "..."},
   "samples": [{"case_id": "...", "family": "...", "method": "...", "quantity": "...",
                "repeat": 1, "status": "ok", "expected": true, "reason": null,
                "timings": {"apply": 0.0029}, "metrics": {"coverage": 1.0},
                "resources": {"worker_peak_rss_bytes": 105840640}}]}
  ```
  `publishable` is always `false` for runs from this job. `expected` is whether the status is in the case's `expected` list. In `metrics`, keep only scalar entries (number, bool, short string) so one sample stays small; drop nested objects and arrays (some raw results reach 13 KB). `engines` comes from `environment.executables` versions plus a short list of package versions (numpy, scipy, xarray, dask, xesmf, esmpy, xarray-regrid, pyresample, pyinterp, healpy, xdggs). Target well under 500 KB per standard run.
- `index.json`: `{"updated_at": "...", "runs": [{"run_id", "profile", "series", "started_at", "n_samples", "status_counts": {"ok": 57, ...}, "file": "runs/<run-id>.json"}]}`, newest first. Writing an entry for an existing `run_id` replaces it.

## 4. Tasks

### A. Summarizer (Python, in `src/regridding_benchmarks/`)
- New module (for example `summary.py`) with a function that turns a validated bundle directory into the `runs/<run-id>.json` structure, and one that adds or replaces its entry in `index.json`. A `python -m regridding_benchmarks.summary <bundle> <data-dir>` entry point is enough; a new CLI subcommand is optional.
- Unit tests in `tests/` using the `unittest` runner, built from a small synthetic bundle (do not depend on the real bundles). Cover: status counts, scalar-only metrics, `expected` flag, replacing an existing index entry, newest-first order.

### B. Job script (`deploy/renku/job_commit.sh`)
- After validate and build-report, call the summarizer, then push `docs/data/runs/<run-id>.json` and `docs/data/index.json` to `main` in addition to the `results` branch push. Fetch and rebase before pushing so a concurrent push does not fail the job. Keep: done-marker (Renku restarts the container after a clean exit), token lookup (`/secrets/github`, then `/secrets/github_token`), neutral commit identity (`renku-benchmark-job <noreply@renkulab.io>`), committing even after a failed step.
- The local-remote test pattern in the earlier tests of this script is the model: run it against a local bare remote with `BENCH_REPO`, `BENCH_RESULTS_REMOTE`, `BENCH_SCRATCH_DIR`, `BENCH_DONE_MARKER`, `BENCH_RUN_ID` set. The data-to-main push needs its own remote override (for example `BENCH_MAIN_REMOTE`) so it is testable offline.

### C. Web page (`docs/renku-results.html` + `docs/renku-results.js`)
- Static, no build step, no framework. Linked from `docs/index.html`. Match the existing site style. Layout must work at phone width.
- Fetch `data/index.json`, then the run files (relative URLs). JavaScript aggregates: per case and timing phase, median and min/max across repeats; status counts per run and per family; filters by profile, family, method and status; list `unavailable` cases with their reasons. Optional second step: compare two runs side by side.
- A banner states: results come from Renku jobs on an unpinned environment and are not publishable editions.
- Must work with zero, one, or many runs, handle fetch errors with a visible message, and not touch the legacy pages.

### D. Backfill and run
- Generate `docs/data/` for the existing bundles, listing only the latest bundle per profile in the index (older duplicates stay in `results` branch history, unlisted). Bundles are on the `results` branch.
- Start the standard job, wait for it, and confirm the new run appears in `index.json` and on the page.

## 5. Acceptance criteria

1. Tests pass: `uv sync --group tiny` then `uv run python -m unittest discover -s tests`.
2. `job_commit.sh` against local bare remotes writes `runs/<id>.json` and an updated `index.json`; a second run adds a second entry and keeps the first.
3. The page's counts for `renku-standard-20261120T155209Z` match a direct count of its `samples/*.json` (72 / 57 / 3 / 12).
4. Adding a run to `index.json` makes it appear with no HTML or JS change.
5. A Renku standard job finishes, pushes to `main` and `results`, exits 0, and does not rerun the benchmark after restart.
6. The page renders correctly in a browser at desktop and phone width, with zero and with multiple runs.
7. Legacy pages in `docs/` are unchanged.

## 6. Repo conventions and environment facts

- Use **uv**: `uv sync --group tiny`, `uv run …`. Python 3.12 locks only (`uv.lock`); the package itself installs on 3.11. Renku's build image runs unpinned Python 3.11.
- Keep it simple: readable over clever, no extra frameworks.
- Do not edit `benchmarks/legacy/archive/` (hash-pinned). The archive's `.log` files are tracked on purpose; `.gitignore` carries `!benchmarks/legacy/archive/**/*.log`.
- Git identity: commit as `lukegre <lukegre@gmail.com>` locally (already configured) and as `renku-benchmark-job <noreply@renkulab.io>` in the job. Do not use or write the user's work email anywhere in commits, files or output.
- The sandbox blocks some network and the macOS keychain. `gh` only works outside the sandbox; use `UV_CACHE_DIR=$TMPDIR/uvc` for uv; PyPI needs `pypi.org` and `files.pythonhosted.org` allowed.
- GitHub Pages serves `main` → `/docs`; every push to `main` rebuilds it.

### Renku facts (project `gregorl/regridding-benchmarks`)
- Launchers: JupyterLab (interactive, build-from-code) `01M7TAZ48ANR2QXA0JRVHS5R0F`; "Benchmark job (smoke)" `01M7WF5DBVTCKRHMN2DQR2C12A`; "Benchmark job (standard)" `01M7WQEWQXJNMT16VREM7DSNEW`. The job launchers use `ghcr.io/lukegre/regridding-benchmarks:sha-b991e2f681c2464c73937305bcfbf9dea1a97064` (public), which has CDO 2.6.5, ESMF/esmpy/xESMF and the DGGS stack. Class `large` (1.75 CPU, 7 GB).
- Use the skill helper `python3 ~/.claude/skills/renku/scripts/renku_agent.py` (auth is stored; `renkulab.io` must be an allowed domain). `job run --launcher <id>` starts a job, `session get/logs <name>` inspects it, `session delete <name> --yes` removes it.
- Renku reuses one job name per launcher. Delete the finished job before rerunning, and delete it when it completes, since Renku restarts the container. A job launched earlier does not pick up script fixes made after its checkout.
- The GitHub push token is a Renku project secret mounted at `/secrets/github`. Never print or log it.
- Code is checked out at job start from `main`, so push script changes to `main` before starting the job.

## 7. Out of scope

Publishing an official edition (needs image digest, designated native-Linux resource, publication cutover in `docs/deployment.md`); making ERA5 or ICON cases runnable (the 12 `unavailable` standard samples are data gaps); pruning the `results` branch duplicates (ask the user first).
