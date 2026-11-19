#!/usr/bin/env bash
set -euo pipefail
# Run inside the image as its default non-root user.
test "$(id -u)" -ne 0
python - <<'PY'
import numpy as np
import xarray as xr
field = xr.DataArray([0.0, 1.0, 2.0], dims=['x'], coords={'x': [0.0, 1.0, 2.0]})
assert np.isclose(field.interp(x=0.5).item(), 0.5)
print('Python interpolation:', np.__version__, xr.__version__)
PY
/opt/benchmark/compiled/bin/python - <<'PY'
import numpy as np
import xarray as xr
import esmpy as ESMF
import xesmf as xe
source = xr.Dataset(coords={'lat': [-1., 0., 1.], 'lon': [0., 1., 2.]})
target = xr.Dataset(coords={'lat': [-0.5, 0.5], 'lon': [0.5, 1.5]})
regrid = xe.Regridder(source, target, 'bilinear')
result = regrid(xr.DataArray(np.ones((3, 3)), dims=('lat', 'lon')))
assert np.allclose(result, 1.0)
print('xESMF interpolation:', ESMF.__version__, xe.__version__)
PY
cdo -V
if [[ ${BENCH_VERIFY_DGGS:-false} == true ]]; then
  PYTHONPATH=/opt/benchmark/source/src python -m unittest discover \
    -s /opt/benchmark/source/tests -p test_workloads.py
  python -c 'import xdggs; print("xdggs:", xdggs.__version__)'
fi
python -m pip freeze
/opt/benchmark/compiled/bin/python -m pip freeze
/opt/benchmark/xhealpixify/bin/python -m pip freeze
sha256sum /opt/benchmark/source/requirements*.lock /opt/benchmark/source/environments/*.lock
