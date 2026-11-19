"""CNES structured-grid and scattered-target bilinear adaptations."""
from __future__ import annotations

import hashlib
from time import perf_counter


def _hash(np, array):
    a = np.ascontiguousarray(array)
    return hashlib.sha256(a.tobytes()).hexdigest()


def _oracle(np, lon, lat, values, x, y):
    """Independent bilinear interpolation with an explicitly periodic x axis."""
    x = np.asarray(x) % 360.0
    y = np.asarray(y)
    dx = lon[1] - lon[0]
    dy = lat[1] - lat[0]
    ix = np.floor((x - lon[0]) / dx).astype(int) % len(lon)
    iy = np.clip(np.floor((y - lat[0]) / dy).astype(int), 0, len(lat) - 2)
    fx = ((x - lon[0]) / dx - np.floor((x - lon[0]) / dx))
    fy = (y - lat[iy]) / dy
    jx = (ix + 1) % len(lon)
    return ((1 - fx) * (1 - fy) * values[ix, iy] + fx * (1 - fy) * values[jx, iy]
            + (1 - fx) * fy * values[ix, iy + 1] + fx * fy * values[jx, iy + 1])


def run(case, context):
    start = perf_counter()
    try:
        import numpy as np
        import pyinterp
        import xarray as xr
        import pyinterp.backends.xarray  # registers accessor
    except ImportError as exc:
        return {'status': 'unavailable', 'reason': f'Optional engine unavailable: {exc}',
                'timings': {}, 'metrics': {}}
    imports = perf_counter() - start
    options = case['options']
    operation = options['operation']
    smoke = options.get('smoke', False)
    threads = options['num_threads']
    start = perf_counter()
    step = 5.0 if smoke else 0.25
    lon = np.arange(0, 360, step)
    lat = np.arange(-90 + step / 2, 90, step)
    rng = np.random.default_rng(42)
    data = np.sin(np.radians(2 * lon))[:, None] * np.cos(np.radians(lat))[None, :]
    data = data + .01 * rng.standard_normal(data.shape)
    if operation == 'periodic':
        data = np.broadcast_to(np.cos(np.radians(lon))[:, None], data.shape).copy()
        x = np.array([-10.0, 0.1, 359.9, 370.0])
        y = np.zeros_like(x)
    elif operation == 'points':
        count = 1024 if smoke else 1_000_000
        x = rng.uniform(lon[0], lon[-1], count)
        y = rng.uniform(lat[0], lat[-1], count)
    else:
        target_step = 1.0 if smoke else .1
        x = np.arange(-180, 180, target_step) + target_step / 2
        y = np.arange(-80, 80, target_step) + target_step / 2
    source_hash = _hash(np, np.concatenate((lon, lat)))
    values_hash = _hash(np, data)
    target_hash = _hash(np, np.concatenate((x, y)))
    if operation == 'regrid':
        array = xr.DataArray(data.T, dims=('lat', 'lon'), name='field', coords={
            'lon': ('lon', lon, {'units': 'degrees_east'}),
            'lat': ('lat', lat, {'units': 'degrees_north'})})
    else:
        grid = pyinterp.Grid(pyinterp.Axis(lon, period=360.0), pyinterp.Axis(lat), data)
    fixture = perf_counter() - start
    start = perf_counter()
    if operation == 'regrid':
        output = np.asarray(array.pyinterp.interp(lon=x, lat=y, num_threads=threads).values)
    else:
        output = np.asarray(pyinterp.bivariate(grid, x, y, num_threads=threads))
    application = perf_counter() - start
    if operation == 'regrid':
        # Check a fixed 64 × 64 spread, including longitudes in the periodic seam.
        ix = np.linspace(0, len(x) - 1, min(64, len(x)), dtype=int)
        iy = np.linspace(0, len(y) - 1, min(64, len(y)), dtype=int)
        xx, yy = np.meshgrid(x[ix], y[iy])
        observed = output[np.ix_(iy, ix)]
    else:
        ix = np.linspace(0, len(x) - 1, min(4096, len(x)), dtype=int)
        xx, yy, observed = x[ix], y[ix], output[ix]
    reference = _oracle(np, lon, lat, data, xx, yy)
    finite = np.isfinite(observed) & np.isfinite(reference)
    error = np.abs(observed[finite] - reference[finite])
    metrics = {'coverage': float(np.isfinite(output).mean()),
               'oracle_coverage': float(finite.mean()),
               'oracle_max_abs_error': float(error.max()) if error.size else None,
               'oracle_samples': int(finite.size), 'target_points': int(output.size),
               'num_threads_argument': threads, 'seed': 42,
               'engine_version': getattr(pyinterp, '__version__', 'unknown')}
    return {'status': 'ok', 'timings': {'imports': imports, 'fixture': fixture,
                                         'application': application}, 'metrics': metrics,
            'geometry': {'source_axes_sha256': source_hash, 'source_values_sha256': values_hash,
                         'target_coordinates_sha256': target_hash}}
