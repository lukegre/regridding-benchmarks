"""Adapt the published conservative Dask workload to a deterministic field."""

from time import perf_counter

from .comparison import arrays_digest


def run(case, context):
    start = perf_counter()
    try:
        import dask
        import dask.array as da
        import numpy as np
        import xarray as xr
        engine = case["options"]["engine"]
        if engine == "xesmf":
            import xesmf
        else:
            import xarray_regrid  # register the accessor
    except ImportError as error:
        return {"status": "unavailable", "reason": str(error)}

    options = case["options"]
    timings = {"imports": perf_counter() - start}
    start = perf_counter()
    south, north, west, east = options["extent"]
    ntime = options["times"]
    skipna = options["skipna"]

    def grid(step):
        lat_bounds = np.arange(south, north + step, step)
        lon_bounds = np.arange(west, east + step, step)
        return xr.Dataset(coords={
            "lat": ("lat", lat_bounds[:-1] + step / 2, {"units": "degrees_north"}),
            "lon": ("lon", lon_bounds[:-1] + step / 2, {"units": "degrees_east"}),
            "lat_b": ("lat_b", lat_bounds), "lon_b": ("lon_b", lon_bounds),
        })

    source, target = grid(0.25), grid(1)
    field = (2 + np.sin(np.deg2rad(source.lat.values[:, None]))
             + 0.2 * np.cos(np.deg2rad(source.lon.values[None, :])))
    field[field.shape[0] // 2, field.shape[1] // 2] = np.nan
    timings["fixture"] = perf_counter() - start
    start = perf_counter()
    t, y, x = options["chunks"]
    offsets = (np.arange(ntime) % 24) / 100
    lazy_field = (da.from_array(field, chunks=(y, x))[None, :, :]
                  + da.from_array(offsets, chunks=t)[:, None, None]).astype("float32")
    data = xr.DataArray(lazy_field, dims=("time", "lat", "lon"),
                        coords={"time": np.arange(ntime), "lat": source.lat, "lon": source.lon})
    timings["source_graph"] = perf_counter() - start

    if engine == "xesmf":
        start = perf_counter()
        regrid = xesmf.Regridder(source, target, "conservative", unmapped_to_nan=True)
        timings["weights"] = perf_counter() - start
    start = perf_counter()
    if engine == "xesmf":
        lazy = regrid(data, skipna=skipna, na_thres=1.0)
    else:
        lazy = data.regrid.conservative(target.drop_vars(["lat_b", "lon_b"]),
                                        latitude_coord="lat", skipna=skipna, nan_threshold=1.0)
    timings["remap_graph"] = perf_counter() - start
    graph_tasks = len(lazy.data.__dask_graph__())
    start = perf_counter()
    with dask.config.set(scheduler="single-threaded"):
        values = lazy.transpose("time", "lat", "lon").compute().values
    timings["compute"] = perf_counter() - start

    # Independent spherical cell areas and explicit 4×4 overlap for the aligned grids.
    bands = np.diff(np.sin(np.deg2rad(source.lat_b.values)))
    masked = np.isfinite(field)
    weights = np.broadcast_to(bands[:, None], field.shape)
    dims = (target.sizes["lat"], 4, target.sizes["lon"], 4)
    def sum_blocks(array):
        return array.reshape(dims).sum(axis=(1, 3))

    overlap = sum_blocks(weights * masked)
    target_area = sum_blocks(weights)
    complete = masked.reshape(dims).all(axis=(1, 3))
    weighted = sum_blocks(np.where(masked, field, 0) * weights)
    expected_finite = overlap > 0
    fully_covered = np.ones_like(complete)
    offset_fraction = 1.0
    if skipna:
        expected_field = weighted / overlap
    else:
        expected_field = weighted / target_area
        if engine != "xesmf":
            # xarray-regrid 0.4.2 fills NaNs with zero even when skipna=False.
            offset_fraction = overlap / target_area
    if engine == "xesmf":
        # Great-circle edges can make a masked source overlap more than one
        # target and can leave partially covered rows along regional edges.
        # Check mask handling against the operator's actual sparse support.
        coefficients = regrid.weights.data
        valid_coefficients = np.isfinite(coefficients.data) & (coefficients.data != 0)
        rows, cols = coefficients.coords[:, valid_coefficients]
        covered_fraction = np.bincount(rows, weights=coefficients.data[valid_coefficients],
                                       minlength=complete.size).reshape(complete.shape)
        wet = masked.ravel()[cols]
        wet_targets = np.bincount(rows[wet], minlength=complete.size).reshape(complete.shape) > 0
        dry_targets = np.bincount(rows[~wet], minlength=complete.size).reshape(complete.shape) > 0
        expected_finite = wet_targets if skipna else wet_targets & ~dry_targets
        fully_covered = np.isclose(covered_fraction, 1, atol=1e-7, rtol=0)
    finite_cells, mask_mismatches = 0, 0
    max_error, relative_integral_error = 0.0, 0.0
    for sample, offset in zip(values, offsets, strict=True):
        finite = np.isfinite(sample)
        finite_cells += int(finite.sum())
        mask_mismatches += int(np.count_nonzero(finite ^ expected_finite))
        common = finite & expected_finite & fully_covered
        expected_sample = expected_field + offset * offset_fraction
        if common.any():
            max_error = max(max_error, float(np.max(np.abs(sample[common] - expected_sample[common]))))
        domain = finite & complete & fully_covered
        reference_total = np.sum(expected_sample[domain] * target_area[domain])
        if reference_total:
            total = np.sum(sample[domain] * target_area[domain])
            relative_integral_error = max(relative_integral_error, float(abs(total / reference_total - 1)))
    return {
        "status": "ok",
        "timings": timings,
        "geometry": {
            "source_sha256": arrays_digest(np, source.lat_b, source.lon_b),
            "target_sha256": arrays_digest(np, target.lat_b, target.lon_b),
            "fixture_sha256": arrays_digest(np, field, offsets),
        },
        "metrics": {
            "coverage": finite_cells / values.size,
            "finite_mask_mismatches": mask_mismatches,
            "fully_covered_geometry_fraction": float(fully_covered.mean()),
            "common_support_max_error": max_error,
            "complete_cell_relative_integral_error": relative_integral_error,
            "graph_tasks": graph_tasks,
            "source_chunks": [list(axis) for axis in data.chunks],
            "output_shape": list(values.shape),
            "source_evaluation_timed": True,
        },
    }
