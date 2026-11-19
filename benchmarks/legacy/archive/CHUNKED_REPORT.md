# Chunked interpolation experiment

## Scope and interpretation

A bounded in-memory experiment on 4 × 512 × 512 float64 cubes with layouts `(time, y, x)` of `(1,128,128)`, `(1,256,256)`, and `(4,512,512)`. Every layout within a profile uses exactly the same source geometry, target geometry, values, and missing-data patch; their SHA-256 hashes are in the raw records. The rectilinear xarray, xESMF and xarray-regrid profiles share the same fixture. CRS profiles use the existing fixed 4326→2056 or 4326→3857 geometry. Cross-method timings are not a ranking: algorithms, geometry and execution models differ.

Three complete runs per layout used a single-thread Dask synchronous scheduler and one thread for OMP/BLAS/Numba. Input was an in-memory NumPy cube wrapped in Dask chunks, not an out-of-core read. Graph construction and `.compute()` are timed separately; compute includes the complete resulting array. Setup is measured once per profile, excludes explicit engine imports and is not added to each application. xESMF weights are built once and reused across layouts. For xarray/xarray-regrid interpolation and odc-geo warping no reusable weights are exposed by these adapters; their interpolation/warp machinery is included in application. Eager-reference time is one complete eager application on the same four-slice cube, not a repeated benchmark. Timings are wall-clock seconds; no warmup or statistical uncertainty is claimed. Each compute attempt has a 60-second alarm, with checkpointed repetitions.

xESMF requests `output_chunks={"y": 512, "x": 512}` explicitly to bound graph growth; outputs have full horizontal chunks and do not demonstrate tiled-output distribution. xarray output has a full longitude chunk and its two spatially chunked layouts include rechunk layers. odc-geo output retains spatial chunks for the two tiled layouts. Actual input/output tuples, task counts, and graph layer names are in the JSON; output laziness alone is not proof of efficient blockwise processing.

## Measurements

Medians of three complete computations, with graph construction shown separately. Setup and eager reference are single measurements shared across the corresponding profile.

| Tool | Grid | Layout | Setup s | Eager reference s | Graph s | Compute s | Tasks |
|---|---|---|---:|---:|---:|---:|---:|
| odc_geo | crs_2056 | 1×128×128 | 0.132 | 0.202 | 0.021 | 0.350 | 128 |
| odc_geo | crs_2056 | 1×256×256 | 0.132 | 0.202 | 0.011 | 0.187 | 32 |
| odc_geo | crs_2056 | 4×512×512 | 0.132 | 0.202 | 0.007 | 0.121 | 2 |
| odc_geo | crs_3857 | 1×128×128 | 0.105 | 0.089 | 0.020 | 0.239 | 128 |
| odc_geo | crs_3857 | 1×256×256 | 0.105 | 0.089 | 0.009 | 0.129 | 32 |
| odc_geo | crs_3857 | 4×512×512 | 0.105 | 0.089 | 0.008 | 0.085 | 2 |
| xarray | rectilinear | 1×128×128 | 0.763 | 0.291 | 0.022 | 0.508 | 2798 |
| xarray | rectilinear | 1×256×256 | 0.763 | 0.291 | 0.011 | 0.094 | 406 |
| xarray | rectilinear | 4×512×512 | 0.763 | 0.291 | 0.010 | 0.039 | 19 |
| xesmf | rectilinear | 1×128×128 | 9.771 | 0.356 | 0.050 | 5.359 | 229 |
| xesmf | rectilinear | 1×256×256 | 9.771 | 0.356 | 0.042 | 1.729 | 57 |
| xesmf | rectilinear | 4×512×512 | 9.771 | 0.356 | 0.046 | 0.084 | 6 |
| xesmf | roms | 1×128×128 | 9.876 | 0.402 | 0.048 | 5.446 | 229 |
| xesmf | roms | 1×256×256 | 9.876 | 0.402 | 0.048 | 1.781 | 57 |
| xesmf | roms | 4×512×512 | 9.876 | 0.402 | 0.041 | 0.119 | 6 |

