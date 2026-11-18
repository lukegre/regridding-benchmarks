"""Summarize recorded xarray-regrid extension without rerunning benchmarks."""
import json
from pathlib import Path
root=Path(__file__).parent
large=json.loads((root/'large_results/combined.json').read_text())
chunk=json.loads((root/'chunked_results/combined.json').read_text())
rows=[r for r in large['summary'] if r['package'].startswith('xarray_regrid_') or r['package']=='xarray_axes']
new_chunk=[r for r in chunk['summary'] if r['tool'].startswith('xarray_regrid_')]
controls=json.loads((root/'results/xarray_regrid_controls.json').read_text())
lines=['# xarray-regrid 0.4.2 benchmark extension','',f"Added {sum(r['repeats'] for r in rows)} large-tier repetitions across {len(rows)} profiles, including a separate xarray_axes query-layout control. Added {sum(r['repeats'] for r in new_chunk)} chunked measurements across {len(new_chunk)} profiles, plus 162 small adversarial probes and {len(controls)} targeted usability/numerical controls.",'',
'## Protocol','',
'The source/target coordinates and values are unchanged from the common 512/1024 rectilinear and full Gaussian fixtures. Canonical hashes are checked alongside all existing tools. Each large profile has three serial one-thread runs after a small warmup; imports and fixture preparation are excluded. Existing measured records are retained. The three chunk layouts use the same 4 × 512 × 512 cube and missing patch, synchronous Dask and three repeats.', '',
'The public xarray-regrid accessor does not expose reusable construction separately. Setup is array/API preparation; formatting, boundary handling and weight/interpolation work occur inside application on every call. These profiles are fused, not a claim that conservative weight construction is free. The new xarray_axes control uses 1-D target axes; the historical xarray adapter uses 2-D target query arrays. Both describe identical physical grids. xarray-regrid linear/nearest use xarray interpolation internally.', '',
'Conservative uses latitude_coord="lat", skipna=True and nan_threshold=1.0, with native output chunk defaults. Its cells follow meridians/parallels and inferred bounds; ESMF uses great-circle edges. Smooth-field centre-sample RMSE is not an integral-conservation verdict. No general curvilinear/swath/spherical-mesh or CRS fallback is implied.', '',
'## Large shared grids','', '| Family | Scale | Adapter | Setup mean s | Apply mean s | Total mean s | RMSE | Finite |','| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |']
for r in rows:
 lines.append(f"| {r['grid']} | {r['scale']} | {r['package']} | {r['setup_seconds_mean']:.5f} | {r['apply_seconds_mean']:.5f} | {r['total_seconds_mean']:.5f} | {r['rmse']:.3g} | {r['finite_fraction']:.2%} |")
lines+=['','## Chunked arrays','', 'All added chunked outputs matched their own eager references exactly, including finite masks, across all three repetitions. This does not establish equivalence between different algorithms. Conservative retained spatial output chunks; linear and nearest rechunked. Runtime warnings for invalid divide were observed during conservative computation around missing cells; completed output/mask comparisons still matched the reference. Raw output chunks and task layers are retained.', '', '| Method | Input layout | Graph median s | Compute median s | Tasks | Max finite difference | Mask mismatches |','| --- | --- | ---: | ---: | ---: | ---: | ---: |']
for r in new_chunk:
 c=r['correctness'];lines.append(f"| {r['tool']} | {'×'.join(map(str,r['layout']))} | {r['median_graph_seconds']:.4f} | {r['median_compute_seconds']:.4f} | {r['graph_tasks']} | {c['max_abs_error']} | {c['finite_mask_mismatches']} |")
lines+=['','## Targeted controls and usability','']
for r in controls:
 details={k:v for k,v in r.items() if k not in ('package','case','status','seconds')}
 lines+=['### '+r['case'],'',f"Status: {r['status']}. A returned output is not a correctness verdict.",'','```json',json.dumps(details,indent=2),'```','']
lines+=['The malformed nonseparable bad-latitude small probes are rejected by our adapter before conversion to 1-D coordinates; those errors do not measure library validation. Linear/conservative categorical probes produce fractional labels as expected for inappropriate class methods. Nearest preserves binary class membership but does not guarantee exact class-boundary accuracy or large integer precision. The mode control tests count-based coarsening with no ties; 0.4.2 documents nondeterministic ties, so no deterministic-tie support is claimed.', '',
'## Reproduce only this extension','', 'Install requirements-python.lock into the documented .venv; acceleration dependencies are pinned without upgrading the previous environment.', '', '```sh', '.venv/bin/python run_large.py --scales 512 1024 --repeats 3 --only xarray_regrid_linear xarray_regrid_nearest xarray_regrid_conservative xarray_axes', 'for method in linear nearest conservative; do', '  .venv/bin/python chunked_bench.py xarray_regrid_${method} rectilinear', '  .venv/bin/python suite.py xarray_regrid_${method}', 'done', '.venv/bin/python xarray_regrid_controls.py', '.venv/bin/python chunked_combine.py', '.venv/bin/python summarize_large.py', '.venv/bin/python build_pages.py', '```','', 'Run profiles serially. Set BENCH_ENV_ROOT when the environments are outside the checkout. See the lock files, raw per-profile JSON, shared-grid report, chunked report, guide and external comparison for scope and evidence.','']
(root/'XARRAY_REGRID_REPORT.md').write_text('\n'.join(lines))
print('Generated XARRAY_REGRID_REPORT.md')
