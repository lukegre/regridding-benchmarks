# How these results compare

We reviewed published experiments and official guidance against our shared-grid and chunked results. The evidence supports several mechanisms, qualifies some tool preferences, and identifies gaps. This is a literature comparison, not a replication of the external experiments.

Sources accessed 2026-11-17. Workloads, hardware, methods and timing boundaries vary; these sources do not establish a universal ranking.

[Large & chunked](docs/index.html) · [Small-grid survey](docs/small-data.html) · [Tool guide](docs/tool-guide.html) · [External comparison](docs/comparison.html)

## What the external evidence adds

### Our SciPy/xarray ordering is workload-dependent

CNES’s global structured-target benchmark reports xarray application faster than SciPy RegularGridInterpolator, reversing our local ordering. It also benchmarks pyinterp, which our suite does not include.

**Implication:** Treat SciPy as fastest among our measured adapters on our fixtures. Benchmark the exact target layout and API before choosing between SciPy and xarray; include pyinterp as an untested candidate.

### Chunk layout can reverse the result

The xarray-regrid conservative notebook reports xESMF/xarray-regrid execution ratios from 0.6 to 16.9 across layouts and NaN policies. Its chunk-amplification warnings resemble our default-output xESMF diagnostic.

**Implication:** Keep graph construction, completed compute, source generation and output chunks explicit. xarray-regrid is a separate package from our xarray.interp adapter; neither source establishes a universal chunked winner.

### Raster reprojection preferences depend on I/O

Development Seed finds GDAL wrappers competitive for local tiles, while remote-file access changes the order. GeoUtils separates serial Dask operation time from initialization overhead. SERTIT’s saved outputs even conflict with its written winner claim.

**Implication:** Keep Rasterio/rioxarray as local-workflow preferences, not cloud performance promises. A Dask input does not prove lazy warp execution; inspect the actual version, reads, output and chunks.

### Accuracy requires more than one smooth-field RMSE

MIRA compares conservation, bounds and feature preservation through repeated remapping; it does not provide a wall-clock ranking. The ERA5 notebook’s pairwise agreement does not make CDO ground truth.

**Implication:** Our numerical preferences remain conditional on quantity semantics. Add common-footprint errors, integral checks, discontinuities and cyclic-remap tests before making a general accuracy claim.

### A regional timeout does not rank global mesh tools

Mahadevan et al. complete conservative construction for ESMF, TempestRemap and MBTempest on different spherical meshes. Our failed TempestRemap regional overlap profiles cannot contradict that result.

**Implication:** Keep the 300-second timeout scoped to our SCRIP regional workflow. MBTempest is a separate untested candidate; do not rank it using our TempestRemap failures.

## Sources and comparisons

### [CNES pyinterp: Benchmarks](https://cnes.github.io/pangeo-pyinterp/benchmarks.html)

maintainer-published executable benchmark · Date/version Undated live page; describes development version after 2026.10.0 · qualifies recommendation · Topics: Rectilinear, Accuracy, Speed

**Setup:** Apple M3 Max, macOS, Python 3.13; best of at least three runs. Source 1440×720 global 0.25° grid. Bilinear target 0.1°, 80°S–80°N, 5.76 million points. Competitors one thread; pyinterp separately one/all cores. Versions: SciPy 1.18.1, xarray 2026.9.0, xESMF 0.9.2. Reported versions: NumPy 2.5.4, SciPy 1.18.1, xarray 2026.9.0, xESMF 0.9.2 and pyinterp development after 2026.10.0. Source 1440 × 720, 0.25° global; structured regridding is to 5.76 million points.

**External evidence:**

- Quote: Each time is the best of at least three runs.
- Bilinear application seconds: xESMF 1.4578; SciPy RegularGridInterpolator 0.1381; xarray.DataArray.interp 0.0317; pyinterp one thread 0.0096. Separate xESMF construction: 42.2 s.
- Conservative application seconds: xESMF 0.1183; pyinterp one thread 0.0012. Separate xESMF construction: 11.2 s. Geometry differs: meridian/parallel boxes versus ESMF great-circle edges.
- Structured 0.1° target over 80°S–80°N, 5.76 million queries: xarray 31.7 ms; SciPy RegularGridInterpolator 138.1 ms; xESMF weight application 1457.8 ms, with 42.2 s construction reported separately. pyinterp one-thread application: 9.6 ms. These are within-source figures, not comparisons to our machine.

