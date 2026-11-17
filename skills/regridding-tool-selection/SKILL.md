---
name: select-geospatial-regridding-tool
description: Choose geospatial remapping tools and interpolation schemes using grid geometry, quantity semantics, accuracy, coverage, measured speed and weight reuse. Covers rectilinear, ROMS, satellite swath, Gaussian, HEALPix, icosahedral, projected mesh, CRS and chunked workflows.
---

# Select a geospatial regridding tool

Use this skill when selecting or implementing a regridding/reprojection workflow. Treat the preferences below as conditional evidence from synthetic fixtures measured on 2026-11-17. Do not infer support, accuracy or performance for untested inputs.

## Workflow

1. Inspect the input and requested output. Record variable meaning and units; dtype, scale/offset and nodata; dimensions and coordinate order; source/target CRS and datum; grid topology and cell location; masks; target extent/resolution; chunk layout; and number of fields sharing geometry. Infer these from metadata where reliable; ask only for requirements that cannot be inferred.
2. Choose semantics before software: distinguish point samples, cell averages, cell totals, labels, probabilities and flags. Decide the required coverage, conservation property, missing-data policy and error tolerance. Use the non-float rules below.
3. Match the grid to a preferred workflow below. Compare only methods that satisfy those requirements. Use the full Gaussian recommendation only for separable axes, a planar mesh algorithm only in an appropriate projected CRS, and structured-swath interpolation only with valid cell geometry.
4. Read the selected tool’s required input contract in tool_contracts.json, including required_input_fields, nonfloat_method, geometry, missing and execution. Check the installed version against primary documentation. Supply real corners for conservative remapping; carry HEALPix nside/order/frame; distinguish ROMS rho/u/v grids; rotate vectors separately. Never invent a CRS or corners to make an adapter accept the data.
5. Optimize within the valid method. For one field compare setup + application; for N fixed-grid fields estimate setup + N × application. Reuse weights only with matching coordinates, bounds, masks, method and periodicity. For chunked data inspect the actual graph, spatial rechunking and output chunks; time complete compute, not only lazy graph construction.
6. Validate a representative subset before the full run. Check finite-mask agreement, common-footprint error, range/positivity where required, class membership, missing-data behavior and chunk-boundary agreement. Check area integrals over a common covered domain for conservation. Smooth-field RMSE alone is insufficient.
7. Run the workflow, retaining setup, graph construction, compute and I/O timing boundaries separately. Record geometry/value hashes, package versions, hardware/thread/scheduler settings, chunk layouts and repeat variability. Keep failed and incomplete runs out of successful timing summaries.
8. Report the selected tool and method, why they satisfy the quantity/grid, the measured evidence and its limits, the alternatives, validation results and any remaining uncertainty. When evidence is missing, state that no measured winner exists and propose a bounded comparison with identical fixtures.

## Non-float rules

- **Categorical identifiers or strings:** Nearest class, with an explicit choice between selecting the nearest cell and retaining its validity versus searching for the nearest valid cell; or an explicitly defined area/distance-weighted mode. Availability of nearest-valid search depends on the tool. Define deterministic ties and an unknown class. Encode labels to integer IDs with a reversible lookup; preserve nodata in a separate validity mask. Use compact codes for identifiers too large for exact float representation (including integers above 2^53); retain the original labels in the lookup and never cast them through float. Never bilinear-interpolate class IDs or round blended labels.
- **Ordinal values:** Use nearest or mode when ordered labels are classes; interpolate only when distances on a numeric scale are meaningful and the resulting values are valid for the application. Do not assume equal spacing between ordinal ranks.
- **Continuous quantity stored as integer:** Convert to floating point and use a continuous method appropriate to geometry, error and conservation; retain scale/offset and units. For CF-packed values, decode scale_factor/add_offset and missingness before interpolation; repack only with an explicit precision and overflow policy. Storage dtype alone does not make a quantity categorical; integer output can lose precision.
- **Extensive counts or totals per cell:** Distribute totals by conservative overlap fractions using cell areas and valid coverage; equivalently remap density then multiply by destination area with consistent normalization. Retain fractional output or use globally constrained rounding if integer totals are required. Ensure areas, masks, covered domain and normalization refer to the same geometry; check total over the common covered domain. For partially covered cells, a coverage-normalized average multiplied by full destination area is not generally conserved; use actual covered area with consistent source and destination masks. Never independently round each interpolated count or assume a weighted average preserves sums.
- **Boolean occupancy:** Use nearest for a sampled state; mode for dominant class; any/all for stated presence semantics; or area fraction as floating point for coverage. Threshold fractions only if an explicit decision threshold is meaningful. Do not choose any/all, mode or fraction interchangeably.
- **Packed bit flags:** Nearest for a representative observation, or unpack each bit and apply documented per-bit any/all/weighted rules; repack after aggregation. Never average or bilinearly interpolate packed flags.
- **Timestamps:** Specify whether values denote instants, intervals or categorical event times, calendar/time zone and missingness; interpolate only when a meaningful temporal model permits, after conversion to a suitable numeric time axis. Use a relative time origin and suitable precision to avoid loss of precision, then restore the calendar and units. Do not blend date encodings blindly or treat intervals as point instants.

