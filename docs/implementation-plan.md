# Regridding benchmark overhaul

## Target outcome

One case registry and one CLI drive local reproduction, CI checks, RenkuLab sessions and batch jobs, and published benchmark refreshes. The suite retains the original synthetic evidence and adds real observations, model output, and cases adapted from published benchmarks. Each public result links to a specific dataset, protocol, software environment, and immutable run bundle.

## Repository layout

```text
pyproject.toml              Package and CLI entry point
src/regridding_benchmarks/  Case loading, runner, fixtures, adapters, metrics, manifests
benchmarks/                 Versioned cases and smoke, standard, and extended profiles
datasets/                   Source manifests and deterministic fetch and subset recipes
environments/               Linux x86_64 locks and container build files
deploy/renku/               Launcher definitions and setup instructions
tests/                      Unit, numerical, runner, adapter, and publication checks
reports/                    Site templates, figures, and report builders
docs/                       Methodology, contributors' guide, and reproduction handbook
.github/workflows/          Pull request checks, image build, refresh, and Pages deployment
```

Keep case definitions and dataset manifests in Git. Cache downloads by checksum and write runs to a configurable output directory outside the source tree. Publish versioned bundles with a manifest, raw repeats, failures, logs, and checksums. Build Pages from validated bundles. Move the tool guide, contracts, recommendations, and agent skill to the same evidence model so their claims can identify the case and run that support them.

## 0. Preserve the baseline and prove RenkuLab execution