**Comparison with our results:** Agrees that structured-grid specialization can avoid expensive general ESMF construction. Challenges a universal SciPy-over-xarray ranking: here xarray structured-target application is faster than SciPy; ours ranks SciPy first on its own rectilinear adapter. pyinterp was not measured locally and is a candidate, not a validated local winner.

**Local evidence:**

- Local rectilinear shared scale 1024, three-run mean setup/application: SciPy 0.00474 / 0.0735 s; xarray 0.000769 / 0.0951 s; smooth-field RMSE effectively equal at 1.96e-7. Source: large_results/combined.json.

**Limits:**

- Different hardware, target construction, versions and best-versus-mean statistic. No cross-site speedup ratio is valid. Claimed numerical agreement between libraries is not analytic accuracy. Pure rectilinear interpolation/conservation does not establish ROMS or mesh support. Periodic-longitude handling must be supplied for SciPy/xarray.

### [xarray-regrid: Performance of xesmf vs xarray-regrid](https://xarray-regrid.readthedocs.io/en/stable/notebooks/benchmarks/benchmarking_xesmf.html)

maintainer-published executed notebook benchmark · Date/version Undated live stable documentation (0.4.2) · consistent · Topics: Chunking, Speed

**Setup:** 8-core Intel i7 Ubuntu desktop. About 4 GB synthetic Dask float32 cube, 1000 times, global 0.25°→1° conservative coarsening. Layouts (1,all,all), (25,all,all), (all,32,32), (all,160,160). Minimum of two repeats. xESMF weights preconstructed; timed calls include .compute(), including generation of lazy random source values.

**External evidence:**

- Quote: xarray-regrid is much faster for small chunks, especially churro-style.
- Published xESMF/xarray-regrid execution ratios for skipna=False/True: (1,all,all) 3.7/7.2; (25,all,all) 0.6/1.1; (all,32,32) 14.2/16.9; (all,160,160) 1.8/2.4.
- Notebook records xESMF output-chunk count warnings of 72× for 32-cell chunks and 6× for 160-cell chunks.

**Comparison with our results:** Supports our observation that spatial chunk layout and output-chunk amplification can dominate completed compute. It also shows a ranking reversal between layouts, so no universal chunked winner is justified. xarray-regrid is a separate, locally untested package; it is not our xarray.interp adapter.

**Local evidence:**

- Local xESMF rectilinear median compute: 5.359 s at (1,128,128) and 0.084 s at (4,512,512); fixed 4 × 512 × 512 cube and full-horizontal output chunks. Separate 1024 graph-only diagnostic: 42,497 tasks and warning of 64× output chunks. Source: chunked_results/combined.json.

**Limits:**

- Conservative downsampling versus our bilinear near-resolution mapping; 1000 times versus four; full desktop versus two-vCPU quota; source graph computation included. Absolute seconds are not shown on the published page. Accuracy is not assessed in this performance notebook. Minimum-of-two differs from our three-run medians.

### [xESMF backend usage and benchmark](https://xesmf.readthedocs.io/en/latest/notebooks/Backend.html)

official executed tutorial microbenchmark · Date/version Undated live development documentation · methodological support · Topics: Rectilinear, Timing boundaries

**Setup:** Bilinear weights for 400×600 source →300×400 target, applied over 10 times ×50 levels. NumPy arrays; SciPy sparse application versus ESMPy native application of the same weights. Notebook CPU/wall outputs; hardware, thread controls and repetition statistic not supplied.

**External evidence:**

- Quote: It also writes weights to disk so we can then read them back for Scipy.
- Executed wall-time outputs: weight generation 4.35 s; ESMPy application 12.3 s; SciPy application 6.07 s.
- Notebook checks exact equality with np.testing.assert_equal(data_out_scipy, data_out_esmpy). Nearby prose still says about 7 s construction and about 3 s ESMPy application; executed outputs differ.

**Comparison with our results:** Supports separating construction from application and illustrates that wrapper/backend strategy changes runtime without changing supplied weights. This is NOT a SciPy RegularGridInterpolator benchmark. Our ESMPy results are on an icosahedral conservative profile, not the notebook's structured bilinear case; no direct local winner can be inferred.