## Input validation

- Identify source and target geometry, CRS/frame, units, shape and field location before choosing a tool.
- Validate coordinates, uniqueness and order, longitude seam, dimensions and valid topology. Validate actual corners and areas for conservative operations.
- Separate geometry masks from per-variable missing values; reserve a collision-free sentinel or use a separate valid mask.
- Determine intensive versus extensive quantity, coverage, normalization, extrapolation, valid output domain and deterministic tie behavior.
- Test identity, constant, known category and missing-value cases; check finite coverage, edge behavior and area integrals when applicable.
- For reused weights, hash coordinates, topology, bounds, masks, method and periodicity; do not reuse by shape alone.
- For chunked data, distinguish lazy graph construction, weight generation and actual compute; account for rechunking and peak memory.

## Preferred tools: accuracy and speed

Choose quantity semantics, acceptable coverage and geometry first; then compare speed within the valid method. These are conditional recommendations on synthetic data, not universal package rankings.

Arithmetic mean of three measured repeats; total range is min–max of per-repeat setup + application.

Setup and application are separate. Fused APIs include weight/geometry work in application; CDO includes native file I/O and process launch. These are measured workflows, not isolated kernel timings. The local mesh family has different targets and cannot be ranked against raster targets.

RMSE is against a smooth analytic scalar field on each output’s finite cells; it does not measure conservation, categorical correctness, edge preservation or uncertainty. Different coverage can hide difficult cells. Validate error on a common footprint and test real fields before adopting a recommendation.

For repeated fields on fixed grids, estimate setup + N × application rather than multiplying total time by N. Reuse weights only when coordinates, bounds, masks, method and periodicity match. The crossover estimate is illustrative, not a new measured multi-field benchmark.

Chunked choice: use xarray linear for separable rectilinear data, xESMF for curvilinear reusable weights, and odc-geo for the tested tiled lazy CRS workflow. All use the common 4 × 512 × 512 cube. xESMF compute changes from 5.36 s to 0.084 s between (1,128,128) and full-cube chunks, but uses full-horizontal output chunks in both; this is not evidence of distributed spatial output. odc-geo LV95 has four mask differences at (1,256,256). The NetCDF control is warm-cache only. See the chunked results for graph timings and full accuracy checks.

Non-float preferences follow semantics below: nearest for nominal classes, explicit mode for an area-majority class, conservative density/area conversion for counts, and explicit logical rules for flags. The smooth-field RMSE ranking supplies no evidence that bilinear is suitable for these variables.

### Rectilinear continuous fields

**Preferred: SciPy linear; xarray linear when labelled arrays matter.** SciPy is the fastest measured linear point interpolator here, with effectively the same smooth-field RMSE as xarray and CDO. Prefer CDO conservative when preserving cell integrals is the requirement; linear point interpolation cannot replace it. For many fields on fixed geometry, Iris has faster measured conservative application than CDO despite slower construction; the illustrative mean-time crossover is about 242 fields, assuming weights are reused.

Measured family: `rectilinear`, shared scale 1024.

