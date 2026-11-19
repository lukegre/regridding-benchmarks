"""Bridge selected historical kernels into the shared runner contract."""
from __future__ import annotations

import importlib
import os
import shutil
import sys
import time
import warnings
from pathlib import Path

from .comparison import arrays_digest
from .legacy import ARCHIVE_DIR


def run(case: dict, context: dict) -> dict:
    opts = case['options']
    family = opts['legacy_family']
    repo = Path(context['repo'])
    archive = repo / ARCHIVE_DIR
    environment_root = Path(os.environ.get('BENCH_ENV_ROOT', repo))
    old_path = os.environ.get('PATH')
    os.environ['PATH'] = os.pathsep.join(filter(None, (str(environment_root / 'compiled/bin'), old_path)))
    sys.path.insert(0, str(archive))
    try:
        if family == 'small':
            return _small(opts, context['scratch'])
        if family == 'shared-grid':
            return _large(opts, environment_root)
        if family == 'native-control':
            return _native(opts)
        if family == 'control':
            return _control(opts, archive)
        if family in ('chunked', 'storage'):
            return _chunked(opts, Path(context['scratch']))
        return {'status': 'unsupported', 'timings': {}, 'metrics': {},
                'reason': f'Legacy {family} runner has not yet been adapted to isolated execution'}
    except ImportError as exc:
        return {'status': 'unavailable', 'timings': {}, 'metrics': {},
                'reason': f'Engine dependency unavailable: {exc}'}
    finally:
        sys.path.pop(0)
        if old_path is None:
            os.environ.pop('PATH', None)
        else:
            os.environ['PATH'] = old_path


def _small(opts: dict, scratch: Path) -> dict:
    start = time.perf_counter()
    import numpy as np
    suite = importlib.import_module('suite')
    pkg, grid, scenario = (opts[k] for k in ('package', 'grid', 'scenario'))
    supported = ('scipy', 'xarray', 'xarray_regrid_', 'pyresample_', 'healpy',
                 'astropy_healpix', 'rasterio', 'rioxarray', 'odc_geo', 'earthkit_mir',
                 'xesmf_', 'cdo', 'cdo_')
    if not any(pkg == s or s.endswith('_') and pkg.startswith(s) for s in supported):
        return {'status': 'unsupported', 'timings': {}, 'metrics': {},
                'reason': 'This historical small-case engine used a separate runner'}
    uses_cdo = pkg.startswith('cdo')
    if uses_cdo and not (shutil.which('cdo') or (suite.ROOT / 'compiled/bin/cdo').is_file()):
        return {'status': 'unavailable', 'reason': 'CDO executable is unavailable'}
    if pkg.startswith('xesmf_'):
        importlib.import_module('xesmf')
    imports = time.perf_counter() - start
    start = time.perf_counter()
    args = suite.sample(grid, scenario)
    fixture_seconds = time.perf_counter() - start
    start = time.perf_counter()
    output = suite.OUT
    try:
        if uses_cdo:
            suite.OUT = scratch
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always')
            result = suite.apply(pkg, grid, scenario, *args[:-1])
    except suite.Unsupported as exc:
        return {'status': 'unsupported', 'timings': {'fixture': fixture_seconds},
                'metrics': {}, 'reason': str(exc)}
    finally:
        suite.OUT = output
    elapsed = time.perf_counter() - start
    extra = {}
    if isinstance(result, tuple):
        result, extra = result
    lo, la, field, mask, tx, ty = args[:-1]
    if hasattr(result, 'coords'):
        result = result.squeeze()
        lon = result.coords.get('longitude', result.coords.get('lon'))
        lat = result.coords.get('latitude', result.coords.get('lat'))
        if lon is None or lat is None:
            raise ValueError('Output coordinates are unavailable')
        lon, lat = suite.xr.broadcast(lon, lat)
        lon, lat = lon.transpose(*result.dims), lat.transpose(*result.dims)
        tx, ty = lon.values, lat.values
        truth = suite.field(tx, ty)
        if scenario == 'constant':
            truth = np.full_like(truth, 7)
        elif scenario == 'categorical':
            truth = (np.sin(np.deg2rad(lon.values)) > 0).astype(float)
        values = result.values
    else:
        values, truth = np.asarray(result), args[-1]
    if values.shape != truth.shape:
        raise ValueError(f'Output shape {values.shape} differs from oracle {truth.shape}')
    finite = np.isfinite(values)
    error = values[finite] - truth[finite]
    metrics = {'finite_fraction': float(finite.mean()),
               'rmse': float(np.sqrt(np.mean(error ** 2))) if error.size else None,
               'max_error': float(np.max(np.abs(error))) if error.size else None,
               'warnings': [str(w.message) for w in captured][:8], **extra}
    timings = {'imports': imports, 'fixture': fixture_seconds}
    setup = extra.get('build_seconds')
    if setup is not None:
        timings['setup'] = setup
        elapsed -= setup
    timings['cli_io_and_remap' if uses_cdo else 'application'] = elapsed
    return {'status': 'ok', 'timings': timings, 'metrics': metrics, 'geometry': {
        'source_sha256': arrays_digest(np, lo, la),
        'target_sha256': arrays_digest(np, tx, ty),
        'input_sha256': arrays_digest(np, field, mask),
    }}


