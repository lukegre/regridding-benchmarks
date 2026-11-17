import os
os.environ['MPLCONFIGDIR']='/tmp/geobench-mpl'
import json,csv,collections,importlib.metadata as md
from pathlib import Path
from suite import ROOT
files=sorted((ROOT/'results').glob('*.json'))
rows=[]
for f in files:
 if f.name=='cli_commands.json':continue
 for x in json.loads(f.read_text()):rows.append(dict(source_file=f.name,**x))
(ROOT/'all_results.json').write_text(json.dumps(rows,indent=2))
keys=['package','grid','scenario','case','status','finite_fraction','rmse','max_error','relative_integral_error','seconds','flags','error','source_file']
with (ROOT/'all_results.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(rows)
count=collections.Counter(x['status'] for x in rows)
summary=[]
for p in sorted(set(x['package'] for x in rows)):
 r=[x for x in rows if x['package']==p];c=collections.Counter(x['status'] for x in r)
 summary.append(f"| {p} | {c['completed']} | {c['error']} | {c['not_exercised']} |")
# Raw smooth-case metrics are paired with coverage. Never rank RMSE without coverage/method context.
base=[x for x in rows if x.get('scenario')=='smooth']
table=[]
for x in base:
 metric=f"{x['rmse']:.4g} / {x['finite_fraction']:.1%}" if x['status']=='completed' else ('error' if x['status']=='error' else '—')
 table.append(f"| {x['package']} | {x['grid']} | {metric} |")
versions=[]
for p in ['numpy','scipy','xarray','rasterio','rioxarray','odc-geo','pyresample','healpy','astropy-healpix','earthkit-geo','mir-python','earthkit-utils','xugrid','uxarray']:
 versions.append(f'{p} {md.version(p)}')
text=f'''# Synthetic geospatial interoperability stress tests

Executed 2026-11-17 on Linux x86_64, Python 3.12. Sources: the Confluence survey “Geospatial data interoperability: regridding and reprojection tools”. All observations concern the installed versions and the adapters included here.

**{len(rows)} recorded probes: {count['completed']} completed, {count['error']} raised errors, {count['not_exercised']} combinations deliberately not exercised.** Thus {count['completed']+count['error']} operations were actually attempted. “Completed” means an output was returned, not that it was correct. Errors include intentional malformed-input tests. Unexercised combinations are adapter scope, not proof a library cannot support them. The 16-method matrix includes related wrappers and shared engines; these are not independent implementations.

## What I would use

- **Satellite swaths:** Pyresample with longitude normalization and an explicit radius/missing-data policy. GDAL geolocation warping is an alternative, but crossing the dateline needs particular care.
- **Rectilinear grids:** xarray/SciPy for simple interpolation; xESMF/CDO when periodicity or conservation matters. Rasterio/rioxarray/odc-geo for affine GIS rasters and CRS changes.
- **ROMS-style curvilinear grids:** xESMF, or CDO. Supply real cell corners for conservation; scalar, u, and v locations need separate geometry. Rotation of vector components is an additional step not implemented by scalar remapping.
- **Icosahedral global meshes:** ESMF or TempestRemap for topology-aware conservative remapping. UXarray was convenient for native face data and nearest-neighbour output. Pyresample can sample face centres but does not use cell topology or conserve integrals.
- **HEALPix:** Healpy for native operations; MIR/CDO for cross-grid operations. Store NESTED/RING and intensive/extensive semantics explicitly. Astropy-healpix required a longitude workaround in this environment.
- **Gaussian:** MIR, CDO, or xESMF. A generic rectilinear interpolator still needs longitude wrapping and periodic seam handling.

## Most consequential findings

1. **Astropy-healpix returned huge finite values for negative target longitudes.** For an analytic field ranging approximately 0.8–3.2, raw −180…180 targets gave RMSE **1.406e12**, maximum absolute output **4.481e13**, and 78.3% finite coverage. Wrapping targets to 0…360 gave RMSE **0.00401**, 100% coverage. This reproduced in scalar and array calls. Warnings included divide-by-zero/invalid interpolation weights. This is a numerical failure in this installed version/path, not merely an exception. See `controls_python.json` and the standalone reproducer.
2. **Longitude conventions can silently discard half the globe.** Pyresample nearest on HEALPix centres returned 54.9% finite output with raw 0…360 source longitudes; normalizing to −180…180 raised this to 100%. The Gaussian case improved from 58.3% to 100%. This reflects its required coordinate convention. SciPy had 50% finite output when source and target longitude ranges disagreed; wrapping raised it to 98.6%, with a remaining seam gap requiring explicit cyclic extension.
3. **Wrong HEALPix storage order looks plausible.** Treating NESTED data as RING increased RMSE **0.00402 → 0.658**, without an exception. Incorrect `ud_grade` scaling multiplied an intensive field's mean by **4**. Correct intensive scaling preserved the mean; correct extensive scaling preserved the sum in this case.
4. **Stale xESMF weights are accepted if dimensions match.** Shifting source longitudes by 3° then reusing a saved weight file gave RMSE **0.02292**, versus **0.000282** after rebuilding. Cache keys must include geometry, masks, method and conventions; shape is insufficient.
5. **Conservation worked on actual closed spherical meshes.** ESMPy remapped 1,280 triangular cells to 320 cells with relative integral error **4.24e−16**. TempestRemap remapped its generated icosahedral mesh to a 36×18 global raster with error **1.41e−16**. These are separate geometries and are not an accuracy ranking. NCO applied TempestRemap's weights with identical outputs in the tested cases.
6. **CDO's conservative HEALPix path has an explicit accuracy gate.** It aborts unless `--force` is supplied, warning that HEALPix edges do not follow great circles. The forced smooth-field run returned RMSE **0.01749**; this does not establish exact HEALPix-area conservation. Nearest and bilinear HEALPix runs worked without this override. Bilinear interpolation of the explicit unstructured triangular mesh was rejected clearly.
7. **ROMS corners, boundary coverage and normalization matter.** Conservative remapping with supplied corners worked. Coarse and fine curved boundary polylines do not enclose exactly the same spherical polygon: minimum weight-row sum was **0.99526**, and an unnormalized constant 7 lost up to **0.03316** near boundaries. Identity remapping preserved 7 exactly; `conservative_normed` preserved it to about **1.8e−15**. Therefore the boundary discrepancy is a geometry/normalization effect, not evidence ESMF breaks conservation. Masked coast cells also need deliberate coverage normalization.
8. **Folded curvilinear cells were accepted.** Moving a ROMS corner by 15° still produced an output, but smooth-field RMSE rose to **0.394**. Validate mesh geometry before regridding. Missing ROMS bounds produced an opaque CF-metadata KeyError; staggered u-grid values supplied to rho-grid weights produced a clear shape error.
9. **Xugrid's Cartesian algorithms must not be treated as global spherical remapping.** Local planar barycentric and overlap cases worked. On global lon/lat triangles, barycentric interpolation failed with a zero-size reduction error and planar overlap returned a fully populated but inaccurate result (RMSE **0.543**). This is a suitability limitation of the tested planar workflow, not a promised spherical capability failing.
10. **Dateline-crossing swaths expose GDAL geolocation assumptions.** Raw wrapped longitudes yielded 53.1% target coverage; continuous longitudes yielded 85.1%. The swath does not cover the whole rectangular target, so 100% is not an oracle here. Pyresample's search radius can extrapolate into areas outside its footprint. Do not compare only RMSE or finite coverage across these methods.
11. **Missing values and categorical values need a policy.** UXarray nearest retained NaNs (95.5% finite in the hole case); TempestRemap/NCO weight application propagated NaNs to affected targets (80.4% finite). Bilinear, Gaussian and conservative methods can produce fractional category values. Use nearest neighbour or a categorical aggregation rule when class labels must remain discrete.
12. **CRS axis order is another silent failure mode.** Omitting `always_xy=True` while passing lon,lat to pyproj produced positions about **6,170 km** away from the intended result. Correct EPSG:4326↔2056 round-trip error was about **1.93e−8°**. Invalid latitude with `errcheck=True` raised a useful error. Rasterio's affine reprojection preserved constants on covered pixels.

## Setup and interface friction

- ESMF/CDO/TempestRemap/NCO/Iris installed through an isolated conda-forge environment; the other tools used wheels in an isolated venv. Both lock files are included.
- Documentation name `iris-esmf-regrid` corresponds to PyPI distribution `esmf-regrid`. Iris conservative and bilinear workflows worked; missing 1-D bounds were inferred in the tested regular-grid case.
- Earthkit's high-level xarray path needed a named DataArray, geographic coordinate metadata, and an extra `earthkit-utils` install. A plain earthkit-geo install did not supply the latter for this path. HEALPix and full-Gaussian MIR runs then worked. The config-file path was redirected to the writable workspace/temporary storage.
- Xugrid needed optional `numba-celltree`. Local remapping worked after installation.
- ESMPy connectivity uses zero-based local node indices, despite node IDs being separately supplied. The first adapter attempt used one-based connectivity and failed; correcting the adapter resolved it. This was not counted as a library grid-support failure.
- Rasterio's geolocation-array path needed a `rasterio.crs.CRS` object, whereas the affine path also accepted integer/string CRS forms. Correcting that adapter resolved the initial AttributeError.
- UXarray's wrong face-count probe raised an IndexError during remapping rather than a clear geometry/data mismatch at construction.

## Test design and limits

The common suite uses six source families and nine perturbations each: smooth analytic scalar, constant, NaN holes, explicit mask holes, reversed sample traversal, 0…360 longitudes, duplicate coordinates, one invalid latitude, and a binary category field. The analytic scalar is `2 + cos(lat)cos(lon) + 0.25 sin(2lat) + 0.1 cos(3lon)cos²(lat)`, with angles in radians inside trigonometric functions.

Fixtures: rectilinear 21×31; synthetic ROMS-style warped 21×31; curved dateline-crossing satellite swath 45×25; HEALPix NSIDE=8 (768 pixels); actual triangulated icosphere with 1,280 faces; full Gaussian 32×64. Native probes additionally use independently generated TempestRemap meshes, ROMS corner grids and local projected triangular meshes. Source generation is deterministic. No real satellite files were downloaded: “satellite” means synthetic geolocated swath samples. No memory exhaustion tests were run.

Some hostile inputs deliberately contradict implicit grid metadata. HEALPix values are indexed by pixel number: reversing values without updating ordering is semantic corruption, while changing separate coordinate arrays does not change the native pixel geometry. MIR receives authoritative gridspecs, so conflicting auxiliary coordinates can be ignored. Affine raster adapters sort axes and infer transforms; they do not claim arbitrary 2-D geolocation support. Several methods have different targets, edge behavior, kernels or geometry resolution. Timings are single-run diagnostic wall times, including adapter and sometimes file I/O/import/JIT costs, **not a controlled speed benchmark**. No memory ranking is presented.

Mask adapters convert invalid samples to NaN; Pyresample drops missing source samples before search. xESMF also receives an explicit source mask. These tests assess the documented adapters, not every package's native mask convention. CDO conservative quadrilateral corners are inferred from synthetic centres; the triangular mesh uses actual vertices. Real satellite footprints and real ROMS corner metadata should be used in production. Tests do not cover ROMS vertical coordinates, vector rotation, topology repair, higher-order kernels, reduced Gaussian grids, MPI scaling or all installation platforms.

Pointwise analytic error and area conservation are distinct. Conservative source values here are centre samples rather than exact analytic cell averages, so pointwise RMSE includes representation differences. Integral checks compare the discrete fields with the remapper's spherical cell areas. A completed operation with invalid coordinates or wrong metadata is not automatically a bug: validity depends on which geometry the API treats as authoritative.

## Probe counts

| Adapter or family | Returned output | Raised error | Not exercised |
| --- | ---: | ---: | ---: |
{chr(10).join(summary)}

## Smooth-field results

Each cell below reports **RMSE / finite coverage** for that adapter's target. “—” means no adapter was exercised. These are diagnostic results, not a leaderboard. In particular raw longitude conventions intentionally remain visible; corrected controls are in `controls_python.json`.

| Adapter | Source grid | RMSE / finite coverage |
| --- | --- | --- |
{chr(10).join(table)}

## Versions and artifacts

Python-wheel environment: {', '.join(versions)}. Compiled environment: ESMF 8.9.1, CDO 2.6.5; exact full packages/builds are recorded in `requirements-compiled.lock`.

- `all_results.csv` and `all_results.json`: machine-readable metrics, status, timings and diagnostics.
- `results/*.json`: detailed per-adapter results including warnings and exception traces.
- `results/cli/`: native meshes, weights, source/output NetCDFs and command logs.
- `results/cdo_*/`: generated source/target inputs and CLI stderr.
- `suite.py`, `native.py`, `extra.py`, `controls.py`, `cli_probes.py`: runnable sources.
- `reproduce.sh`: complete suite invocation after creating the two environments.
- `reproduce_astropy.py`: minimal negative-longitude failure/workaround reproducer.
'''
(ROOT/'REPORT.md').write_text(text)
print(dict(total=len(rows),**count))