## xarray-regrid extension

The added linear, nearest and conservative accessors use the same cube and all three layouts: 9 new profiles and 27 measurements. All outputs matched their own eager references exactly, including finite masks. Conservative retained native spatial output chunks; linear/nearest rechunked through xarray interpolation. Conservative uses `skipna=True, nan_threshold=1.0` and meridian/parallel cell geometry; this differs from the bilinear xESMF control. Its formatting and weight work occur per call in graph/compute, not the shared API setup. Runtime warnings for invalid divide occurred around missing cells without a discrepancy against the eager reference. See [the extension report](XARRAY_REGRID_REPORT.md) for the full added timing table and usability controls.

## Correctness and seams

Each result was compared with the same tool’s eager output, not with another algorithm. A NaN island at source rows/columns 124–131 crosses a 128-cell input boundary. For each layout the report stores the worst finite-mask mismatch count, finite-value maximum absolute difference, and maximum error on target-index rows/columns adjacent to multiples of 128 across all three repetitions. Those target-index bands are a useful screen, not an exact map of transformed input chunk boundaries, especially for CRS warps.

xESMF and xarray had no finite-mask mismatches; maximum finite errors were at most 8.89e-16 and zero respectively. odc-geo 4326→3857 had no mask mismatches and maximum finite error 1.78e-15. For 4326→2056, `(1,256,256)` produced **4 finite-mask mismatches**, and its largest finite difference was 6.61e-7; `(1,128,128)` had no mask mismatches but differed by up to 6.80e-7. The full-spatial layout matched its eager reference. These discrepancies are observations, not proof of their cause or evidence that all layouts are equivalent.

## Storage control

A separate xarray rectilinear test wrote the **same cube and hash** to NetCDF4 with on-disk chunks `(1,128,128)`, reopened it lazily with matching Dask chunks, and read the file once to warm the OS cache. Across three runs, median graph construction was 0.026 s and complete compute **including file reads** was 0.552 s. File creation and opening are excluded. This is a warm-cache control, not a cold-disk or storage throughput benchmark. All three outputs matched the eager reference exactly, including the finite mask. The corresponding in-memory median compute was 0.508 s; the two are descriptive measurements, not an isolated estimate of storage overhead.

## Larger graph-only diagnostic

For a separate 4 × 1024 × 1024 rectilinear xESMF input with `(1,128,128)` chunks and default output chunking, construction produced 42,497 tasks in 2.757 s after 37.487 s weight setup. Output spatial chunks were eight 128-cell chunks on each axis. xESMF warned that output chunk count increased by a factor of 64. The diagnostic did **not** execute this graph. An earlier default-output compute pilot was interrupted after approximately 150 s, and a full-horizontal-output 1024 pilot after approximately 120 s; neither produced a completed execution measurement. The shared 512 grid was selected for all timed profiles to keep the suite bounded. These interrupted pilots are not successful timings.

## Reproduction

Run each profile serially in a fresh process, then run the storage and graph-only controls and combine the JSON. Install the two environments using the README first; run these commands from the repository root. The temporary NetCDF file is deleted after the storage control.

```bash
compiled/bin/python chunked_bench.py xesmf rectilinear
compiled/bin/python chunked_bench.py xesmf roms
.venv/bin/python chunked_bench.py xarray rectilinear
.venv/bin/python chunked_bench.py xarray_regrid_linear rectilinear
.venv/bin/python chunked_bench.py xarray_regrid_nearest rectilinear
.venv/bin/python chunked_bench.py xarray_regrid_conservative rectilinear
.venv/bin/python chunked_bench.py odc_geo crs_2056
.venv/bin/python chunked_bench.py odc_geo crs_3857
.venv/bin/python chunked_storage.py
compiled/bin/python chunked_diagnostic.py
python chunked_combine.py
```

Raw per-profile files, storage control, graph diagnostic, and combined summary live in `chunked_results/`. The combined file contains 24 summaries, 72 in-memory run records, zero failed attempts, plus three storage-control runs. Fixture generation is inherited from `large_bench.py`; setup and inputs are not part of measured compute times.
