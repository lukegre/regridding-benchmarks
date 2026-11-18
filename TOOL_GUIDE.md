# Which tool for which data?

Choose by data meaning and geometry before comparing speed. A method that returns numbers is not necessarily valid for your quantity. This guide summarizes documented roles and the specific synthetic adapters tested on 2026-11-17; it is not a guarantee for every version or input.

[Large & chunked](docs/index.html) · [Small-grid survey](docs/small-data.html) · [Tool guide](docs/tool-guide.html) · [Agent contracts](tool_contracts.json)

## Choose geometry and method

| Source / task | Starting point | Required decision |
| --- | --- | --- |
| Geolocated swath / scattered centres | Pyresample nearest or Gaussian; GDAL geolocation warp where suitable | Centre sampling does not conserve cell integrals; select radius and footprint policy. |
| Rectilinear 1-D axes or full Gaussian | Xarray axis-based or SciPy point interpolation; xarray-regrid for meridian/parallel conservative cells; xESMF/CDO for their supported spherical geometry; MIR for native Gaussian workflows | Handle longitude seam; use actual cell bounds for conservation. |
| Curvilinear / ROMS | xESMF or CDO with correct centres and real corners | Use separate rho/u/v geometries; rotate vector components separately. |
| Affine raster with CRS change | Rasterio/GDAL, rioxarray or odc-geo | Specify source and destination CRS, transform, shape, nodata and kernel. |
| Global spherical unstructured mesh | ESMPy or TempestRemap for overlap; UXarray or Pyresample for centre-based nearest sampling | Topology-aware area overlap needs valid nodes and faces; planar lon/lat is not spherical geometry. |
| HEALPix | Healpy / astropy-healpix for native operations; MIR or CDO for supported cross-grid operations | Carry nside, RING/NESTED ordering, frame and intensity/total semantics. |
| Local projected mesh | Xugrid planar algorithms | Choose a suitable projected CRS and ensure both meshes share it. |
| Coordinate conversion only | pyproj | Coordinate transformation alone does not regrid field values. |

## Preferred tools: accuracy and speed

Choose quantity semantics, acceptable coverage and geometry first; then compare speed within the valid method. These are conditional recommendations on synthetic data, not universal package rankings.

Arithmetic mean of three measured repeats; total range is min–max of per-repeat setup + application.

Setup and application are separate. Fused APIs include weight/geometry work in application; CDO includes native file I/O and process launch. These are measured workflows, not isolated kernel timings. The local mesh family has different targets and cannot be ranked against raster targets.

RMSE is against a smooth analytic scalar field on each output’s finite cells; it does not measure conservation, categorical correctness, edge preservation or uncertainty. Different coverage can hide difficult cells. Validate error on a common footprint and test real fields before adopting a recommendation.

For repeated fields on fixed grids, estimate setup + N × application rather than multiplying total time by N. Reuse weights only when coordinates, bounds, masks, method and periodicity match. The crossover estimate is illustrative, not a new measured multi-field benchmark.

Chunked choice: use xarray linear for separable rectilinear data, xESMF for curvilinear reusable weights, and odc-geo for the tested tiled lazy CRS workflow. All use the common 4 × 512 × 512 cube. xESMF compute changes from 5.36 s to 0.084 s between (1,128,128) and full-cube chunks, but uses full-horizontal output chunks in both; this is not evidence of distributed spatial output. odc-geo LV95 has four mask differences at (1,256,256). The NetCDF control is warm-cache only. See the chunked results for graph timings and full accuracy checks.

Non-float preferences follow semantics below: nearest for nominal classes, explicit mode for an area-majority class, conservative density/area conversion for counts, and explicit logical rules for flags. The smooth-field RMSE ranking supplies no evidence that bilinear is suitable for these variables.

External benchmark comparison: CNES reverses our historical SciPy/2-D-query xarray ordering; the new 1-D-target control now shows xarray faster locally too; xarray-regrid changes order with chunk layout; cloud tile readers can change Rasterio/rioxarray/odc-geo performance. Consult the External benchmarks page. pyinterp and MBTempest remain untested local candidates, not measured local winners.

xarray-regrid is now measured locally. The new xarray_axes control uses the same canonical destination via 1-D axes, while the historical xarray adapter uses 2-D point queries. All physical grid sizes and hashes remain shared. Conservative xarray-regrid cell edges follow meridians/parallels; ESMF edges are great circles. Its public accessor combines construction and application, so no separate reusable-weight speedup is claimed.

### Rectilinear continuous fields

