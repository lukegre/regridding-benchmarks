# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Reproducible benchmarks for geospatial regridding/remapping tools (xESMF, CDO, xarray-regrid, SciPy, pyresample, DGGS libraries, etc.). A registry of versioned cases is executed in isolated worker processes, producing validated run bundles that are rendered into a static report site. See `docs/reproduction.md` and `docs/deployment.md` for the full procedures.

## Commands

Use **uv** for package management and for running everything (prefix commands with `uv run`; don't call `pip` directly).

```sh
uv venv                                         # creates .venv (gitignored)
uv pip install -e .                             # CLI works without scientific engines
uv pip install -r requirements-python.lock      # pinned engines for numerical cases
uv run python -m unittest discover -s tests     # offline tests (what CI runs)
uv run python -m unittest tests.test_runner     # one test module
uv run python -m unittest tests.test_runner.ClassName.test_name   # one test

uv run regridding-benchmarks list-cases --profile smoke
uv run regridding-benchmarks fetch --profile smoke
uv run regridding-benchmarks run --profile smoke --case <CASE_ID> --run-id local --output-dir <dir>   # --case repeatable; --resume continues
uv run regridding-benchmarks validate-bundle <dir>/local          # --publication, --check-roster for stricter checks
uv run regridding-benchmarks build-report <dir>/local --output-dir <site>   # --legacy-edition <dir> adds the legacy evidence
uv run regridding-benchmarks import-legacy --output-dir <dir>
```

No linter is configured. CI (`.github/workflows/checks.yml`) runs the unit tests, then an end-to-end smoke run → validate → build-report, plus a "tiny-adapters" job that installs only numpy/scipy/xarray/dask/netcdf4/xarray-regrid from `requirements-python.lock` and runs `tests/test_legacy_parity.py` and four analytic smoke cases. Many cases need engines not installed locally; those report `unavailable` rather than failing.

## Architecture

Pipeline: **registry → runner → worker → bundle → report**.

- `benchmarks/*.json` (cases, plus `profiles.json` defining smoke/standard/extended repeats and publishability) and `datasets/*.json` (checksum-pinned external inputs) are loaded and validated by `registry.py`. `benchmarks/legacy/archive/` is excluded from discovery. Each case names an `adapter` as `module:function`; bump the case `version` when its fixture, protocol or validation changes.
- `runner.py` executes samples serially and resumably. Each sample runs in a subprocess via `worker.py`, which imports the case's adapter and calls `adapter(case, context)`, writing a JSON response. Adapters (`legacy_adapter`, `workloads`, `era5`, `mur_tiles`, `dask_conservative`, `pyinterp_case`, …) return `{status, timings, metrics, reason}`. Statuses are the `OUTCOMES` set in `registry.py` (`ok`, `expected_rejection`, `unsupported`, `unavailable`, `timeout`, `crash`, `failed_validation`); a missing optional engine or unverifiable input is `unavailable`, not a failure.
- A run bundle is `manifest.json` (roster, environment, fingerprint), `samples/`, `logs/`, `checksums.json`. `bundle.py` validates integrity, roster, and (with `--publication`) provenance/completeness. `provenance.py` records source revision, interpreter/lock digests, image digest, resource limits.
- `report.py` renders the static site from validated bundles; `legacy.py` verifies and exports the original edition.
- Multiple Python environments are used: the main interpreter plus `BENCH_PYTHON`, `BENCH_COMPILED_PYTHON`, `BENCH_XHEALPIXIFY_PYTHON`, and `BENCH_ENV_ROOT` (compiled CDO/xESMF under `compiled/bin`) — see `provenance.py` and `legacy_adapter.py`. Locks: `requirements-python.lock`, `requirements-compiled*.lock`, `environments/*.lock`.

## Legacy edition and published site

- `benchmarks/legacy/archive/` holds the original runners, raw results and reports. Adapters reuse its kernels but must not modify it; its scripts rewrite recorded outputs, so run them only from a separate checkout of `e4a4d263877433859d14dd6c6d91924127dbd54c`. Its manifests pin SHA-256 hashes — don't edit archived files.
- `docs/` is the currently served GitHub Pages site (`main` → `/docs`) and keeps legacy URLs. Cutover to the bundle-based publication workflow (`.github/workflows/publish.yml`, `deploy/publication/snapshot.py`) is staged and not yet done.
- Legacy timings are a separate historical series and must not be pooled with fresh runs; smoke timings must never become performance editions.

## Deployment

`environments/Dockerfile` (Linux x86_64, pinned by digest) plus `deploy/renku/{session,job}.sh` for RenkuLab; `refresh.yml` is disabled unless `BENCHMARK_REFRESH_ENABLED=true` and needs a self-hosted runner. Details in `docs/deployment.md`.