**Local evidence:**

- Our large tier separates construction and eager application where exposed; fused APIs are labelled. Our ESMPy conservative adapter uses a different icosahedral family. Source: large_results/combined.json.

**Limits:**

- Single visible timings with unspecified hardware; stale prose conflicts with executed cells. Use numeric cell outputs and disclose inconsistency. Same-weight equality does not prove accuracy versus a physical truth. No basis for cross-machine or current-version speedup guarantees.

### [Iris: Which Regridder to Use](https://scitools-iris.readthedocs.io/en/latest/user_manual/explanation/which_regridder_to_use.html)

official qualitative guidance, NOT a measured benchmark · Date/version Undated live unreleased documentation; fetched page identifies 3.17.0.dev8 · methodological support · Topics: Conservation, Weight reuse

**Setup:** No timing experiment or hardware specification. Describes native Iris and iris-esmf-regrid schemes, caching, coordinate requirements, conservation and mask semantics.

**External evidence:**

- Quote: Generally, the prepare step is the more expensive of the two.
- Native AreaWeighted needs bounded 1-D lat/lon axes; ESMFAreaWeighted also supports bounded 2-D coordinates and face-located meshes. Both cache weights.
- ESMFAreaWeighted represents edges as great-circle arcs, unlike native AreaWeighted latitude/longitude boundaries; masks and mdtol alter covered-area conservation.

**Comparison with our results:** Supports our semantics-first selection, repeated-field weight reuse and explicit geometry/mask contracts. It does not validate our approximately 242-field Iris/CDO or 257-field ESMPy/CDO crossover estimates; those remain illustrative estimates from local means.

**Local evidence:**

- Our iris adapter is iris-esmf-regrid ESMFAreaWeighted, not native iris.analysis.AreaWeighted. The 242-field Iris/CDO and 257-field ESMPy/CDO estimates use local means, not externally measured crossovers. Source: tool_recommendations.json.

**Limits:**

- Qualitative documentation must be separated from benchmark confirmation. Do not attribute local speed advantages to all Iris schemes. Great-circle versus parallel-bounded conservation methods are not numerically identical even when both are valid for their chosen cell geometry.

### [xarray-regrid: Benchmarking bilinear regridding](https://xarray-regrid.readthedocs.io/en/latest/notebooks/benchmarks/benchmarking_bilinear.html)

maintainer-published real-data comparison notebook · Date/version Undated documentation; embedded dataset history is 2023-06-19 · qualifies recommendation · Topics: Accuracy, Timing boundaries

**Setup:** ERA5 monthly dewpoint for 2000, 12 time slices; target 265×530 points, 45–90°N and 90–180°E at 0.17°. CDO files converted to 64-bit. Dask distributed client; hardware and repetition statistic unspecified.

**External evidence:**

- Quote: xESMF seems to (subtly) deviate from the CDO and xarray-regrid results.
- Notebook reports approximately 1e-8 relative differences between CDO and xarray-regrid; these are pairwise differences, not error against independent truth.
- Visible times: xarray-regrid 0.070 s with explicit compute; xESMF 9.683 s includes constructor but no explicit compute in that timed cell. CDO is run separately without a timing.

**Comparison with our results:** Supports our observation that bilinear implementations can differ slightly, and qualifies treating CDO and xESMF as numerically interchangeable. Does not establish CDO as ground truth or prove that its errors are lower. The notebook wraps xarray.interp; it is separate from the conservative chunk benchmark.

**Local evidence:**

- Local rectilinear scale 1024 smooth analytic RMSE: CDO/SciPy/xarray approximately 1.96e-7, xESMF approximately 1.95e-7. Pairwise ERA5 agreement cannot validate this analytic-error ordering. Source: large_results/combined.json.

**Limits:**

- Do not report the visible times as a controlled head-to-head speedup: setup/application and lazy materialization boundaries differ. Pairwise agreement cannot establish physical accuracy. ERA5, polar target and interpolation kernels differ from our fixtures.

### [astropy-healpix Performance (v2.0.1 documentation)](https://docs.astropy.org/projects/astropy-healpix/en/stable/performance.html)

Maintainer-published microbenchmark · Date/version Publication date not stated; page reports updated 2026-07-20 · different workload · Topics: HEALPix, Speed

