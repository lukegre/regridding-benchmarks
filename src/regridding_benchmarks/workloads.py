"""Optional, offline DGGS workload checks.

These checks deliberately do not download tutorial datasets. Missing optional engines
are recorded as unavailable; numerical and serialization failures remain failures.
"""
from importlib import import_module
import importlib.util
import signal
import subprocess
import sys
from time import perf_counter


def _modules(*names):
    try:
        return [import_module(name) for name in names]
    except ImportError as exc:
        return str(exc)


def run(case, context):
    operation = case['options']['operation']
    if operation == 'xhealpixify':
        return _xhealpixify(case)
    if operation == 'xhealpixify_mur':
        return _xhealpixify_mur(context)
    if operation == 'icon':
        return {'status': 'unavailable', 'timings': {}, 'metrics': {},
                'reason': 'The mutable ICON intake source has no pinned, checksum-verified snapshot or verified pyicon sampling contract.'}
    if operation == 'indexing':
        names = ['numpy', 'healpy']
    elif operation == 'xdggs_indexing':
        names = ['numpy', 'healpy', 'xdggs']
    elif operation == 'wgs84':
        names = ['numpy', 'healpy', 'healpix_geo.nested']
    else:
        names = ['numpy', 'xarray', 'xdggs']
    if operation == 'zarr':
        names.append('zarr')
    elif operation == 'cf':
        names.append('scipy')
    if 'xdggs' in names and importlib.util.find_spec('h3ronpy') is not None:
        # A compiled transitive import can SIGILL before Python can catch it
        # on an emulator or incompatible CPU. Distinguish this from a crash
        # in the actual geometry or round-trip operation.
        probe = subprocess.run([sys.executable, '-c', 'import h3ronpy'], capture_output=True)
        if probe.returncode == -signal.SIGILL:
            sys.stderr.write(probe.stderr.decode(errors='replace'))
            return {'status': 'unavailable', 'timings': {}, 'metrics': {},
                    'reason': 'xdggs dependency h3ronpy raised SIGILL during import on this runtime'}
    modules = _modules(*names)
    if isinstance(modules, str):
        return {'status': 'unavailable', 'timings': {}, 'metrics': {}, 'reason': modules}
    np = modules[0]
    start = perf_counter()
    if operation == 'indexing':
        hp = modules[1]
        nside = int(case['options'].get('nside', 8))
        ring = np.arange(12 * nside * nside, dtype=np.int64)
        nested = hp.ring2nest(nside, ring)
        restored = hp.nest2ring(nside, nested)
        if not np.array_equal(restored, ring) or len(np.unique(nested)) != len(ring):
            raise AssertionError('RING/NESTED permutation is not an identity')
        lon, lat = hp.pix2ang(nside, nested, nest=True, lonlat=True)
        if not np.array_equal(hp.ang2pix(nside, lon, lat, nest=True, lonlat=True), nested):
            raise AssertionError('pixel centre lookup failed')
        metrics = {'cells': int(len(ring)), 'permutation_identity': True, 'centre_lookup_identity': True}
    elif operation == 'xdggs_indexing':
        hp, xdggs = modules[1:]
        level = int(case['options'].get('level', 3))
        nside = 2 ** level
        ids = np.arange(12 * nside * nside, dtype='int64')
        for order in ('ring', 'nested'):
            info = xdggs.HealpixInfo(level=level, indexing_scheme=order)
            lon, lat = hp.pix2ang(nside, ids, nest=order == 'nested', lonlat=True)
            actual = info.geographic2cell_ids(lon=lon, lat=lat)
            np.testing.assert_array_equal(actual, ids)
        metrics = {'cells_per_order': int(len(ids)), 'orders': 2, 'healpy_index_agreement': True}
    elif operation == 'wgs84':
        hp, geo = modules[1:]
        level = int(case['options'].get('level', 3))
        nside = 2 ** level
        # Independent WGS84 geodetic-to-authalic transformation followed by
        # healpy's spherical HEALPix indexing. Avoid cell-boundary test points.
        eccentricity = np.sqrt(1 - (1 - 1 / 298.257223563) ** 2)
        def q(phi):
            sin_phi = np.sin(phi)
            e = eccentricity
            return (1 - e * e) * (sin_phi / (1 - e * e * sin_phi ** 2)
                                   - np.log((1 - e * sin_phi) / (1 + e * sin_phi)) / (2 * e))
        def authalic(latitude):
            return np.rad2deg(np.arcsin(np.clip(q(np.deg2rad(latitude)) / q(np.pi / 2), -1, 1)))
        lon = np.array([-179.5, -120., -45., .3, 42., 130., 179.5])
        lat = np.array([-85., -60., -30., 0., 30., 60., 85.])
        expected = hp.ang2pix(nside, lon, authalic(lat), nest=True, lonlat=True)
        actual = geo.lonlat_to_healpix(lon, lat, level, ellipsoid='WGS84')
        np.testing.assert_array_equal(actual, expected)
        ids = np.arange(12 * nside * nside, dtype='int64')
        geo_lon, geo_lat = geo.healpix_to_lonlat(ids, level, ellipsoid='WGS84')
        spherical_lon, spherical_lat = hp.pix2ang(nside, ids, nest=True, lonlat=True)
        lon_error = np.max(np.abs((geo_lon - spherical_lon + 180) % 360 - 180))
        lat_error = np.max(np.abs(authalic(geo_lat) - spherical_lat))
        if max(lon_error, lat_error) > 1e-9:
            raise AssertionError('WGS84 cell centres differ from authalic-sphere reference')
        metrics = {'reference_points': len(lon), 'centres': len(ids),
                   'max_longitude_error_degrees': float(lon_error),
                   'max_authalic_latitude_error_degrees': float(lat_error)}
    elif operation == 'range_memory':
        import resource
        from xdggs.healpix.moc_index import HealpixMocIndex
        level = int(case['options'].get('level', 8))
        if not 1 <= level <= 20:
            raise ValueError('range profile level must be between 1 and 20')
        # Half-open level-29 ranges cover two separated base cells.  They
        # represent 2 * 4**level cells without materializing a dense array.
        width = 4 ** 29
        ranges = np.array([[0, width], [2 * width, 3 * width]], dtype='uint64')
        index = HealpixMocIndex.from_array(ranges, dim='cells', name='cell_ids',
                                          grid_info=modules[2].HealpixInfo(level=level),
                                          compression='ranges')
        expected = 2 * 4 ** level
        if index.size != expected:
            raise AssertionError('range coverage cardinality differs from expected')
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # macOS reports bytes; Linux reports KiB. This is the process lifetime
        # high-water mark, including imports, rather than an operation delta.
        peak_bytes = peak if sys.platform == 'darwin' else peak * 1024
        metrics = {'level': level, 'covered_cells': int(index.size), 'input_ranges': 2,
                   'index_nbytes': int(index.nbytes), 'process_peak_rss_bytes': int(peak_bytes),
                   'dense_uint64_equivalent_bytes': int(expected * 8)}
    elif operation in ('cf', 'zarr'):
        xr = modules[1]
        # Sparse, deliberately non-consecutive cell IDs and a missing value.
        ids = np.array([0, 3, 17, 95], dtype='int64')
        ds = xr.Dataset({'value': ('cells', np.array([1., np.nan, 3., 4.]))},
                        coords={'cell_ids': ('cells', ids, {'grid_name': 'healpix', 'level': 2, 'indexing_scheme': 'nested'})})
        decoded = ds.dggs.decode()
        encoded = decoded.dggs.encode(convention=operation)
        path = context['scratch'] / ('dggs.zarr' if operation == 'zarr' else 'dggs.nc')
        if operation == 'zarr':
            encoded.to_zarr(path, mode='w')
            reopened = xr.open_zarr(path).load()
        else:
            encoded.to_netcdf(path, engine='scipy')
            reopened = xr.open_dataset(path, engine='scipy').load()
        result = reopened.dggs.decode(convention=operation)
        np.testing.assert_array_equal(result.cell_ids.values, ids)
        np.testing.assert_allclose(result.value.values, ds.value.values, equal_nan=True)
        # Encoding a second time must preserve supported convention metadata.
        reencoded = result.dggs.encode(convention=operation)
        if operation == 'cf':
            if not any(v.attrs.get('grid_mapping_name') == 'healpix' for v in reencoded.variables.values()):
                raise AssertionError('CF HEALPix grid mapping missing')
        else:
            if 'dggs' not in reencoded.attrs:
                raise AssertionError('Zarr DGGS metadata missing')
        metrics = {'cells': len(ids), 'sparse_ids_preserved': True, 'values_and_mask_preserved': True, 'grid_metadata_preserved': True}
    else:
        raise ValueError('unknown workload operation: ' + operation)
    return {'status': 'ok', 'timings': {'apply': perf_counter() - start}, 'metrics': metrics}