| Tool / method | Setup mean (s) | Apply mean (s) | Total mean (min–max), s | Accuracy | Finite coverage |
| --- | --- | --- | --- | --- | --- |
| scipy | 0.00474 | 0.0735 | 0.0782 (0.0675–0.0929) | RMSE 1.96e-07 | 100.000% |
| xarray | 0.000769 | 0.0951 | 0.0958 (0.0846–0.109) | RMSE 1.96e-07 | 100.000% |
| cdo_bilinear | 1.75 | 0.223 | 1.97 (1.87–2.11) | RMSE 1.96e-07 | 100.000% |
| xesmf_bilinear | 38 | 0.447 | 38.4 (36.9–41.1) | RMSE 1.95e-07 | 100.000% |
| cdo_conservative | 12.7 | 0.267 | 12.9 (12.4–13.5) | RMSE 3.35e-05 | 100.000% |
| iris | 61.7 | 0.0642 | 61.8 (52.7–67.9) | RMSE 3.35e-05 | 100.000% |

### Full Gaussian continuous fields

**Preferred: SciPy/xarray for separable point interpolation; CDO conservative for cell averages.** The tested full Gaussian grid has separable latitude/longitude axes: SciPy is much faster at similar smooth-field RMSE. This recommendation does not cover reduced Gaussian grids. Use MIR for supported native meteorological grid workflows, rather than assuming reduced grids can be reshaped.

Measured family: `gaussian`, shared scale 1024.

| Tool / method | Setup mean (s) | Apply mean (s) | Total mean (min–max), s | Accuracy | Finite coverage |
| --- | --- | --- | --- | --- | --- |
| scipy | 0.016 | 0.136 | 0.152 (0.149–0.158) | RMSE 1.02e-06 | 100.000% |
| xarray | 0.00363 | 0.181 | 0.185 (0.177–0.193) | RMSE 1.02e-06 | 100.000% |
| cdo_bilinear | 2.82 | 0.405 | 3.22 (3.05–3.35) | RMSE 1.02e-06 | 100.000% |
| earthkit_mir | 0.0263 | 16.2 | 16.2 (15.1–17.2) | RMSE 1.02e-06 | 100.000% |
| cdo_conservative | 24.7 | 0.344 | 25.1 (24.7–25.7) | RMSE 1.51e-06 | 100.000% |

### ROMS / curvilinear continuous fields

**Preferred: CDO bilinear for measured speed and accuracy; xESMF for a Python weight workflow.** CDO and xESMF have very similar smooth-field error and complete coverage here; CDO is faster for both setup and application in this adapter. Prefer CDO conservative for cell averages requiring overlap remapping. Choose xESMF for Python integration and explicit weight management, not a measured speed advantage.

Measured family: `roms`, shared scale 1024.

| Tool / method | Setup mean (s) | Apply mean (s) | Total mean (min–max), s | Accuracy | Finite coverage |
| --- | --- | --- | --- | --- | --- |
| cdo_bilinear | 1.76 | 0.251 | 2.02 (1.77–2.26) | RMSE 1.98e-07 | 100.000% |
| xesmf_bilinear | 35.4 | 0.603 | 36 (35.4–37.1) | RMSE 1.96e-07 | 100.000% |
| cdo_conservative | 13.4 | 0.278 | 13.7 (13.4–14) | RMSE 3.24e-05 | 100.000% |
| xesmf_conservative | 58.1 | 0.559 | 58.7 (57.3–60.6) | RMSE 3.24e-05 | 100.000% |

### Satellite swaths

**Preferred: Pyresample nearest for fast geolocated centre sampling; CDO bilinear for the tested structured swath.** Pyresample nearest is the speed choice when nearest sampling and a finite search radius are acceptable. The structured-swath CDO bilinear adapter has much lower smooth-field RMSE but lower coverage. These RMSE values use different finite subsets: they do not establish an accuracy winner on a common footprint. Irregular/folded swaths need additional geometry checks; do not treat every swath as a structured cell grid.

Measured family: `satellite_swath`, shared scale 1024.