def _large(opts: dict, environment_root: Path) -> dict:
    module = importlib.import_module('large_bench')
    module.ENVROOT = environment_root
    result = module.run(opts['package'], opts['grid'], opts['scale'], 1)
    row = result['runs'][0]
    timings = {'imports': row['import_seconds'], 'fixture': row['input_preparation_seconds'],
               'setup': row['setup_seconds'], 'application': row['apply_seconds']}
    for src, dst in [('io_prepare_seconds', 'io_prepare'), ('output_read_seconds', 'output_read')]:
        if src in row:
            timings[dst] = row[src]
    return {'status': 'ok', 'timings': timings, 'metrics': row,
            'geometry': {k: row[k] for k in ('source_geometry_sha256', 'destination_geometry_sha256',
                                                'values_sha256') if k in row}}


def _chunked(opts: dict, scratch: Path) -> dict:
    import json
    scratch.mkdir(parents=True, exist_ok=True)
    module = importlib.import_module('chunked_storage' if opts['legacy_family'] == 'storage' else 'chunked_bench')
    module.OUT = scratch
    if opts.get('bounded_smoke'):
        base = importlib.import_module('chunked_bench')
        base.N = module.N = 128 if opts['legacy_family'] == 'storage' else 32
        base.LAYOUTS = module.LAYOUTS = [(1, 16, 16)]
        base.REPEATS = module.REPEATS = 1
    output = scratch / opts['source']
    if output.exists():
        output.unlink()
    if opts['legacy_family'] == 'storage':
        module.main()
    else:
        module.run(opts['package'], opts['grid'])
    row = json.loads(output.read_text())
    failures = row.get('failures', [])
    if failures:
        return {'status': 'crash', 'timings': {}, 'metrics': row,
                'reason': str(failures[0].get('error', 'Chunked execution failed'))}
    # The original scripts measure multiple layouts and repeats as a single experiment.
    records = row.get('records', row.get('repeats', []))
    correctness = [r['correctness'] for r in records if 'correctness' in r]
    if correctness:
        row['finite_mask_mismatches'] = max(r['finite_mask_mismatches'] for r in correctness)
        errors = [r['max_abs_error'] for r in correctness if r['max_abs_error'] is not None]
        row['max_abs_error'] = max(errors) if errors else None
        row['finite_values_min'] = min(r['finite_values'] for r in correctness)
    return {'status': 'ok', 'timings': {}, 'metrics': row,
            'geometry': row.get('fixture', {})}


def _native(opts: dict) -> dict:
    previous = sys.argv[:]
    try:
        sys.argv = [str(Path(sys.path[0]) / 'native.py'), 'python']
        native = importlib.import_module('native')
    finally:
        sys.argv = previous
    package, name = opts['package'], opts['control']
    if package == 'ESMPy':
        method, constant = name.removeprefix('icosahedral_').rsplit('_', 1)
        fn = lambda: native.esmf_mesh(method, constant == 'True')
    elif package == 'xESMF':
        fn = lambda: native.roms_conserve(name.removeprefix('roms_conservative_'))
    elif package == 'UXarray':
        fn = lambda: native.ux_mesh(name.removeprefix('icosahedral_'))
    elif package == 'Xugrid':
        fn = lambda: native.xu_mesh(name)
    elif package == 'Rasterio':
        fn = lambda: native.raster_crs(name.removeprefix('4326_to_2056_'))
    elif package == 'Healpy':
        fn = lambda: native.healpy_order(name)
    else:
        return {'status': 'unsupported', 'timings': {}, 'metrics': {}, 'reason': 'Unknown native control'}
    start = time.perf_counter()
    metrics = fn()
    return {'status': 'ok', 'timings': {'application': time.perf_counter() - start}, 'metrics': metrics}


def _control(opts: dict, repo: Path) -> dict:
    # Compile only named functions: these old scripts execute and write files at
    # module import. Their numerical bodies are reused without those side effects.
    import ast
    import numpy as np
    import xarray as xr
    suite = importlib.import_module('suite')
    package, name = opts['package'], opts['control']
    scope = {'np': np, 'xr': xr, 'sample': suite.sample, 'field': suite.field}
    if package.startswith('xarray_regrid_'):
        importlib.import_module('xarray_regrid')  # registers the xarray accessor
        path = repo / 'xarray_regrid_controls.py'
        function = {'closed_global_integral': 'conservation',
                    'categorical_coarsening_unnamed_input': 'mode',
                    'categorical_coarsening_no_ties': 'mode',
                    'large_integer_ids_native': 'large_ids',
                    'large_integer_ids_compact_codes': 'large_ids'}[name]
        arguments = {'categorical_coarsening_unnamed_input': (False,),
                     'large_integer_ids_native': (False,),
                     'large_integer_ids_compact_codes': (True,)}.get(name, ())
    else:
        path = repo / 'controls.py'
        wrapped = name.endswith('_True')
        if package == 'SciPy':
            function, arguments = 'scipy', (wrapped,)
        elif package == 'astropy-healpix':
            function, arguments = 'astropy', (wrapped,)
        elif package == 'Pyresample':
            function, arguments = 'resample', (name.split('_longitude_wrapped_')[0], wrapped)
        else:
            return {'status': 'unsupported', 'timings': {}, 'metrics': {}, 'reason': 'Unknown control'}
    tree = ast.parse(path.read_text(), filename=str(path))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == function]
    if len(functions) != 1:
        raise ValueError(f'Cannot locate legacy control function {function}')
    selected = ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[]))
    exec(compile(selected, str(path), 'exec'), scope)
    start = time.perf_counter()
    result = scope[function](*arguments)
    return {'status': 'ok', 'timings': {'application': time.perf_counter() - start}, 'metrics': result}