- Record the current revision and verify the historical checksums. Package the existing small, large, and chunked results and original tool guide as a legacy edition. Preserve the current URLs or redirect them to the matching edition at cutover.
- Build a Linux x86_64 image from the current Python and compiled locks. Start with both existing environments inside the image. Record the image digest and actual dependency versions. Smoke-test a Python adapter, xESMF/ESMF, and the CDO executable as a non-root user.
- Link the GitHub repo to a RenkuLab project. Provide a **JupyterLab session launcher** for exploration and a **non-interactive Job launcher** for smoke and standard profiles. Start with a smoke command around the existing runners and replace it with the shared CLI in phase 1. Use the same pinned benchmark environment for both. A thin Jupyter layer on the same base image is fine if needed. Pin the source revision for batch runs, even when the linked checkout opens on a moving branch.
- Configure separate writable scratch, checksum-verified input cache, and durable result storage. Use a Renku data connector or an explicit upload from the job. Verify the bundle is readable after the job ends. Size the initial CPU, memory, and disk class from the smoke run, then pilot the full matrix before selecting resources for standard and extended jobs.
- Verify whether the target RenkuLab deployment offers supported unattended credentials for Job submission and status polling. The documented CLI supports `rnk job start` and documents browser-based login. Test unattended authentication and renewal explicitly before making the scheduler depend on it. [Job launchers](https://docs.renkulab.io/en/latest/docs/users/compute/job/guides/create-a-job-launcher/) · [Custom images](https://docs.renkulab.io/en/latest/docs/users/compute/environment/guides/use-your-own-docker-image-for-renku-session/) · [Renku CLI](https://docs.renkulab.io/en/latest/docs/users/cli/cli-reference/) · [Resource classes](https://docs.renkulab.io/en/latest/docs/users/compute/resource-pools-and-classes/)

**Acceptance:** a clean checkout starts the smoke profile from a RenkuLab session and a Job. The Job completes with the browser closed and leaves a durable result bundle. Record the chosen Renku namespace and launcher IDs in the setup guide once provisioned.

## 1. Replace the runner and results contract

- Add an installable CLI with commands to list cases, fetch inputs, run a profile, validate a bundle, and build a report. Case definitions specify adapter, fixture or dataset, source and target geometry, quantity semantics, method, mask rules, timing phases, resources, and expected outcomes. Use one registry for selection, execution, and reporting.
- Put fixture normalization, result validation, and measurement around the adapter calls. Reuse the existing kernels and package-specific setup where possible. Preserve timing distinctions among imports, fixture loading, weight construction, graph construction, materialized application, storage, and CLI I/O where observable.
- Write run metadata before measuring. Record commit, schema and case versions, image and lock digests, observed engine versions, effective CPU and memory limits, thread and cache policies, dataset hashes, and geometry fingerprints. Include bounds or topology where the method depends on them. Write checkpoints atomically and resume only compatible samples within the same run. Distinguish successful output, expected rejection, unsupported case, timeout, crash, and incomplete run.
- Migrate the small adversarial, shared-grid, chunked, storage, and native-control cases. Import the legacy measurements with their original provenance and explicit unknowns. Compare case inventories, expected statuses, fixture hashes and numerical outputs where available. Treat timing from a different machine or configuration as a separate series.
- Add offline CI for schemas, manifest integrity, compatibility on resume, interrupted writes, and aggregation. Add tiny Python and compiled adapter tests and a report-build/browser check. Use method-specific gates for finite masks, coverage, constant preservation, categorical integrity, and conservation on the appropriate domain. Pair per-adapter errors with common-support comparisons when meaningful.

**Acceptance:** all legacy case families are accounted for, the new runner emits valid bundles from fresh and interrupted runs, and the report can render historical measurements without the benchmark environments installed.

## 2. Add real inputs and published workloads

For each case, pin input identifiers and checksums, time and spatial selection, coordinate/CRS and mask interpretation, and the upstream protocol revision where available. Record deliberate deviations from the published protocol. Use analytic fixtures for absolute numerical error. Use pairwise differences, coverage, invariants, or an independent reference suited to the real-data case.

| Priority | Case | Deliverable |
| --- | --- | --- |
| First | ICON `ngc3028` and pyicon | Pin zoom 7 and the notebook's surface ocean temperature slice. Reproduce its 1° latitude–longitude target and compare pyicon with a baseline using the same sampling rule. Record wet-cell coverage and common-support differences. [easy.gems notebook](https://easy.gems.dkrz.de/Processing/healpix/pyicon_healpix.html) |
| First | HEALPix geometry and `xdggs` | Exercise RING/NESTED identity, sparse cell IDs, and CF 1.13 HEALPix and Zarr DGGS write/reopen round trips. Verify values, masks, and supported grid metadata. Compare spherical indexing with healpy and test WGS84 `healpix-geo` geometry against independent reference cases. Add a higher-resolution range-coverage memory profile. [EGU abstract](https://doi.org/10.5194/egusphere-egu26-18208) · [xdggs conventions](https://xdggs.readthedocs.io/en/latest/user_guide/conventions.html) |
| Next | ERA5 dewpoint | Pin the notebook's 12 monthly fields and exact 265 × 530 target, or document a replacement input as an adaptation. Run CDO, xESMF, and xarray-regrid with consistent dtype, coverage checks, and completed timing phases. [Published ERA5 comparison](https://xarray-regrid.readthedocs.io/en/stable/notebooks/benchmarks/benchmarking_bilinear.html) |
| Next | xHEALPixify | Add latitude–longitude → HEALPix for a masked analytic field and a small ocean subset. Inspect the pinned operation before selecting a matching baseline. Check empty cells, coastline leakage, and cell IDs. [xHEALPixify](https://github.com/IAOCEA/xhealpixify) |
| Next | MUR SST and VIIRS | Use MUR SST for a local versus remote Web Mercator tile case with fixed zooms, resampling, and overview policy. Measure read time, warp time, total latency, and peak memory. Add a VIIRS Level-2 antimeridian scene for geolocation and flag/mask handling. Consider IMERG as a second tile input to exercise axis ordering. [Development Seed benchmark](https://developmentseed.org/warp-resample-profiling/examples/summarize-results.html) · [NOAA VIIRS SST](https://coastwatch.noaa.gov/cwn/products/acspo-global-sst-viirs.html) |
| Extended | Published Dask and structured comparisons | Reproduce 0.25° → 1° conservative coarsening with 1,000 time slices, four layouts, and both missing-value policies. Disclose whether source generation is timed. Reproduce CNES structured and scattered bilinear cases with pyinterp, explicit thread counts, and a periodic-longitude control. [Dask protocol](https://xarray-regrid.readthedocs.io/en/stable/notebooks/benchmarks/benchmarking_xesmf.html) · [CNES protocol](https://cnes.github.io/pangeo-pyinterp/benchmarks.html) |
| Extended | MIRA and global mesh weight generation | Use one published cubed-sphere/MPAS pair. Track conservation drift, bounds violations, and feature loss through repeated remaps, including the published iteration count in the full profile. Separately measure overlap and weight construction with ESMF, TempestRemap, and MBTempest where available. [MIRA inputs](https://github.com/CANGA/MIRA-Datasets) · [MIRA study](https://gmd.copernicus.org/articles/15/6601/2022/) · [Weight construction study](https://gmd.copernicus.org/articles/13/2355/2020/) |
| Access dependent | EUMETSAT GEO-Ring | Start with one L1g HEALPix infrared scene, such as Cyclone Freddy. Pin the actual product and inspect its format, mask, geometry, and ordering. Evaluate subsetting and remapping around supported disk edges and seams. Add a native-to-HEALPix case if matched native input and the production mapping are available. Confirm access and redistribution terms before selecting public artifacts. [Test-data guide](https://user.eumetsat.int/resources/user-guides/geo-ring-test-data) · [EUMETSAT scene example](https://climate.esa.int/media/documents/08._20260326_FKaspar_EUMETSAT_for_ESA_CCI.pdf#page=23) |

Track the remaining literature as an explicit coverage table. Prioritize the xESMF same-weight SciPy/ESMPy application microbenchmark and GeoUtils eager/Dask/GDAL reprojection scaling if they resolve decisions in the tool guide. Treat SERTIT's file-to-file workload as an adaptation unless its source CRS and data are recoverable. Use the astropy-healpix indexing microbenchmark and Iris guidance for the relevant operation and weight-reuse contracts.

**Acceptance:** each implemented case has a bounded smoke variant where feasible, an executable full specification, explicit numerical checks, and a report that identifies the dataset, upstream source, and local deviations. Unavailable inputs or engines appear with explicit status and reason.

## 3. Automate refresh, publication, and rollback

1. Run offline correctness and report checks on pull requests. Build a pinned, tested benchmark image for trusted revisions. Propose dependency changes through reviewable lockfile updates.
2. Trigger a standard refresh monthly as a starting cadence and expose a manual dispatch for standard or extended runs. Prefer submitting the RenkuLab Job from the workflow once supported unattended authentication, status tracking, and result retrieval have been proven. Restrict scheduled jobs to trusted revisions. If that integration is unavailable, schedule the same container on a controlled Linux runner and keep RenkuLab Jobs available for batch reproduction. Label runner series separately.
3. Run one timing profile at a time per benchmark resource, recording CPU model, effective limits, resource class and cache state. Keep RenkuLab measurements in their own series unless repeat runs and recorded resources establish a comparable reference. Keep pruned smoke timing out of the published performance series.
4. Validate the candidate against the expected roster, sample counts, provenance and numerical tolerances. Retain diagnostics for failed attempts. Use run IDs and workflow concurrency to make retries idempotent and prevent overlapping refreshes or stale jobs from advancing publication. Archive only approved files and outputs permitted by the dataset terms.
5. Publish the successful bundle under an immutable edition and deploy Pages from that bundle. The site exposes the last successful edition, historical links, and a visible status for unavailable cases. A failed or cancelled refresh leaves the last successful edition available. Roll back by redeploying a previous validated bundle. Add citation metadata and document the chosen reuse terms. [GitHub Actions schedules](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) · [GitHub Pages deployment](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)

**Acceptance:** an unattended refresh publishes a verified edition through ordinary scripts, and a deliberately failed or cancelled refresh preserves the prior edition. A reader can reproduce a published smoke case on RenkuLab from the documented image, source revision, and inputs.

## Cutover order

1. Baseline capture, container, and RenkuLab smoke run.
2. New runner and provenance with one migrated synthetic case, one real ICON case, and offline DGGS tests.
3. Historical data import, remaining synthetic migration, and staging publication.
4. Scheduled standard refresh and public cutover after bundle parity, link checks, and rollback rehearsal.
5. Expand the real-data and literature cases by priority, with costly or credentialed profiles run separately.

Renku project ownership, available resource quota, durable storage, unattended authentication, and GEO-Ring access are deployment checks. The offline runner, migration, and report work can proceed while those are resolved.