| Tool / method | Setup mean (s) | Apply mean (s) | Total mean (min–max), s | Accuracy | Finite coverage |
| --- | --- | --- | --- | --- | --- |
| pyresample_nearest | 1.88 | 0.0346 | 1.91 (1.84–1.97) | RMSE 0.00138 | 92.698% |
| pyresample_gauss | 3.11 | 0.543 | 3.66 (3.47–3.91) | RMSE 0.00137 | 92.698% |
| cdo_bilinear | 3.51 | 0.342 | 3.85 (3.51–4.47) | RMSE 1.12e-07 | 83.175% |
| xesmf_bilinear | 68.9 | 1 | 69.9 (67.4–73.8) | RMSE 1.11e-07 | 83.175% |

### Raster CRS conversion: WGS84 → Web Mercator

**Preferred: Rasterio bilinear; rioxarray for labelled-array integration.** Rasterio has the best mean total time at 4096², with essentially identical RMSE and coverage across the three raster wrappers. odc-geo remains the choice among the tested adapters when retaining tiled lazy output is required; verify its chunked result separately.

Measured family: `crs_4326_to_3857`, shared scale 4096.

| Tool / method | Setup mean (s) | Apply mean (s) | Total mean (min–max), s | Accuracy | Finite coverage |
| --- | --- | --- | --- | --- | --- |
| rasterio | 0.000107 | 1.23 | 1.23 (1.19–1.27) | RMSE 4.23e-09 | 100.000% |
| rioxarray | 0.0889 | 1.3 | 1.39 (1.36–1.42) | RMSE 4.23e-09 | 100.000% |
| odc_geo | 0.0871 | 1.79 | 1.88 (1.85–1.91) | RMSE 4.23e-09 | 100.000% |

### Raster CRS conversion: WGS84 → Swiss LV95

**Preferred: Rasterio or rioxarray bilinear; no robust speed winner between them at 4096².** rioxarray has the lowest mean total at 4096², but the observed total-time ranges overlap Rasterio. Their outputs have the same measured RMSE and coverage. Prefer Rasterio for direct warp control, rioxarray for labelled arrays. odc-geo is slower here and the separate 256² chunk layout changes four finite-mask values; validate tiled LV95 output before relying on equivalence.

Measured family: `crs_4326_to_2056`, shared scale 4096.

| Tool / method | Setup mean (s) | Apply mean (s) | Total mean (min–max), s | Accuracy | Finite coverage |
| --- | --- | --- | --- | --- | --- |
| rasterio | 0.000161 | 2.16 | 2.16 (2.03–2.42) | RMSE 1.46e-05 | 95.191% |
| rioxarray | 0.0964 | 1.96 | 2.05 (2.01–2.08) | RMSE 1.46e-05 | 95.191% |
| odc_geo | 0.0894 | 3.59 | 3.68 (3.59–3.72) | RMSE 1.46e-05 | 95.191% |

### HEALPix continuous intensities

**Preferred: Healpy native interpolation; MIR if lower smooth-field error justifies its cost.** Healpy is the fastest measured native interpolation, at essentially the same RMSE as astropy-healpix and CDO bilinear. MIR has lower RMSE on this smooth field but much higher total time. Choose nearest native pixel lookup for categorical IDs; bilinear intensity interpolation does not preserve per-pixel totals.

Measured family: `healpix`, shared scale 1024.

| Tool / method | Setup mean (s) | Apply mean (s) | Total mean (min–max), s | Accuracy | Finite coverage |
| --- | --- | --- | --- | --- | --- |
| healpy | 0.226 | 0.0398 | 0.266 (0.262–0.268) | RMSE 9.28e-07 | 100.000% |
| astropy_healpix | 1.36 | 0.0391 | 1.4 (1.34–1.43) | RMSE 9.28e-07 | 100.000% |
| earthkit_mir | 0.00942 | 18.1 | 18.2 (16.9–19.9) | RMSE 5.97e-07 | 100.000% |
| cdo_bilinear | 3.01 | 0.378 | 3.39 (3.14–3.55) | RMSE 9.28e-07 | 100.000% |

### Icosahedral centres: nearest or smoothing

**Preferred: Pyresample nearest for categories/centre sampling; Gaussian only for justified smoothing.** Nearest gives approximately the same smooth-field RMSE as CDO nearest and UXarray, with lower mean setup and application times. Gaussian reduces this smooth-field error but changes the operation into smoothing; it is not an overlap-conservative substitute. UXarray remains useful for its mesh data model, rather than a measured speed advantage in this nearest adapter.