**Setup:** HEALPix pixel-index-to-angle conversion, RING/NESTED, nside 1/128, vector sizes 10/1000/1000000; not field interpolation. Hardware: Not stated on the benchmark page. Timing: Function timings in the printed microbenchmark; setup/application separation and repetitions not specified on this page. Source locator: pix2ang benchmark table. External locator: HEALPix scale 1024: healpy mean setup 0.226 s, astropy-healpix 1.358 s; application ~0.040 s each and RMSE ~9.28e-7..

**External evidence:**

- For pix2ang with NESTED=True, nside=128 and 1,000,000 indices, the printed table reports healpy 0.0364285 s, astropy-healpix 0.1383810 s, ratio 3.80. The supplied command is python -m astropy_healpix.bench.
- Brief source excerpt: “For larger arrays, the difference is a factor of a few at most.”

**Comparison with our results:** Our HEALPix scale-1024 bilinear-weight workflows also favor healpy in construction (0.226 versus 1.358 s), while application is similar (~0.040 s each) and smooth-field RMSE is effectively equal (~9.28e-7). The external conversion operation cannot validate those interpolation timings or a portable speedup. Retain healpy as a performance preference for the measured native workflow; do not quote the external 3.80 ratio as an interpolation speedup.

**Local evidence:**

- Local HEALPix scale 1024: healpy construction mean 0.226 s versus astropy-healpix 1.358 s; application about 0.040 s each; analytic RMSE about 9.28e-7. Source: large_results/combined.json.

**Limits:**

- No external accuracy measurement or hardware metadata; the table is illustrative and version-sensitive.

### [Improving climate model coupling through a complete mesh representation: a case study with E3SM (v1) and MOAB (v5.x)](https://gmd.copernicus.org/articles/13/2355/2020/)

Peer-reviewed primary performance benchmark · Date/version 2020-05-26 · different workload · Topics: Spherical meshes, Weight construction

**Setup:** Cubed-sphere to polygonal MPAS finite-volume conservative maps at multiple resolutions. A separate parallel study uses 614,400 to 153,600 cubed-sphere quadrilaterals. Hardware: Serial study: 8 Intel Xeon E7-4820 CPUs, 2.00 GHz, 64 available cores, 1.47 TB RAM; runs described as serial. Timing: Supermesh/intersection plus conservative weight generation; not field application. Parallel scaling is separately reported. Source locator: Section 4.1/Figure 8; Section 4.3.1/Figure 11. External locator: Four regional TempestRemap/NCO profiles timed out at 300 s during overlap generation, before completed weight/application measurements..

**External evidence:**

- Serial TempestRemap is comparable to ESMF and can be faster for highly refined cases; MBTempest averages about 2× faster than both in the reported conservative construction comparison.
- Brief source excerpt: “the MBTempest remapper consistently outperforms both tools, with a 2× speedup on average.”

**Comparison with our results:** Our regional SCRIP overlap-generation timeout before completed weights is not evidence of global TempestRemap unsuitability. The paper completes different spherical meshes and reinforces separating construction from application; MBTempest is a distinct implementation absent from our suite. Keep the timeout scoped to our adapter/input/time limit. Add MBTempest as an untested future candidate, not a measured local winner.

**Local evidence:**

- Four local TempestRemap/NCO regional profiles timed out at 300 seconds in overlap generation, before completed weights/application. NCO depends on the same Tempest weights. Source: large_results/combined.json failures.

**Limits:**

- Different geometry, implementations, versions and hardware; no transferable absolute-time comparison.

### [Metrics for Intercomparison of Remapping Algorithms (MIRA) protocol applied to Earth system models](https://gmd.copernicus.org/articles/15/6601/2022/)

Peer-reviewed primary numerical benchmark; not a wall-clock speed benchmark · Date/version 2022-09-02 · qualifies recommendation · Topics: Spherical meshes, Conservation, Accuracy

**Setup:** Cubed-sphere, MPAS and regular latitude–longitude meshes, uniform and regionally refined; analytic and realistic scalar fields; generally 1000 cyclic source→target→source remaps. Hardware: No hardware-normalized runtime comparison; numerical efficacy is the focus. Timing: No measured cross-package wall-clock ranking. Section 6.4 discusses offline setup and online application conceptually and leaves same-machine runtime comparison as future work. Source locator: Sections 4–5 and 6.4. External locator: Our large profiles repeat the same single-remap workflow three times; these are timing repeats, not 1000 cyclic remaps..

