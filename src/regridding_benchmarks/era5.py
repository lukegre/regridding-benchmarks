"""Reproduce the ERA5 bilinear comparison from a verified NetCDF snapshot."""

import shutil
import subprocess
from time import perf_counter

from .comparison import arrays_digest


def run(case, context):
    start = perf_counter()
    engine = case["options"]["engine"]
    try:
        import numpy as np
        import xarray as xr
        from scipy.interpolate import RegularGridInterpolator
        if engine == "xesmf":
            import xesmf
        elif engine == "xarray-regrid":
            import xarray_regrid  # register the accessor
    except ImportError as error:
        return {"status": "unavailable", "reason": str(error)}

    cdo = shutil.which("cdo")
    if engine == "cdo" and not cdo:
        return {"status": "unavailable", "reason": "CDO executable is missing"}
    timings = {"imports": perf_counter() - start}
    start = perf_counter()
    smoke = case["options"]["smoke"]
    lat = np.arange(45, 90, 0.17)[:12 if smoke else None]
    lon = np.arange(90, 180, 0.17)[:12 if smoke else None]
    months = np.arange("2000-01", "2001-01", dtype="datetime64[M]")
    if case.get("fixture"):
        source_lat = np.arange(44.75, 47.25, 0.25)
        source_lon = np.arange(89.75, 92.25, 0.25)
        field = xr.DataArray(
            (230 + source_lat[:, None] * 0.2 - source_lon[None, :] * 0.05)[None, :, :],
            dims=("time", "lat", "lon"),
            coords={"time": months[:1].astype("datetime64[s]"), "lat": source_lat, "lon": source_lon},
            attrs={"units": "K"},
        )
    else:
        with xr.open_dataset(context["dataset_path"]) as dataset:
            rename = {key: value for key, value in
                      (("valid_time", "time"), ("latitude", "lat"), ("longitude", "lon"))
                      if key in dataset.dims}
            source = dataset["d2m"].rename(rename).transpose("time", "lat", "lon")
            if not np.array_equal(source.time.values.astype("datetime64[M]"), months):
                raise ValueError("Expected exactly the 12 monthly fields of 2000")
            if source.attrs.get("units") != "K":
                raise ValueError("Expected ERA5 2 m dewpoint in kelvin")
            field = source.assign_coords(lon=source.lon % 360).sortby(["lat", "lon"])
            if smoke:
                field = field.isel(time=slice(0, 1)).sel(
                    lat=slice(lat[0] - 0.25, lat[-1] + 0.25),
                    lon=slice(lon[0] - 0.25, lon[-1] + 0.25),
                )
            field = field.astype("float64").load()
    field = field.rename("d2m")
    field.lat.attrs.update(units="degrees_north", standard_name="latitude")
    field.lon.attrs.update(units="degrees_east", standard_name="longitude")
    target = xr.Dataset(coords={
        "lat": ("lat", lat, field.lat.attrs), "lon": ("lon", lon, field.lon.attrs),
    })
    timings["fixture"] = perf_counter() - start

    start = perf_counter()
    if engine == "xesmf":
        regrid = xesmf.Regridder(field, target, "bilinear", unmapped_to_nan=True)
        timings["weights"] = perf_counter() - start
        start = perf_counter()
        output = regrid(field).transpose("time", "lat", "lon").compute().values
    elif engine == "xarray-regrid":
        output = field.regrid.linear(target).transpose("time", "lat", "lon").compute().values
    else:
        output, cdo_timings = remap_cdo(cdo, field, lat, lon, context["scratch"], xr, np)
        timings.update(cdo_timings)

    if engine != "cdo":
        timings["application"] = perf_counter() - start

    target_lon, target_lat = np.meshgrid(lon, lat)
    interpolator = RegularGridInterpolator(
        (field.lat.values, field.lon.values), field.transpose("lat", "lon", "time").values,
        bounds_error=False, fill_value=np.nan,
    )
    reference = np.moveaxis(interpolator(np.stack((target_lat, target_lon), axis=-1)), -1, 0)
    actual_finite, reference_finite = np.isfinite(output), np.isfinite(reference)
    common = actual_finite & reference_finite
    errors = output[common] - reference[common]
    return {
        "status": "ok", "timings": timings,
        "environment": {"cdo": cdo} if engine == "cdo" else {},
        "geometry": {
            "source_sha256": arrays_digest(np, field.lat.values, field.lon.values),
            "target_sha256": arrays_digest(np, lat, lon),
        },
        "metrics": {
            "output_dtype": str(output.dtype),
            "output_shape": list(output.shape),
            "coverage": float(actual_finite.mean()),
            "common_coverage": float(common.mean()),
            "finite_mask_mismatches": int(np.count_nonzero(actual_finite ^ reference_finite)),
            "common_max_difference_k": float(np.max(np.abs(errors))) if errors.size else None,
            "common_rmse_k": float(np.sqrt(np.mean(errors ** 2))) if errors.size else None,
        },
    }


def remap_cdo(cdo, field, lat, lon, scratch, xr, np):
    start = perf_counter()
    infile, outfile, gridfile = [scratch / name for name in ("source.nc", "output.nc", "grid.txt")]
    field.to_netcdf(infile, engine="scipy", format="NETCDF3_64BIT")
    gridfile.write_text(
        f"gridtype = lonlat\nxsize = {len(lon)}\nysize = {len(lat)}\n"
        f"xfirst = {lon[0]}\nxinc = 0.17\nyfirst = {lat[0]}\nyinc = 0.17\n"
    )
    prepare = perf_counter() - start
    version = subprocess.check_output([cdo, "-V"], stderr=subprocess.STDOUT, text=True)
    print(version.splitlines()[0], flush=True)
    start = perf_counter()
    subprocess.run([cdo, "-P", "1", "-b", "F64", "-f", "nc", f"remapbil,{gridfile}",
                    str(infile), str(outfile)], check=True)
    command = perf_counter() - start
    start = perf_counter()
    with xr.open_dataset(outfile) as dataset:
        output = dataset["d2m"]
        output = output.rename({dimension: dimension[:3] for dimension in output.dims
                                if dimension in {"latitude", "longitude"}})
        if not np.allclose(output.lat, lat) or not np.allclose(output.lon, lon):
            raise ValueError("CDO target coordinates differ from the case")
        values = output.transpose("time", "lat", "lon").values
    return values, {"cli_prepare": prepare, "cli_remap_io": command, "output_read": perf_counter() - start}