**Preferred: Xarray with 1-D target axes for linear point interpolation; xarray-regrid conservative for meridian/parallel cells.** The added xarray_axes control is fastest among the measured rectilinear linear adapters, with effectively equal smooth-field RMSE. xarray-regrid linear uses this axis-based xarray machinery with additional formatting; the original xarray adapter used 2-D point queries. All share the same physical grid and values. xarray-regrid conservative has much lower one-call time than CDO/ESMF here, but uses different cell-edge geometry and includes construction on every call. Use CDO/ESMF when their spherical cell representation is required; long fixed-grid series can amortize reusable weights. Do not interpret point-interpolation RMSE as a conservation ranking.

Measured family: `rectilinear`, shared scale 1024.

| Tool / method | Setup mean (s) | Apply mean (s) | Total mean (min–max), s | Accuracy | Finite coverage |
| --- | --- | --- | --- | --- | --- |
| xarray_axes | 0.00101 | 0.0317 | 0.0328 (0.0275–0.0381) | RMSE 1.96e-07 | 100.000% |
| xarray_regrid_linear | 0.00164 | 0.0594 | 0.061 (0.0476–0.0823) | RMSE 1.96e-07 | 100.000% |
| scipy | 0.00474 | 0.0735 | 0.0782 (0.0675–0.0929) | RMSE 1.96e-07 | 100.000% |
| xarray | 0.000769 | 0.0951 | 0.0958 (0.0846–0.109) | RMSE 1.96e-07 | 100.000% |
| xarray_regrid_nearest | 0.0016 | 0.0195 | 0.0211 (0.0203–0.0224) | RMSE 0.000161 | 100.000% |
| xarray_regrid_conservative | 0.00214 | 0.208 | 0.211 (0.169–0.262) | RMSE 3.35e-05 | 100.000% |
| cdo_conservative | 12.7 | 0.267 | 12.9 (12.4–13.5) | RMSE 3.35e-05 | 100.000% |
| iris | 61.7 | 0.0642 | 61.8 (52.7–67.9) | RMSE 3.35e-05 | 100.000% |

### Full Gaussian continuous fields

**Preferred: Xarray 1-D target axes for full Gaussian point interpolation; choose conservative geometry explicitly.** The full Gaussian source has separable axes. The xarray_axes control and xarray-regrid linear are faster here than SciPy with effectively equal smooth-field RMSE. Reduced Gaussian grids are outside this adapter. xarray-regrid conservative is fast and passes a separate meridian/parallel global integral control, but has higher smooth-field RMSE on this Gaussian fixture than CDO/ESMF conservative; centre samples are not exact cell averages, and cell geometry differs. Select by the required integral and geometry rather than one RMSE. MIR remains a candidate for supported native meteorological workflows.

Measured family: `gaussian`, shared scale 1024.

| Tool / method | Setup mean (s) | Apply mean (s) | Total mean (min–max), s | Accuracy | Finite coverage |
| --- | --- | --- | --- | --- | --- |
| xarray_axes | 0.00408 | 0.062 | 0.0661 (0.0626–0.072) | RMSE 1.02e-06 | 100.000% |
| xarray_regrid_linear | 0.00159 | 0.0752 | 0.0768 (0.0708–0.0861) | RMSE 1.02e-06 | 100.000% |
| scipy | 0.016 | 0.136 | 0.152 (0.149–0.158) | RMSE 1.02e-06 | 100.000% |
| xarray_regrid_conservative | 0.00211 | 0.498 | 0.501 (0.477–0.52) | RMSE 2.65e-06 | 100.000% |
| cdo_conservative | 24.7 | 0.344 | 25.1 (24.7–25.7) | RMSE 1.51e-06 | 100.000% |
| xesmf_conservative | 113 | 0.596 | 114 (102–120) | RMSE 1.51e-06 | 100.000% |
| earthkit_mir | 0.0263 | 16.2 | 16.2 (15.1–17.2) | RMSE 1.02e-06 | 100.000% |

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


## Non-float data: choose by semantics, not dtype