**External evidence:**

- The study evaluates accuracy, conservation, monotonicity and feature preservation for ESMF, TempestRemap, GMLS and WLS-ENOR. In tested smooth cases, TempestRemap p=2 reaches high-order convergence; ESMF conserve2nd improves errors over conserve but exhibits degraded convergence. Bounds are not guaranteed without filtering.
- Brief source excerpt: “our intercomparison study specifically compares only the numerical performance of each algorithm”

**Comparison with our results:** Our single-remap smooth-field RMSE and same-field repeat timings cannot establish convergence order, long-cycle dissipation, conservation or monotonicity. A faster/low-RMSE interpolator is not thereby preferable for conservative climate coupling. Retain conditional recommendations. Add repeated-remap, discontinuity, bounds and common-domain integral tests before a general accuracy verdict.

**Local evidence:**

- Our large-tier accuracy uses single-remap analytic scalar errors and finite coverage. Three timing repetitions are independent executions, not a 1000-cycle remapping experiment. Source: large_bench.py and large_results/combined.json.

**Limits:**

- Different order, fields and meshes; no direct numerical RMSE or speed ratio with our fixtures.

### [Cloud-native resampling and reprojection in Python — Development Seed](https://developmentseed.org/warp-resample-profiling/examples/summarize-results.html)

published benchmark / reproducible profiling notebooks · Date/version Results page processes results/2024-11-01; source repository inspected at a611e4fea1027f460625cea5c67760b9d10573cc (2026-04-03). These dates describe different artifacts. · qualifies recommendation · Topics: CRS conversion, Remote I/O

**Setup:** Data: One timestep and variable from real MUR SST and GPM IMERG; full resolution input, Web Mercator 256×256 output tiles at multiple zoom extents. MUR SST input is 0.01-degree global. Methods: Initial comparison uses nearest neighbour, including Rasterio, rioxarray, odc-geo, Pyresample and xESMF with/without pre-generated weights. Local/cloud NetCDF, virtualized Zarr, converted Zarr and overview-enabled formats. Hardware: JupyterHub/Docker environment documented; exact CPU model/count, RAM and thread settings not found in inspected summary and runner source. Timing: utils.process_results takes pyinstrument_data\["duration"\] from a fresh profiled script. Script includes imports, file opening/read/crop and completed load/compute. Weight-free and cached xESMF are separate variants. Not matched to our import-excluded timing. Accuracy: Not a numerical-accuracy or conservation benchmark; no RMSE-based ranking is supplied.

**External evidence:**

- ODC and Rioxarray (both based on GDAL) consistently had relatively fast times and low memory usage.
- Rasterio had similar memory usage and time for local tile generation to ODC and Rioxarray, but was much slower for remote files.
- XESMF without pre-generated weights was consistently the slowest method.
- MUR SST zoom 0 saved table: rasterio / COG / local duration 0.451393 s; rioxarray / NetCDF / h5netcdf / local 24.109180 s; odc / NetCDF / h5netcdf / local 29.754768 s. These rows differ in storage/overview configuration and are not a pure library comparison.
- df.loc\[ind, "duration (s)"\] = pyinstrument_data\["duration"\]
- da.load() precedes return xr_reproject(da, gbox).load(); this ODC example materializes cropped input before reprojection.

**Comparison with our results:** Supports separating xESMF weight construction from reuse and treating GDAL raster wrappers as competitive local reprojection workflows. It also limits our preference: the external remote-file result reverses a simplistic Rasterio-is-always-fastest conclusion because readers and access patterns matter. Our in-memory kernels and warm NetCDF control cannot establish cloud tile-serving performance. Keep Rasterio/rioxarray local-raster preference conditional; add explicit reader/overview/network caveat and cache weight advice.

**Local evidence:**

- Our rectilinear 1024 xESMF bilinear means: 37.990 s setup + 0.447 s application. Our Web Mercator 4096 total means: Rasterio 1.23 s, rioxarray 1.39 s, odc-geo 1.88 s, essentially identical smooth-field RMSE/coverage.

**Limits:**