def _xhealpixify(case):
    """Regional masked bilinear interpolation versus explicit four-corner weights."""
    from importlib.metadata import PackageNotFoundError, version
    revision = '8ebd09eb7'
    try:
        installed = version('xhealpixify')
    except PackageNotFoundError:
        return {'status': 'unavailable', 'timings': {}, 'metrics': {},
                'reason': 'xhealpixify at commit 8ebd09eb7db4ee4bc9b12f8dd05ccd436986a93c is not installed'}
    if revision not in installed:
        return {'status': 'unavailable', 'timings': {}, 'metrics': {},
                'reason': f'Cannot verify xhealpixify revision from installed version {installed!r}'}
    modules = _modules('numpy', 'xarray', 'healpy', 'xhealpixify')
    if isinstance(modules, str):
        return {'status': 'unavailable', 'timings': {}, 'metrics': {}, 'reason': modules}
    np, xr, hp, xh = modules
    lat = np.arange(-40., 41., 2.)
    lon = np.arange(-40., 41., 2.)
    y, x = np.meshgrid(lat, lon, indexing='ij')
    wet = x * x + y * y > 80
    analytic = np.sin(np.deg2rad(x)) * np.cos(np.deg2rad(y))
    source = xr.Dataset({'value': (('latitude', 'longitude'), np.where(wet, analytic, 1e6)),
                         'wet': (('latitude', 'longitude'), wet)},
                        coords={'latitude': lat, 'longitude': lon})
    nside = 16
    ids = np.arange(hp.nside2npix(nside))
    tx, ty = hp.pix2ang(nside, ids, nest=True, lonlat=True)
    tx = (tx + 180) % 360 - 180
    selected = (abs(tx) < 35) & (abs(ty) < 35)
    ids, tx, ty = ids[selected], tx[selected], ty[selected]
    target = xr.Dataset(coords={'cell_ids': ('cells', ids), 'longitude': ('cells', tx),
                                'latitude': ('cells', ty)})
    start = perf_counter()
    # This operation compiles Numba on first use; setup includes that overhead.
    regridder = xh.HealpyRegridder(source, target, interpolation_kwargs={'mask': 'wet', 'min_vertices': 3})
    setup = perf_counter() - start
    start = perf_counter()
    result = regridder.regrid_ds(source[['value']]).compute()
    raw = result.value.data
    actual = np.asarray(raw.todense() if hasattr(raw, 'todense') else raw)
    apply = perf_counter() - start
    np.testing.assert_array_equal(result.cell_ids.values, ids)
    # Independent regular-grid bracket search, not xHEALPixify's tree or weights.
    ix, iy = np.searchsorted(lon, tx) - 1, np.searchsorted(lat, ty) - 1
    fx, fy = (tx - lon[ix]) / 2, (ty - lat[iy]) / 2
    weights = np.stack([(1-fx)*(1-fy), fx*(1-fy), (1-fx)*fy, fx*fy], axis=1)
    rows = np.stack([iy, iy, iy+1, iy+1], axis=1)
    cols = np.stack([ix, ix+1, ix, ix+1], axis=1)
    valid = wet[rows, cols]
    counts = valid.sum(axis=1)
    weights *= valid
    denom = weights.sum(axis=1)
    baseline = np.divide((weights * analytic[rows, cols]).sum(axis=1), denom,
                         out=np.full(len(ids), np.nan), where=(counts >= 3) & (denom > 0))
    np.testing.assert_array_equal(np.isfinite(actual), np.isfinite(baseline))
    common = np.isfinite(baseline)
    if not common.any() or not np.any(counts == 3) or not np.any(counts < 3):
        raise AssertionError('fixture must exercise wet, partially masked and empty targets')
    max_difference = float(np.max(np.abs(actual[common] - baseline[common])))
    if max_difference > 1e-10:
        raise AssertionError('masked bilinear baseline differs')
    return {'status': 'ok', 'timings': {'setup': setup, 'apply': apply},
            'metrics': {'target_cells': len(ids), 'wet_target_cells': int(common.sum()),
                        'empty_target_cells': int((~common).sum()),
                        'partially_masked_target_cells': int((counts == 3).sum()),
                        'max_common_support_difference': max_difference,
                        'cell_ids_preserved': True},
            'environment': {'xhealpixify_version': installed}}


