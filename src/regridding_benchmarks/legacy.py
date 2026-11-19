"""Capture the original benchmark edition without requiring benchmark engines."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

SOURCE_REVISION = 'e4a4d263877433859d14dd6c6d91924127dbd54c'


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _safe(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or Path(name).is_absolute():
        raise ValueError(f'Invalid edition path: {name}')
    return path


def _verify(root: Path, files: dict[str, str]) -> None:
    for name, expected in files.items():
        path = _safe(root, name)
        if not path.is_file() or _digest(path) != expected:
            raise ValueError(f'Missing or changed legacy source: {name}')


def build_edition(repo: Path, output: Path) -> dict:
    """Verify and copy the immutable legacy inputs, plus an offline record index.

    Index entries link to unmodified JSON with a JSON Pointer. The index does
    not assert that historical statuses are expected or timings comparable.
    """
    repo, output = Path(repo).resolve(), Path(output).resolve()
    sources = json.loads((repo / 'benchmarks/legacy/sources.manifest').read_text())
    if sources['source_revision'] != SOURCE_REVISION:
        raise ValueError('Unexpected source revision in legacy source manifest')
    _verify(repo, sources['files'])
    historical = json.loads((repo / 'results-manifest.json').read_text())
    _verify(repo, historical)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f'Edition output must be empty: {output}')
    output.mkdir(parents=True, exist_ok=True)
    for name in sources['files']:
        dest = _safe(output, name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_safe(repo, name), dest)
    records = []
    small = json.loads((repo / 'all_results.json').read_text())
    for i, row in enumerate(small):
        records.append({'family': 'small', 'source': 'all_results.json', 'pointer': f'/{i}',
                        'status': row.get('status'), 'package': row.get('package'),
                        'grid': row.get('grid'), 'scenario': row.get('scenario')})
    for path in sorted((repo / 'results').glob('*.json')):
        if not (path.name.startswith(('native_', 'controls_')) or path.name == 'xarray_regrid_controls.json'):
            continue
        rows = json.loads(path.read_text())
        if not isinstance(rows, list):
            continue
        for i, row in enumerate(rows):
            records.append({'family': 'native-control' if path.name.startswith('native_') else 'control',
                            'source': f'results/{path.name}', 'pointer': f'/{i}',
                            'status': row.get('status'), 'package': row.get('package'),
                            'grid': row.get('grid'), 'case': row.get('case')})
    for path in sorted((repo / 'large_results').glob('*.json')):
        row = json.loads(path.read_text())
        if not isinstance(row, dict) or 'status' not in row:
            continue
        records.append({'family': 'shared-grid', 'source': f'large_results/{path.name}',
                        'pointer': '', 'status': row['status'], 'package': row.get('package'),
                        'grid': row.get('grid'), 'scale': row.get('scale')})
    for path in sorted((repo / 'chunked_results').glob('*.json')):
        if path.name == 'combined.json':
            continue  # summary duplicates individual files
        row = json.loads(path.read_text())
        records.append({'family': 'storage' if path.name.startswith('storage_') else
                        'diagnostic' if path.name.startswith('diagnostic_') else 'chunked',
                        'source': f'chunked_results/{path.name}', 'pointer': '',
                        'status': 'historical_record', 'package': row.get('tool'), 'grid': row.get('grid')})
    index = {'schema_version': 1, 'source_revision': SOURCE_REVISION,
             'series': 'legacy: separate historical measurements; do not pool with new runs',
             'unknowns': ['original image digest', 'complete effective resource limits',
                          'complete per-case engine versions', 'small-case fixture hashes'],
             'records': records}
    (output / 'index.json').write_text(json.dumps(index, indent=2, allow_nan=False) + '\n')
    files = dict(sources['files'])
    files['index.json'] = _digest(output / 'index.json')
    manifest = {'schema_version': 1, 'edition': 'legacy', 'source_revision': SOURCE_REVISION,
                'guide': 'TOOL_GUIDE.md', 'index': 'index.json', 'files': files}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def validate_edition(output: Path) -> dict:
    output = Path(output).resolve()
    manifest = json.loads((output / 'manifest.json').read_text())
    if manifest.get('schema_version') != 1 or manifest.get('edition') != 'legacy':
        raise ValueError('Invalid legacy edition manifest')
    _verify(output, manifest['files'])
    index = json.loads(_safe(output, manifest['index']).read_text())
    for record in index['records']:
        path = _safe(output, record['source'])
        if record['source'] not in manifest['files']:
            raise ValueError(f'Unlisted record source: {record["source"]}')
        value = json.loads(path.read_text())
        for part in record['pointer'].split('/')[1:]:
            part = part.replace('~1', '/').replace('~0', '~')
            value = value[int(part)] if isinstance(value, list) else value[part]
    return manifest
