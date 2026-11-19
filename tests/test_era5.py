import importlib.util
import tempfile
import unittest
from pathlib import Path

from regridding_benchmarks.era5 import run


@unittest.skipUnless(all(importlib.util.find_spec(name)
                         for name in ("numpy", "scipy", "xarray", "xarray_regrid")),
                     "optional ERA5 test dependencies missing")
class ERA5Test(unittest.TestCase):
    def test_full_target_and_month_selection_from_netcdf(self):
        import numpy as np
        import xarray as xr

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "monthly.nc"
            latitude = np.arange(90, 44.5, -0.25)
            longitude = np.arange(89.75, 180.25, 0.25)
            times = np.arange("2000-01", "2001-01", dtype="datetime64[M]").astype("datetime64[s]")
            values = (220 + np.arange(12)[:, None, None] + latitude[None, :, None] * 0.1
                      + longitude[None, None, :] * 0.05)
            xr.DataArray(values, dims=("valid_time", "latitude", "longitude"), coords={
                "valid_time": times, "latitude": latitude, "longitude": longitude,
            }, name="d2m", attrs={"units": "K"}).to_netcdf(path, engine="scipy")
            result = run({"options": {"engine": "xarray-regrid", "smoke": False}}, {"dataset_path": path})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["metrics"]["output_shape"], [12, 265, 530])
        self.assertEqual(result["metrics"]["coverage"], 1)
        self.assertLess(result["metrics"]["common_max_difference_k"], 1e-10)
