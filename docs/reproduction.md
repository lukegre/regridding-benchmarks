# Reproduce a benchmark edition

Use Python 3.11 or newer for the registry, validation, and static reports. Use Python 3.12 with the pinned benchmark environments for historical numerical comparisons. The Linux image, RenkuLab launcher settings and refresh workflows are documented in the [deployment guide](deployment.md).

## Reproduce a published case

1. Read the edition page and manifest. Record the run ID, commit, image digest, case ID and case version, engine versions, limits, and the input checksum. Check the case mask, quantity semantics, and target geometry before comparing results.
2. Check out the recorded commit and use the recorded image by digest. When running outside the image, set `BENCH_PYTHON` and `BENCH_COMPILED_PYTHON` to the absolute paths of the interpreters for the original two locks. The launcher uses its own interpreter when a requested alternate interpreter is unset.
3. Put inputs, scratch, and output in separate writable locations outside the checkout. Use `fetch` to verify the local cache or fetch the pinned HTTPS files. Configure `--repo` when launching from another directory.
4. Run the profile and inspect the complete bundle. Use `--case CASE_ID` to run a single case in that profile. A full standard or extended profile is required for publication.

```sh
regridding-benchmarks fetch --profile standard --cache-dir /cache/regridding
regridding-benchmarks run --profile standard --run-id local-standard \
  --cache-dir /cache/regridding --scratch-dir /scratch/regridding --output-dir /results
regridding-benchmarks validate-bundle /results/local-standard
```

Continue an interrupted run with the same command and `--resume`. Input availability, case definitions, run settings, source and environment must match. Completed samples, including unsuccessful attempts, remain part of that run. Use a new run ID to retry a completed sample under different conditions. If a run exits with an unexpected outcome, inspect its sample and log before comparing timing. A validated bundle can contain unsuccessful outcomes. Publication validation additionally checks that all observed outcomes are expected for their case.

## Compare evidence

A run bundle contains the planned roster and environment in `manifest.json`, raw timing and numerical repeats in `samples/`, process logs in `logs/`, and checksums in `checksums.json`. The report aggregates completed timings within an edition and timing phase. Use the recorded series, CPU, memory limits, software versions and cache policy to decide whether two editions are comparable. Smoke cases may shrink input, layouts or repeats and appear without aggregate performance timings.

Use analytic error for known reference fields and mask-aware comparisons for remapped values. For conservative operations, compare the area-weighted integral over the declared common domain. For categorical operations, inspect valid class membership and the mask separately. The masked rectilinear comparison records both adapters' error on their own support and on the same finite cells.

Preserve the original measurements with `regridding-benchmarks import-legacy --output-dir /results/legacy`. Pass that directory through `build-report --legacy-edition /results/legacy` to surface the original evidence index, raw files, and legacy revision in the site. The [legacy edition guide](../benchmarks/legacy/README.md) explains the recorded provenance and migration checks.

## Add or update a case

Add a versioned case to `benchmarks/` and a source manifest to `datasets/` for external inputs. Set the case geometry, quantity, mask policy, timing phases, resource limit and expected statuses. Record an upstream protocol and deliberate deviations. Define numeric gates and bounded smoke options where applicable. Leave the input unavailable when the actual data checksum or redistribution terms are unresolved. Bump the case version when its fixture, protocol or validation changes.

Use a named series for a controlled measurement resource. Cite the edition ID, source revision and exact case or raw sample location. For the legacy edition, cite the source revision, original JSON path and JSON Pointer from the legacy index. Review upstream and repository reuse terms before redistributing data or publishing a new archive. The repository has no explicit general reuse license.