def _xhealpixify_mur(context):
    """Checksum-pinned MUR coastal field against rectilinear bilinear reference."""
    from importlib.metadata import PackageNotFoundError, version
    try:
        installed = version('xhealpixify')
    except PackageNotFoundError:
        return {'status': 'unavailable', 'timings': {}, 'metrics': {}, 'reason': 'pinned xhealpixify is not installed'}
    if '8ebd09eb7' not in installed:
        return {'status': 'unavailable', 'timings': {}, 'metrics': {}, 'reason': f'Cannot verify xhealpixify revision from {installed!r}'}
    if context.get('dataset_path') is None:
        return {'status': 'unavailable', 'timings': {}, 'metrics': {}, 'reason': 'MUR input absent from verified cache'}
    modules = _modules('numpy', 'xarray', 'healpy', 'xhealpixify', 'pandas')
    if isinstance(modules, str):
        return {'status': 'unavailable', 'timings': {}, 'metrics': {}, 'reason': modules}
    np, xr, hp, xh, pd = modules
    start = perf_counter()
    from .mur import coastal_field

    lat, lon, values, wet = coastal_field(context['dataset_path'], np, pd)
    source = xr.Dataset({'value': (('latitude', 'longitude'), np.where(wet, values, 1e6)),
                         'wet': (('latitude', 'longitude'), wet)}, coords={'latitude': lat, 'longitude': lon})
    corners = hp.ang2vec([-123.9, -120.1, -120.1, -123.9], [35.1, 35.1, 38.9, 38.9], lonlat=True)
    ids = hp.query_polygon(512, corners, nest=True)
    tx, ty = hp.pix2ang(512, ids, nest=True, lonlat=True)
    tx = (tx + 180) % 360 - 180
    keep = (tx > -123.9) & (tx < -120.1) & (ty > 35.1) & (ty < 38.9)
    ids, tx, ty = ids[keep], tx[keep], ty[keep]
    target = xr.Dataset(coords={'cell_ids': ('cells', ids), 'longitude': ('cells', tx), 'latitude': ('cells', ty)})
    load = perf_counter() - start
    start = perf_counter()
    regridder = xh.HealpyRegridder(source, target, interpolation_kwargs={'mask': 'wet', 'min_vertices': 3})
    setup = perf_counter() - start
    start = perf_counter()
    result = regridder.regrid_ds(source[['value']]).compute()
    raw = result.value.data
    actual = np.asarray(raw.todense() if hasattr(raw, 'todense') else raw)
    apply = perf_counter() - start
    np.testing.assert_array_equal(result.cell_ids.values, ids)
    ix, iy = np.searchsorted(lon, tx) - 1, np.searchsorted(lat, ty) - 1
    fx = (tx - lon[ix]) / (lon[ix + 1] - lon[ix])
    fy = (ty - lat[iy]) / (lat[iy + 1] - lat[iy])
    weights = np.stack([(1-fx)*(1-fy), fx*(1-fy), (1-fx)*fy, fx*fy], axis=1)
    rows = np.stack([iy, iy, iy+1, iy+1], axis=1)
    cols = np.stack([ix, ix+1, ix, ix+1], axis=1)
    valid = wet[rows, cols]
    counts = valid.sum(axis=1)
    weights *= valid
    denom = weights.sum(axis=1)
    baseline = np.divide((weights * np.where(valid, values[rows, cols], 0)).sum(axis=1), denom,
                         out=np.full(len(ids), np.nan), where=(counts >= 3) & (denom > 0))
    np.testing.assert_array_equal(np.isfinite(actual), np.isfinite(baseline))
    common = np.isfinite(baseline)
    if not common.any() or not (~common).any() or not (counts == 3).any():
        raise AssertionError('MUR case did not exercise coastline and empty targets')
    difference = float(np.max(np.abs(actual[common] - baseline[common])))
    if difference > 1e-9:
        raise AssertionError('MUR masked bilinear baseline differs')
    return {'status': 'ok', 'timings': {'load': load, 'setup': setup, 'apply': apply},
            'metrics': {'source_wet_cells': int(wet.sum()), 'target_cells': len(ids),
                        'wet_target_cells': int(common.sum()), 'empty_target_cells': int((~common).sum()),
                        'partially_masked_target_cells': int((counts == 3).sum()),
                        'max_common_support_difference_celsius': difference, 'cell_ids_preserved': True},
            'environment': {'xhealpixify_version': installed}}