- **Categorical identifiers or strings:** Nearest class, with an explicit choice between selecting the nearest cell and retaining its validity versus searching for the nearest valid cell; or an explicitly defined area/distance-weighted mode. Availability of nearest-valid search depends on the tool. Define deterministic ties and an unknown class. Encode labels to integer IDs with a reversible lookup; preserve nodata in a separate validity mask. Use compact codes for identifiers too large for exact float representation (including integers above 2^53); retain the original labels in the lookup and never cast them through float. Never bilinear-interpolate class IDs or round blended labels.
- **Ordinal values:** Use nearest or mode when ordered labels are classes; interpolate only when distances on a numeric scale are meaningful and the resulting values are valid for the application. Do not assume equal spacing between ordinal ranks.
- **Continuous quantity stored as integer:** Convert to floating point and use a continuous method appropriate to geometry, error and conservation; retain scale/offset and units. For CF-packed values, decode scale_factor/add_offset and missingness before interpolation; repack only with an explicit precision and overflow policy. Storage dtype alone does not make a quantity categorical; integer output can lose precision.
- **Extensive counts or totals per cell:** Distribute totals by conservative overlap fractions using cell areas and valid coverage; equivalently remap density then multiply by destination area with consistent normalization. Retain fractional output or use globally constrained rounding if integer totals are required. Ensure areas, masks, covered domain and normalization refer to the same geometry; check total over the common covered domain. For partially covered cells, a coverage-normalized average multiplied by full destination area is not generally conserved; use actual covered area with consistent source and destination masks. Never independently round each interpolated count or assume a weighted average preserves sums.
- **Boolean occupancy:** Use nearest for a sampled state; mode for dominant class; any/all for stated presence semantics; or area fraction as floating point for coverage. Threshold fractions only if an explicit decision threshold is meaningful. Do not choose any/all, mode or fraction interchangeably.
- **Packed bit flags:** Nearest for a representative observation, or unpack each bit and apply documented per-bit any/all/weighted rules; repack after aggregation. Never average or bilinearly interpolate packed flags.
- **Timestamps:** Specify whether values denote instants, intervals or categorical event times, calendar/time zone and missingness; interpolate only when a meaningful temporal model permits, after conversion to a suitable numeric time axis. Use a relative time origin and suitable precision to avoid loss of precision, then restore the calendar and units. Do not blend date encodings blindly or treat intervals as point instants.

## Before running

- Identify source and target geometry, CRS/frame, units, shape and field location before choosing a tool.
- Validate coordinates, uniqueness and order, longitude seam, dimensions and valid topology. Validate actual corners and areas for conservative operations.
- Separate geometry masks from per-variable missing values; reserve a collision-free sentinel or use a separate valid mask.
- Determine intensive versus extensive quantity, coverage, normalization, extrapolation, valid output domain and deterministic tie behavior.
- Test identity, constant, known category and missing-value cases; check finite coverage, edge behavior and area integrals when applicable.
- For reused weights, hash coordinates, topology, bounds, masks, method and periodicity; do not reuse by shape alone.
- For chunked data, distinguish lazy graph construction, weight generation and actual compute; account for rechunking and peak memory.

## Geometry, missing data and execution

For a cell-average intensive quantity, conservative weights generally preserve the area integral over the covered domain, subject to geometry, masks and normalization. For cell totals, divide by source area, remap consistently and multiply by destination area, or use explicit overlap fractions. Compare integrals over the same covered region.

A grid mask defines geometry excluded when weights are built; a per-variable NaN or nodata describes missing field values. They can have different effects. State how partial destination coverage is normalized and whether unmapped cells are missing or extrapolated.

Chunks are an execution strategy, not geometry. A lazy graph is not a computed result. Weight generation, source windows, spatial rechunking and output materialization can dominate memory; verify the exact package version and operation with realistic chunks. See the Large & chunked report for measured cases; absence of a test is not evidence of support or non-support.

Source/destination coordinate systems and units must agree with the operation. Do not infer spatial compatibility from equal array shapes. Validate periodic longitude, unique coordinates, corner orientation and non-self-intersection. Record any datum transformation and axis order.

The large regional TempestRemap overlap generation profiles timed out at 300 s; NCO depended on those same weights. Small native icosahedral-to-raster tests succeeded. This does not establish that NCO application or global meshes are unsupported.

## Small runnable example

```python
# Categorical IDs: keep a separate valid mask and never blend labels.
import numpy as np
from scipy.interpolate import RegularGridInterpolator
lat = np.array([0., 1.]); lon = np.array([10., 11.])
classes = np.array([[1, 2], [1, 2]])  # 1=forest, 2=water
valid = np.array([[True, True], [True, False]])
query = np.array([[0.2, 10.8], [0.9, 10.9], [3., 10.]])  # lat, lon
lookup = RegularGridInterpolator((lat, lon), classes, method="nearest",
                                 bounds_error=False, fill_value=-1)
valid_at = RegularGridInterpolator((lat, lon), valid.astype(float),
                                   method="nearest", bounds_error=False, fill_value=0)
result = lookup(query).astype(int)
result[valid_at(query) == 0] = -1  # explicit unknown; -1 is not a valid class
# result: [2, -1, -1]; retain a reversible ID-to-label table.
```

## Per-tool input contracts

### CDO