Measured family: `icosahedral`, shared scale 1024.

| Tool / method | Setup mean (s) | Apply mean (s) | Total mean (min–max), s | Accuracy | Finite coverage |
| --- | --- | --- | --- | --- | --- |
| pyresample_nearest | 0.898 | 0.0201 | 0.918 (0.894–0.931) | RMSE 0.00178 | 100.000% |
| cdo_nearest | 1.59 | 0.171 | 1.77 (1.59–1.98) | RMSE 0.00178 | 100.000% |
| uxarray | 1.1 | 3.92 | 5.02 (4.48–5.66) | RMSE 0.00178 | 100.000% |
| pyresample_gauss | 2.33 | 0.596 | 2.93 (2.66–3.35) | RMSE 0.000728 | 100.000% |

### Icosahedral cell averages: conservative overlap

**Preferred: CDO conservative for a small number of fields; ESMPy when weights are reused many times.** CDO and ESMPy have nearly identical smooth-field RMSE and complete coverage. CDO constructs weights faster; ESMPy applies them faster. Using mean setup + N × mean application gives an illustrative crossover near 257 fields on this fixture. This assumes the same geometry/masks and reusable weights; verify integral conservation independently. TempestRemap/NCO large regional overlap pilots timed out, so this suite supplies no completed large speed ranking for them.

Measured family: `icosahedral`, shared scale 1024.

| Tool / method | Setup mean (s) | Apply mean (s) | Total mean (min–max), s | Accuracy | Finite coverage |
| --- | --- | --- | --- | --- | --- |
| cdo_conservative | 18.7 | 0.277 | 19 (18.6–19.2) | RMSE 0.00124 | 100.000% |
| esmpy | 77.9 | 0.0463 | 77.9 (71.3–83.1) | RMSE 0.00124 | 100.000% |

### Local projected triangular meshes

**Preferred: Xugrid when planar mesh geometry is appropriate; no measured cross-tool winner.** Xugrid is the only adapter in this separate mesh-centred family. Its small smooth-field RMSE and fast application support suitability for this fixture, not superiority over raster or spherical adapters with different targets. Reuse weights to amortize setup; never apply planar lon/lat overlap as though it were spherical.

Measured family: `roms_mesh`, shared scale 1024.

| Tool / method | Setup mean (s) | Apply mean (s) | Total mean (min–max), s | Accuracy | Finite coverage |
| --- | --- | --- | --- | --- | --- |
| xugrid | 39.9 | 0.0665 | 39.9 (38.1–43.7) | RMSE 3.01e-10 | 100.000% |

### Coordinate transformation without raster interpolation

**Preferred: pyproj.** Use pyproj when the requested output is transformed coordinates. It performs a different task from raster reprojection; the table reports maximum round-trip coordinate error instead of field RMSE. Do not rank its speed against raster interpolation.

Measured family: `crs_4326_to_2056`, shared scale 4096.

| Tool / method | Setup mean (s) | Apply mean (s) | Total mean (min–max), s | Accuracy | Finite coverage |
| --- | --- | --- | --- | --- | --- |
| pyproj | 0.00634 | 8.75 | 8.75 (8.46–9.23) | Round-trip max 1.99e-08° | 100.000% |


## Evidence and companion contracts

- [Human-readable guide](https://lukegre.github.io/regridding-benchmarks/tool-guide.html)
- [Machine-readable input contracts](https://lukegre.github.io/regridding-benchmarks/tool_contracts.json)
- [Recommendation rules](https://lukegre.github.io/regridding-benchmarks/tool_recommendations.json)
- [Large-grid evidence](https://lukegre.github.io/regridding-benchmarks/large-results.json)
- [Chunked evidence](https://lukegre.github.io/regridding-benchmarks/chunked-results.json)
- [Small-grid adversarial survey](https://lukegre.github.io/regridding-benchmarks/small-data.html)

In a checkout of lukegre/regridding-benchmarks, the source files are tool_recommendations.json, tool_contracts.json, large_results/combined.json and chunked_results/combined.json. Rebuild this skill and the guide with build_guide.py, or regenerate all Pages output with build_pages.py using the documented Python environment. Do not hand-edit generated recommendations or reinterpret advisory contracts as a formal validator.