- No direct throughput or speedup ratio against our runs: different hardware, real input dimensions, 256² tile outputs, nearest rather than our bilinear CRS kernels, process/import/I/O boundaries and data locality.
- Published summary warns that xESMF may be appropriate for conservation/curvilinear workloads despite slow setup; its nearest tile benchmark does not adjudicate conservative accuracy.
- The ODC example is not proof of fully lazy out-of-core input execution; it calls load() before warp.

### [GeoUtils scaling benchmarks — reprojection by raster size](https://glaciohack.github.io/geoutils/comparisons/comparisons.json)

published benchmark dashboard / machine-readable ASV-derived measurements · Date/version Raw JSON metadata date 2026-09-19T21:32:05Z; commit a31a03838b63bb9e39d21d0d956c72f1bcad2282. Dashboard summary and raw JSON can refer to different revisions; values below are from raw JSON. · consistent · Topics: CRS conversion, Chunking

**Setup:** Data: WGS84 EPSG:4326 raster → UTM32N EPSG:32632, nearest neighbour, preserving selected output dimensions. Raster side lengths 1024,2048,4096. Methods: GeoUtils Rasterio/GDAL calculation engine under eager, Dask and multiprocessing execution; standalone GDAL CLI also supplied. Summary reference workload uses 512×512 chunks. Hardware: Machine github-actions-x64-f56edd1d, Python /home/runner/miniconda3/envs/geoutils-dev/bin/python. Published dashboard states one computational process and one thread; detailed CPU model not in downloaded metadata. Timing: Raw JSON distinguishes operation_time_s (after execution-mode initialization) from end_to_end_time_s (prepared inputs through completed output). The latter includes worker/CLI startup. Accuracy: Timing and memory dashboard; no common-footprint RMSE or conservation evidence in these records.

**External evidence:**

- All options run without parallelism: one computational process using one thread.
- Reprojects a WGS84 (EPSG:4326) raster to UTM zone 32N (EPSG:32632) with nearest-neighbor resampling while preserving the selected output dimensions.
- reprojection-raster-size, parameter 2048: eager operation_time_s 1.0428038770000967, end_to_end_time_s 1.049540535000233; Dask operation_time_s 1.888733711499981, end_to_end_time_s 3.6690352219998204.
- reprojection-raster-size, parameter 4096: eager operation_time_s 4.118796545499663, end_to_end_time_s 4.134179817000586; Dask operation_time_s 8.59900268899969, end_to_end_time_s 10.462309581999762.

**Comparison with our results:** The external eager/Dask gap supports our warning that chunking is an execution strategy rather than an automatic speed gain. Its separate operation/end-to-end measurements also reinforce exposing execution initialization costs. It does not validate our exact optimal chunk size or our odc-geo accuracy discrepancy. Continue to require measured compute rather than graph construction alone, and use eager/full chunks when data fits and latency dominates.

**Local evidence:**

- Our synchronous single-thread chunk suite keeps geometry fixed: xarray rectilinear compute medians 0.508/0.094/0.039 s for (1,128,128)/(1,256,256)/(4,512,512). odc-geo Web Mercator 0.239/0.129/0.085 s; graph task counts128/32/2.

**Limits:**

- Different wrapper, nearest kernel, UTM destination, and dataset geometry; no cross-site seconds or package speedups are comparable.
- Dask is intentionally single-worker, so this cannot establish multiworker or distributed scaling.
- No claim that lower eager time is preferable when dataset exceeds available memory.
- No external accuracy evidence for our four finite-mask differences in one odc-geo LV95 layout.

### [SERTIT Open Source Rasters Comparison — use case reprojection benchmark](https://github.com/sertit/open_source_rasters_comparison/blob/30575de1f0c2e6241f87cfebecb52659ea7be21d/notebooks/08_usecase_reproj_dask.ipynb)

exploratory benchmark notebook with saved outputs; methodological caveats · Date/version Repository inspected at 30575de1f0c2e6241f87cfebecb52659ea7be21d (2026-07-21); execution date not recorded in inspected notebook. · qualifies recommendation · Topics: CRS conversion, Timing boundaries