- **Use for:** Climate-file remapping of structured, Gaussian and supported unstructured grids.
- **Required input:** CF-like NetCDF/GRIB variables with horizontal dimensions and grid metadata; choose a compatible target grid description. Dimensions and data order must match the declared grid.
- **Geometry and units:** Geographic centres in degrees; provide cell vertices/bounds for conservative work and correct grid type/order, seam and periodicity.
- **Mask and missing data:** Set file missing values and grid masks deliberately; inspect target coverage and normalization.
- **Execution and chunking:** CLI consumes and writes files; weight generation and application can be separate. File I/O is materialized.
- **Tested adapter:** Nearest, bilinear and conservative adapters across the synthetic families; not every grid/method combination succeeded.
- **Non-float method choices:** For supported grids, use remapnn / gennn for nearest class sampling; verify method/grid compatibility. Weighted category mode or flag aggregation needs an explicit workflow.
- **Limits and fallback:** Bilinear on the tested triangular mesh was rejected. HEALPix conservative aborted without --force because edges are not great circles; forcing is not proof of exact conservation.
- **Primary documentation:** [https://code.mpimet.mpg.de/projects/cdo/embedded/index.html](https://code.mpimet.mpg.de/projects/cdo/embedded/index.html)

### xESMF

- **Use for:** Rectilinear or curvilinear latitude/longitude grids, reusable weights and conservative remapping.
- **Required input:** xarray Dataset/DataArray grid with lon/lat 1-D axes or matching 2-D centre arrays in degrees; field horizontal dimensions match grid. Destination has corresponding coordinates.
- **Geometry and units:** Conservative methods require valid cell corners/bounds (lon_b, lat_b or supported CF bounds); check orientation, topology and partial coverage. Set periodic for appropriate global non-conservative grids; handle seam consistently.
- **Mask and missing data:** Grid mask uses ESMF convention 1 valid, 0 masked. It is distinct from per-field NaNs; choose skipna and normalization policy explicitly.
- **Execution and chunking:** Weights may be reused; key them by all coordinates, corners, masks, method and periodicity, not shape. Dask data application is supported; weight construction and spatial chunk behavior depend on version/method. The chunked benchmark explicitly sets output_chunks={'y': 512, 'x': 512}; it does not demonstrate spatially distributed output. In a separate 1024×1024 default-output pilot, 128×128 input chunks produced a warning of 64× more output chunks and the pilot was stopped after about 150 seconds without completing; this is not a completed timing.
- **Tested adapter:** Bilinear, nearest_s2d and conservative on supported structured grids, including ROMS corners.
- **Non-float method choices:** Use method='nearest_s2d' for source-to-destination nearest classes. Weighted mode, bitwise rules and count conservation require a separate explicit workflow; do not use bilinear for labels.
- **Limits and fallback:** Our adapter did not exercise general unstructured xESMF. Missing/folded corners and stale weights can fail or silently degrade results. Scalar remapping does not rotate vectors.
- **Primary documentation:** [https://xesmf.readthedocs.io/en/latest/user_api.html](https://xesmf.readthedocs.io/en/latest/user_api.html) · [https://xesmf.readthedocs.io/en/latest/notebooks/Masking.html](https://xesmf.readthedocs.io/en/latest/notebooks/Masking.html)

### GDAL / Rasterio

- **Use for:** Affine GIS rasters, CRS changes; geolocation-array warping for suitable swaths.
- **Required input:** Raster bands or NumPy arrays with spatial rows/columns, source and destination shape, CRS and affine transform; or explicit 2-D geolocation arrays for the supported warp path. Rasterio geolocation path used CRS objects.
- **Geometry and units:** Provide CRS as EPSG/WKT/CRS object, transform mapping pixel coordinates to CRS coordinates and destination grid. Respect pixel-centre/edge convention; avoid discontinuous longitude for a dateline swath.
- **Mask and missing data:** Set source and destination nodata or masks explicitly; valid pixels and numeric sentinels must not collide.
- **Execution and chunking:** Warp is an eager native operation in tested Rasterio calls; file-backed/windowed workflows need sufficient source overlap and their own memory plan.
- **Tested adapter:** Affine raster reprojection and a separate geolocation-array swath path.
- **Non-float method choices:** Use rasterio.enums.Resampling.nearest or, where supported and appropriate, Resampling.mode. Check tie, nodata and footprint behavior for the installed GDAL version.
- **Limits and fallback:** A swath is not an affine raster; geolocation handling needs explicit support. Dateline coverage was sensitive to longitude continuity. Resampling kernel is not automatically area-conservative.
- **Primary documentation:** [https://rasterio.readthedocs.io/en/stable/topics/reproject.html](https://rasterio.readthedocs.io/en/stable/topics/reproject.html) · [https://gdal.org/en/stable/programs/gdalwarp.html](https://gdal.org/en/stable/programs/gdalwarp.html)

### earthkit-geo / MIR

- **Use for:** ECMWF-style Gaussian and HEALPix grids with authoritative grid specifications.
- **Required input:** A named xarray DataArray with geographic coordinate metadata for the tested high-level path, or a supported MIR/earthkit field and explicit input/output gridspec. Values must follow gridspec order.
- **Geometry and units:** Specify Gaussian grid parameters or HEALPix nside/order as appropriate; coordinates and grid definition must agree. Select a supported destination specification.
- **Mask and missing data:** Define missing data according to the field and interpolation configuration; verify output coverage.
- **Execution and chunking:** Tested calls materialized output; caches and native setup affect timing. Chunked/lazy behavior is API- and version-specific, not established by this adapter.
- **Tested adapter:** Full Gaussian and HEALPix high-level xarray/MIR workflows.
- **Non-float method choices:** Choose a documented nearest-neighbour interpolation supported by the exact gridspec and installed MIR version; verify the configuration and class preservation. Otherwise use a suitable nearest-capable tool.
- **Limits and fallback:** Other families were not exercised by this adapter. The installed high-level xarray path required earthkit-utils and named geographic metadata.
- **Primary documentation:** [https://earthkit-geo.readthedocs.io/en/latest/](https://earthkit-geo.readthedocs.io/en/latest/) · [https://mir.readthedocs.io/en/latest/](https://mir.readthedocs.io/en/latest/)

### Pyresample

- **Use for:** Geolocated swaths or irregular point centres to another swath or area, using neighbour search.
- **Required input:** SwathDefinition with matching 1-D or 2-D lon/lat arrays and data shape, or an AreaDefinition with CRS, extent and shape; target needs an equivalent geometry. Geographic lon/lat are degrees. Scan-based or EWA workflows can impose additional 2-D layout requirements.
- **Geometry and units:** Use longitudes in the documented −180…180 convention and valid latitudes. Specify radius of influence in metres and neighbour/weight parameters. Search uses centres, not cell polygons.
- **Mask and missing data:** Set fill value or masked output; decide whether invalid samples are dropped before search. Radius can extrapolate beyond the observed footprint.
- **Execution and chunking:** Neighbour info may be reused for matching geometry. Dask-capable APIs exist but vary by algorithm; tested standard adapter was eager.
- **Tested adapter:** Nearest and Gaussian centre-based sampling on all six source families.
- **Non-float method choices:** Use kd_tree.resample_nearest for nearest class sampling with an explicit radius and fill value. Gaussian weighted averaging is not a class mode.
- **Limits and fallback:** Does not make a centre-based nearest/Gaussian sample conservative; use polygon-aware remapping for area integrals.
- **Primary documentation:** [https://pyresample.readthedocs.io/en/latest/howtos/swath.html](https://pyresample.readthedocs.io/en/latest/howtos/swath.html) · [https://pyresample.readthedocs.io/en/latest/howtos/geometry_utils.html](https://pyresample.readthedocs.io/en/latest/howtos/geometry_utils.html)

### odc-geo

- **Use for:** Dask-aware xarray reprojection of affine, georeferenced rasters.
- **Required input:** xarray DataArray with spatial y/x dimensions and a valid GeoBox (shape, affine transform, CRS); provide destination GeoBox and resampling.
- **Geometry and units:** Source and destination CRS, pixel geometry and spatial dimension order must agree with array coordinates.
- **Mask and missing data:** Supply nodata consistent with dtype and metadata; choose destination fill and check valid footprint.
- **Execution and chunking:** The tested path chunked y/x and explicitly computed the Dask result. Chunk size and source windows affect memory; graph creation is not completion.
- **Tested adapter:** Affine raster reprojection to an explicit GeoBox.
- **Non-float method choices:** Select resampling='nearest' for classes; use mode only if supported by the exact backend/version and its aggregation semantics fit. Validate nodata and destination dtype.
- **Limits and fallback:** Not a general swath or mesh interface in this adapter; use geolocation or mesh-aware tools when geometry is not affine.
- **Primary documentation:** [https://odc-geo.readthedocs.io/en/latest/](https://odc-geo.readthedocs.io/en/latest/)

### rioxarray

- **Use for:** xarray-facing GIS rasters, CRS metadata and reprojection.
- **Required input:** DataArray/Dataset with identifiable x/y spatial dimensions, CRS (for example rio.write_crs) and transform/coordinates; specify destination CRS or matching raster.
- **Geometry and units:** Rasterio/GDAL affine pixel geometry and CRS must match the array; set spatial dimensions when nonstandard.
- **Mask and missing data:** Use rio nodata/encoded nodata and destination nodata consistently; do not confuse missing values with valid classes.
- **Execution and chunking:** The tested rio.reproject call materialized data. Do not assume Dask-lazy reprojection; use an appropriate lazy alternative and verify its version-specific contract.
- **Tested adapter:** Affine raster reprojection on regular grids.
- **Non-float method choices:** Pass rasterio.enums.Resampling.nearest or supported Resampling.mode to rio.reproject; validate nodata and backend tie handling.
- **Limits and fallback:** A curvilinear/swath grid is not automatically affine; use a geolocation-aware or mesh-aware method.
- **Primary documentation:** [https://corteva.github.io/rioxarray/stable/rioxarray.html#rioxarray.raster_array.RasterArray.reproject](https://corteva.github.io/rioxarray/stable/rioxarray.html#rioxarray.raster_array.RasterArray.reproject)

### SciPy RGI / xarray.interp

- **Use for:** Simple point interpolation on rectilinear axes, including full Gaussian latitude arrays.
- **Required input:** RegularGridInterpolator: strictly ascending or descending 1-D coordinate axes and values with matching leading dimensions; target points in axis order and units. xarray.interp: named dimensions and coordinate labels.
- **Geometry and units:** Coordinates need not be evenly spaced but must be monotonic and unique. Explicitly normalize longitude and extend a cyclic column for global seam interpolation.
- **Mask and missing data:** Define bounds_error/fill_value or xarray extrapolation policy and propagate missing values intentionally.
- **Execution and chunking:** SciPy RGI consumes in-memory numerical arrays in the tested path. xarray may operate on Dask arrays depending on method and chunks; verify compute/memory for the installed version.
- **Tested adapter:** Linear and nearest structured-axis interpolation including full Gaussian grids.
- **Non-float method choices:** Use RegularGridInterpolator(..., method='nearest') or xarray.interp(..., method='nearest') for numeric codes; encode labels compactly and retain the validity mask. Neither provides conservative overlap.
- **Limits and fallback:** Not a CRS transformer, 2-D curvilinear grid, polygon overlap or conservative remapper. Interpolate only after coordinating CRS and units.
- **Primary documentation:** [https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.RegularGridInterpolator.html](https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.RegularGridInterpolator.html) · [https://docs.xarray.dev/en/stable/generated/xarray.Dataset.interp.html](https://docs.xarray.dev/en/stable/generated/xarray.Dataset.interp.html)

### Healpy / astropy-healpix

- **Use for:** Native HEALPix indexing, interpolation or resolution changes.
- **Required input:** One value per pixel with length 12 × nside²; record valid nside, RING or NESTED order, frame and units. astropy coordinates use astropy units/SkyCoord; healpy angular APIs may use theta/phi radians or lonlat degrees.
- **Geometry and units:** Source ordering must match declared order; targets must use the same coordinate frame. Wrap target longitude consistently and handle the seam. Validate nside for the selected order (for example healpy.isnsideok(nside, nest=True)); NESTED requires a power-of-two nside.
- **Mask and missing data:** Healpy UNSEEN/masks and NaNs require explicit handling; preserve validity separately from data.
- **Execution and chunking:** Tested native operations use materialized arrays. Resolution changes need an explicit intensity versus total scaling policy (healpy ud_grade power).
- **Tested adapter:** Healpy and astropy-healpix interpolation on HEALPix; Healpy resolution scaling control.
- **Non-float method choices:** For classes, use healpy.ang2pix and gather by pixel index or astropy-healpix coordinate-to-index and gather; do not use bilinear interpolation of codes. Match nside, order and frame.
- **Limits and fallback:** Wrong ordering returned plausible wrong values. In the installed astropy-healpix path negative longitudes produced huge finite values; wrapping to 0…360 fixed that control. Verify installed version and longitude behavior.
- **Primary documentation:** [https://healpy.readthedocs.io/en/latest/generated/healpy.pixelfunc.ud_grade.html](https://healpy.readthedocs.io/en/latest/generated/healpy.pixelfunc.ud_grade.html) · [https://astropy-healpix.readthedocs.io/en/latest/](https://astropy-healpix.readthedocs.io/en/latest/)

### ESMPy

- **Use for:** Topology-aware spherical grid or mesh remapping, including conservation.
- **Required input:** ESMF Grid or Mesh and Fields at the correct centre/node location, with compatible source/destination dimensions and geometry; add node coordinates, IDs, element types and connectivity for a mesh.
- **Geometry and units:** Supply valid spherical coordinates, element connectivity and corner geometry; in our Mesh adapter connectivity used zero-based local node indices independent of node IDs. Check API/version and decomposition.
- **Mask and missing data:** ESMF grid/mesh masks and unmapped destination policy are separate from field NaNs; define area/coverage normalization.
- **Execution and chunking:** Weight construction and application are separate; native arrays are materialized in the tested serial adapter. Parallel decomposition is outside these tests.
- **Tested adapter:** Conservative closed spherical triangular mesh remapping with integral checks.
- **Non-float method choices:** Select a documented nearest source-to-destination regridding method for compatible field locations; verify the installed ESMPy API and grid/mask support. Use conservative overlap plus area handling for totals.
- **Limits and fallback:** A mesh of points alone cannot provide conservative cell overlap; validate geometry and source/destination field locations.
- **Primary documentation:** [https://earthsystemmodeling.org/esmpy_doc/release/latest/html/](https://earthsystemmodeling.org/esmpy_doc/release/latest/html/)

### TempestRemap / NCO

- **Use for:** Offline spherical mesh overlap weights and file-based weight application.
- **Required input:** TempestRemap source/destination mesh files with node coordinates and cell connectivity, plus field data in compatible NetCDF dimensions/order. NCO applies compatible generated map weights to a matching file.
- **Geometry and units:** Use valid non-self-intersecting cells, matching topology and coordinates; check mesh area, orientation, coverage and map normalization.
- **Mask and missing data:** Encode missing data and masks separately; our weight application propagated NaNs to affected targets. Define unmapped-cell policy.
- **Execution and chunking:** Native command-line mesh/map generation and file-based application; setup and apply can be reused separately. Tested workflow materializes files.
- **Tested adapter:** TempestRemap conservative mesh-to-mesh and mesh-to-raster; NCO applied the same maps and matched outputs.
- **Non-float method choices:** For classes, apply only a map known to encode the desired nearest or categorical aggregation rule; these tested conservative weights average values and are not category mode. Use a nearest-capable tool if necessary.
- **Limits and fallback:** NCO is a weight application path here, not independent weight generation. Conservation depends on geometry and normalization; arbitrary NaN gaps need explicit handling.
- **Primary documentation:** [https://climate.ucdavis.edu/tempestremap.php](https://climate.ucdavis.edu/tempestremap.php) · [https://nco.sourceforge.net/nco.html#ncremap](https://nco.sourceforge.net/nco.html#ncremap)

### Xugrid

- **Use for:** UGRID mesh manipulation and local planar mesh interpolation/overlap.
- **Required input:** xarray data with UGRID topology: node x/y coordinates, face-node connectivity and correctly located face/node values; destination mesh with compatible coordinates.
- **Geometry and units:** Use a suitable projected planar CRS and units for tested Cartesian algorithms; connectivity index base and fill entries must match metadata.
- **Mask and missing data:** Carry mesh masks and missing field values explicitly; verify overlapping valid area.
- **Execution and chunking:** Optional spatial indexing dependencies may be needed; chunk/lazy behavior varies by operation. Tested local workflows used materialized arrays.
- **Tested adapter:** Local planar barycentric and overlap remapping.
- **Non-float method choices:** Choose an explicitly supported nearest or category aggregation operation for the installed version, or use a nearest-capable tool on suitable mesh centres. Tested barycentric/overlap arithmetic is not a class mode.
- **Limits and fallback:** Do not treat the tested Cartesian algorithms on raw global lon/lat as spherical conservative remapping; use ESMPy or TempestRemap for topology-aware spherical overlap.
- **Primary documentation:** [https://deltares.github.io/xugrid/](https://deltares.github.io/xugrid/)

### UXarray

- **Use for:** Native unstructured spherical-grid data and sampling to a target grid.
- **Required input:** Grid/UGRID-style topology and xarray-like data indexed by the correct face/node dimension; target lon/lat in documented units and shape.
- **Geometry and units:** Node coordinates, face connectivity and field location must agree; check face count and longitude convention.
- **Mask and missing data:** Set missing/invalid data explicitly and inspect target coverage; nearest in the test retained NaNs.
- **Execution and chunking:** Tested nearest remap materialized results; check operation-specific Dask behavior before sizing a pipeline.
- **Tested adapter:** Face-centre nearest to a structured target on an icosahedral mesh.
- **Non-float method choices:** Use the documented nearest-neighbour remapping path for face classes, checking input location, output dtype and mask; tested nearest is not conservative.
- **Limits and fallback:** Nearest is not conservative. Wrong face count failed during remapping; validate shape first. Do not infer untested methods from this adapter.
- **Primary documentation:** [https://uxarray.readthedocs.io/en/latest/](https://uxarray.readthedocs.io/en/latest/)

### iris-esmf-regrid

- **Use for:** Iris cubes on supported grids with ESMF-backed bilinear or area-weighted remapping.
- **Required input:** Iris Cube with horizontal coordinates and field dimensions aligned to source grid; supply a compatible target Cube/grid and coordinate system.
- **Geometry and units:** Conservative operation requires cell bounds; supported 1-D bounds may be inferred, but supply real corners for curved cells and verify coordinate units and CRS.
- **Mask and missing data:** Iris masks and ESMF grid masks differ from arbitrary NaNs; choose missing-area tolerance/coverage policy for the scheme.
- **Execution and chunking:** Reusable regridders separate geometry setup from application. Lazy behavior is operation/version-specific; verify actual computed output and chunk sizing.
- **Tested adapter:** Bilinear and conservative Iris workflows on regular grids; 1-D bounds inferred in a control.
- **Non-float method choices:** The tested bilinear and conservative schemes average values; they are not category modes. Use an explicitly supported nearest scheme or a separate nearest-capable tool for class labels.
- **Limits and fallback:** Distribution is named esmf-regrid. Bounds inferred from centres do not establish true curvilinear cell geometry.
- **Primary documentation:** [https://iris-esmf-regrid.readthedocs.io/en/latest/](https://iris-esmf-regrid.readthedocs.io/en/latest/)

### pyproj

- **Use for:** Transform coordinate points between CRSs; prepare geometry for another remapper.
- **Required input:** Source and destination CRS as EPSG, WKT or pyproj CRS; coordinate arrays in the source CRS units, with matching shapes.
- **Geometry and units:** Use Transformer.from_crs(..., always_xy=True) when passing x,y or lon,lat; longitude/latitude degrees for geographic CRS, projected coordinates in CRS units.
- **Mask and missing data:** Check input validity and transformation errors (errcheck=True); propagate validity independently.
- **Execution and chunking:** Coordinate transformations use eager arrays in the tested path; batch points if needed.
- **Tested adapter:** EPSG:4326 to EPSG:2056 and 3857 point transforms with round-trip checks.
- **Non-float method choices:** No value interpolation method: transform the coordinates, then choose a separate nearest, categorical aggregation or conservative remapper according to semantics.
- **Limits and fallback:** Does not resample raster values, calculate overlap, or conserve totals; combine with an appropriate raster or mesh remapper.
- **Primary documentation:** [https://pyproj4.github.io/pyproj/stable/api/transformer.html](https://pyproj4.github.io/pyproj/stable/api/transformer.html)

### xarray-regrid

- **Use for:** Rectilinear labelled arrays with separable 1-D axes; linear/nearest interpolation, meridian/parallel conservative remapping, and categorical coarsening.
- **Required input:** xarray DataArray/Dataset with distinct source and target 1-D coordinate axes matching field dimensions. Geographic axes should be named lat/latitude and lon/longitude for native spherical formatting. Most-common coarsening requires a named DataArray in the tested 0.4.2 workflow and an explicit array of expected labels.
- **Geometry and units:** The tested accessor accepts separable axes, not general ROMS/swath/HEALPix/icosahedral geometry or CRS warps. Conservative bounds are inferred from centres; latitude correction is explicit. Meridian/parallel cells differ from ESMF great-circle cells. Verify inferred edge cells, longitude seam and domain before integral claims.
- **Mask and missing data:** Conservative tests use skipna=True and nan_threshold=1.0. Thresholding is sequential per dimension; missing-cell normalization differs from a geometry mask. Linear/nearest missingness follows xarray interpolation. Preserve a separate validity policy for categorical output.
- **Execution and chunking:** Public accessor calls construct formatting/interpolation machinery and conservative weights during each call; no reusable weight-construction timer is exposed. Large results are labelled fused. Dask graph construction and complete synchronous compute are separate in chunk tests. Conservative retained spatial chunks in tested layouts; linear/nearest rechunked. Lazy input is not a general out-of-core guarantee.
- **Tested adapter:** Version 0.4.2 with acceleration dependencies. Linear, nearest and conservative at shared 512/1024 rectilinear and full Gaussian sizes; all three at common 4×512×512 chunk layouts. Nine small adversarial scenarios per family/method. Separate global integral, count-mode, unnamed-array and integer-ID controls.
- **Non-float method choices:** Use .regrid.nearest(target) with compact category codes and a reversible lookup: our direct int64 IDs above 2^53 lost precision, while compact codes decoded exactly. For categorical coarsening use .regrid.most_common(target, values=labels, fill_value=unknown) on a named DataArray; 0.4.2 documents nondeterministic ties, so supply a different explicit reducer when deterministic ties are required. This is count-based mode, not an area-weighted-mode guarantee. Never linear/conservative-interpolate class IDs; convert extensive totals to density with consistent areas before conservative remapping.
- **Limits and fallback:** No implicit scattered or curvilinear fallback. Bad nonseparable coordinate probes are rejected by our adapter before entering the accessor. Mode is for substantial coarsening, not generic near-resolution interpolation; its documented ties are nondeterministic. Same smooth-field RMSE does not imply identical conservative cell geometry.
- **Primary documentation:** [https://xarray-regrid.readthedocs.io/en/stable/](https://xarray-regrid.readthedocs.io/en/stable/) · [https://xarray-regrid.readthedocs.io/en/stable/autoapi/xarray_regrid/index.html](https://xarray-regrid.readthedocs.io/en/stable/autoapi/xarray_regrid/index.html)