**Setup:** Data: Real Pléiades Neo image subsets: one band, 9104×5758 (~100MB),29135×18426 (~1GB),71367×45135 (~6GB). Target EPSG4326; notebook says source EPSG:324643, which appears suspect and is not independently resolved. Methods: Bilinear Rasterio file-to-file, rioxarray open/reproject/to_raster, and Dask-backed opening followed by rio.reproject/to_raster with varying input chunks. Hardware: Intel Core i7-12700K @3.6GHz,64GB RAM,Windows11. Thread and scheduler details not explicitly controlled in inspected timing cells. Timing: perf_counter encloses memory_profiler.memory_usage invocation of full file open → default target transform → reprojection → raster write. Profiling overhead/I/O included; no separate setup/application timing, systematic repeat distribution or warm/cold cache control. Accuracy: No numerical reference-error or finite-mask comparison in saved timing cells.

**External evidence:**

- The resampling method used for all reprojection scenarios is bilinear.
- Saved outputs: Rasterio durations 6.74,30.18,175.71 seconds; rioxarray durations 6.2,25.24,162.83 seconds, for 100MB,1GB,6GB respectively.
- At 1GB, Dask-opening chunk1024 duration31.32s and chunk2048 duration25.45s; at6GB chunk2048 164.25s,chunk4096 164.14s,auto166.14s.
- The written conclusion says Rasterio: Fastest for simple reprojections; this conflicts with its own saved rioxarray timings.

**Comparison with our results:** Its saved outputs reinforce that Rasterio/rioxarray ordering depends on the workload and wrappers; do not repeat the notebook claim that Rasterio always wins. Its chunk-input timings do not prove lazy warp execution: rio.reproject can materialize .values. Versioned primary source below supports this caveat. Keep both Rasterio/rioxarray as conditional preferences rather than one universal winner; require checking output array type before describing a Dask-backed call as lazy.

**Local evidence:**

- Our4096LV95 rioxarray total mean2.05s versus Rasterio2.16s; WebMercator Rasterio1.23s versus rioxarray1.39s.

**Limits:**

- Exploratory single-notebook measurements, no fixed canonical target shape/hash across adapters is demonstrated.
- The companion03_reprojection notebook claims rio.reproject creates a lazy Dask graph, which conflicts with verified rioxarray0.19 implementation and docs. Dask on opening does not prove Dask warp.
- Source-CRS identifier appears suspect; notebook conclusions contain a timing-order inconsistency. Treat it as lower-confidence evidence, not a validation of our recommendations.
- No independently validated error/conservation metric.

### [rioxarray0.19.0 reproject implementation and Dask note](https://github.com/corteva/rioxarray/blob/0.19.0/rioxarray/raster_array.py)

versioned implementation/documentation, not a benchmark · Date/version Version0.19.0 · methodological support · Topics: Chunking, Execution model

**Setup:** Data: Not applicable Methods: RasterArray.reproject Hardware: Not applicable Timing: No timings Accuracy: No accuracy measurements

**External evidence:**

- To re-project with dask, see odc-geo & pyresample.
- rasterio.warp.reproject(source=self._obj.values, destination=dst_data, ...)

**Comparison with our results:** Corroborates checking actual execution/output chunks instead of treating Dask-backed input as proof of lazy output. Also supplies a primary-source correction to SERTIT companion notebook narration. Retain existing separation between eager rioxarray and tested lazy odc-geo; do not infer behavior of newer versions without inspection.

**Local evidence:**

- Our large rioxarray adapter is timed eagerly; chunk suite uses odc-geo for tiled lazy reprojection rather than assuming rio.reproject preserves laziness.

**Limits:**

- Not an independent speed benchmark; no performance ratio or error ranking follows from source code alone.
- Version-specific evidence.

## Evidence gaps

- No external source reviewed reproduces our complete grid hashes, masks, methods, hardware, versions and timing boundaries. No direct cross-study speed ratio is justified.
- pyinterp, xarray-regrid and MBTempest were not run locally. Their external results identify candidates rather than local winners.
- Our smooth analytic scalar, mostly single-remap tests do not cover vector rotation, convergence order, long-cycle dissipation or every missing-value/conservation policy.
- The HEALPix external microbenchmark measures coordinate conversion, not map interpolation. Its speed ratio cannot validate our interpolation timings.
- Official guidance and issue reports support interpretation; they are explicitly labelled and do not count as independent benchmark replication.

[Download comparison data](docs/external-comparisons.json)
