"""Generate the offline tool guide and its Markdown companion from advisory contracts."""
from pathlib import Path
import html, json

ROOT = Path(__file__).resolve().parent
contract = json.loads((ROOT / 'tool_contracts.json').read_text())

def esc(s): return html.escape(s, quote=True)

choices = [
 ('Geolocated swath / scattered centres', 'Pyresample nearest or Gaussian; GDAL geolocation warp where suitable', 'Centre sampling does not conserve cell integrals; select radius and footprint policy.'),
 ('Rectilinear 1-D axes or full Gaussian', 'SciPy/xarray for point interpolation; xESMF or CDO for appropriate conservative grids; MIR for supported Gaussian grids', 'Handle longitude seam; use actual cell bounds for conservation.'),
 ('Curvilinear / ROMS', 'xESMF or CDO with correct centres and real corners', 'Use separate rho/u/v geometries; rotate vector components separately.'),
 ('Affine raster with CRS change', 'Rasterio/GDAL, rioxarray or odc-geo', 'Specify source and destination CRS, transform, shape, nodata and kernel.'),
 ('Global spherical unstructured mesh', 'ESMPy or TempestRemap for overlap; UXarray or Pyresample for centre-based nearest sampling', 'Topology-aware area overlap needs valid nodes and faces; planar lon/lat is not spherical geometry.'),
 ('HEALPix', 'Healpy / astropy-healpix for native operations; MIR or CDO for supported cross-grid operations', 'Carry nside, RING/NESTED ordering, frame and intensity/total semantics.'),
 ('Local projected mesh', 'Xugrid planar algorithms', 'Choose a suitable projected CRS and ensure both meshes share it.'),
 ('Coordinate conversion only', 'pyproj', 'Coordinate transformation alone does not regrid field values.')]
intro = 'Choose by data meaning and geometry before comparing speed. A method that returns numbers is not necessarily valid for your quantity. This guide summarizes documented roles and the specific synthetic adapters tested on 2026-11-17; it is not a guarantee for every version or input.'
recommendations = json.loads((ROOT / 'tool_recommendations.json').read_text())
large = json.loads((ROOT / recommendations['evidence']).read_text())
def measured(r):
    result = []
    for package in r['packages']:
        matches = [x for x in large['summary'] if x['grid'] == r['grid'] and x['scale'] == r['scale'] and x['package'] == package]
        if len(matches) != 1: raise ValueError((r['task'], package, len(matches)))
        x = matches[0]
        accuracy = f"RMSE {x['rmse']:.3g}" if x['rmse'] is not None else f"Round-trip max {x['roundtrip_max_degrees']:.3g}°"
        result.append([package, f"{x['setup_seconds_mean']:.3g}", f"{x['apply_seconds_mean']:.3g}", f"{x['total_seconds_mean']:.3g} ({x['total_seconds_min']:.3g}–{x['total_seconds_max']:.3g})", accuracy, f"{100*x['finite_fraction']:.3f}%"])
    return result
recommendation_notes = recommendations['interpretation']
checks = contract['common_validation']
notes = [
 'For a cell-average intensive quantity, conservative weights generally preserve the area integral over the covered domain, subject to geometry, masks and normalization. For cell totals, divide by source area, remap consistently and multiply by destination area, or use explicit overlap fractions. Compare integrals over the same covered region.',
 'A grid mask defines geometry excluded when weights are built; a per-variable NaN or nodata describes missing field values. They can have different effects. State how partial destination coverage is normalized and whether unmapped cells are missing or extrapolated.',
 'Chunks are an execution strategy, not geometry. A lazy graph is not a computed result. Weight generation, source windows, spatial rechunking and output materialization can dominate memory; verify the exact package version and operation with realistic chunks. See the Large & chunked report for measured cases; absence of a test is not evidence of support or non-support.',
 'Source/destination coordinate systems and units must agree with the operation. Do not infer spatial compatibility from equal array shapes. Validate periodic longitude, unique coordinates, corner orientation and non-self-intersection. Record any datum transformation and axis order.',
 'The large regional TempestRemap overlap generation profiles timed out at 300 s; NCO depended on those same weights. Small native icosahedral-to-raster tests succeeded. This does not establish that NCO application or global meshes are unsupported.'
]
example = '''# Categorical IDs: keep a separate valid mask and never blend labels.
import numpy as np
from scipy.interpolate import RegularGridInterpolator
lat = np.array([0., 1.]); lon = np.array([10., 11.])
classes = np.array([[1, 2], [1, 2]])  # 1=forest, 2=water
valid = np.array([[True, True], [True, False]])
query = np.array([[0.2, 10.8], [0.9, 10.9], [3., 10.]])  # lat, lon
lookup = RegularGridInterpolator((lat, lon), classes, method="nearest",
                                 bounds_error=False, fill_value=-1)
valid_at = RegularGridInterpolator((lat, lon), valid.astype(float),
                                   method="nearest", bounds_error=False, fill_value=0)
result = lookup(query).astype(int)
result[valid_at(query) == 0] = -1  # explicit unknown; -1 is not a valid class
# result: [2, -1, -1]; retain a reversible ID-to-label table.'''
# Markdown is generated from the same data and prose as the HTML page.
md=['# Which tool for which data?','',intro,'','[Large & chunked](docs/index.html) · [Small-grid survey](docs/small-data.html) · [Tool guide](docs/tool-guide.html) · [Agent contracts](tool_contracts.json)','','## Choose geometry and method','','| Source / task | Starting point | Required decision |','| --- | --- | --- |']
md += ['| '+ ' | '.join(row)+' |' for row in choices]
rec_md = []
rec_md += ['', '## Preferred tools: accuracy and speed', ''] + [n+'\n' for n in recommendation_notes]
for r in recommendations['recommendations']:
 rec_md += ['### '+r['task'], '', '**Preferred: '+r['preferred']+'.** '+r['reason'], '', f"Measured family: `{r['grid']}`, shared scale {r['scale']}.", '', '| Tool / method | Setup mean (s) | Apply mean (s) | Total mean (min–max), s | Accuracy | Finite coverage |', '| --- | --- | --- | --- | --- | --- |']
 rec_md += ['| '+' | '.join(row)+' |' for row in measured(r)] + ['']
md += rec_md
md += ['', '## Non-float data: choose by semantics, not dtype','']
for x in contract['semantic_policy']:
 md += [f"- **{x['semantics']}:** {x['scheme']} {x['avoid']}"]
md += ['', '## Before running', ''] + ['- '+s for s in checks]
md += ['', '## Geometry, missing data and execution', ''] + [s+'\n' for s in notes]
md += ['## Small runnable example', '', '```python',example,'```','','## Per-tool input contracts','']
labels=[('fit','Use for'),('inputs','Required input'),('geometry','Geometry and units'),('missing','Mask and missing data'),('execution','Execution and chunking'),('tested_adapter','Tested adapter'),('nonfloat_method','Non-float method choices'),('unsupported_or_fallback','Limits and fallback')]
for t in contract['tools']:
 md += ['### '+t['name'],''] + [f"- **{label}:** {t[key]}" for key,label in labels] + ['- **Primary documentation:** '+ ' · '.join(f'[{u}]({u})' for u in t['documentation']),'']
(ROOT/'TOOL_GUIDE.md').write_text('\n'.join(md)+'\n')
skill = [
 '---', 'name: select-geospatial-regridding-tool',
 'description: Choose geospatial remapping tools and interpolation schemes using grid geometry, quantity semantics, accuracy, coverage, measured speed and weight reuse. Covers rectilinear, ROMS, satellite swath, Gaussian, HEALPix, icosahedral, projected mesh, CRS and chunked workflows.',
 '---', '', '# Select a geospatial regridding tool', '',
 'Use this skill when selecting or implementing a regridding/reprojection workflow. Treat the preferences below as conditional evidence from synthetic fixtures measured on 2026-11-17. Do not infer support, accuracy or performance for untested inputs.', '',
 '## Workflow', '',
 '1. Inspect the input and requested output. Record variable meaning and units; dtype, scale/offset and nodata; dimensions and coordinate order; source/target CRS and datum; grid topology and cell location; masks; target extent/resolution; chunk layout; and number of fields sharing geometry. Infer these from metadata where reliable; ask only for requirements that cannot be inferred.',
 '2. Choose semantics before software: distinguish point samples, cell averages, cell totals, labels, probabilities and flags. Decide the required coverage, conservation property, missing-data policy and error tolerance. Use the non-float rules below.',
 '3. Match the grid to a preferred workflow below. Compare only methods that satisfy those requirements. Use the full Gaussian recommendation only for separable axes, a planar mesh algorithm only in an appropriate projected CRS, and structured-swath interpolation only with valid cell geometry.',
 '4. Read the selected tool’s required input contract in tool_contracts.json, including required_input_fields, nonfloat_method, geometry, missing and execution. Check the installed version against primary documentation. Supply real corners for conservative remapping; carry HEALPix nside/order/frame; distinguish ROMS rho/u/v grids; rotate vectors separately. Never invent a CRS or corners to make an adapter accept the data.',
 '5. Optimize within the valid method. For one field compare setup + application; for N fixed-grid fields estimate setup + N × application. Reuse weights only with matching coordinates, bounds, masks, method and periodicity. For chunked data inspect the actual graph, spatial rechunking and output chunks; time complete compute, not only lazy graph construction.',
 '6. Validate a representative subset before the full run. Check finite-mask agreement, common-footprint error, range/positivity where required, class membership, missing-data behavior and chunk-boundary agreement. Check area integrals over a common covered domain for conservation. Smooth-field RMSE alone is insufficient.',
 '7. Run the workflow, retaining setup, graph construction, compute and I/O timing boundaries separately. Record geometry/value hashes, package versions, hardware/thread/scheduler settings, chunk layouts and repeat variability. Keep failed and incomplete runs out of successful timing summaries.',
 '8. Report the selected tool and method, why they satisfy the quantity/grid, the measured evidence and its limits, the alternatives, validation results and any remaining uncertainty. When evidence is missing, state that no measured winner exists and propose a bounded comparison with identical fixtures.', '',
 '## Non-float rules', '']
skill += [f"- **{x['semantics']}:** {x['scheme']} {x['avoid']}" for x in contract['semantic_policy']]
skill += ['', '## Input validation', ''] + ['- '+x for x in checks]
skill += rec_md
skill += ['', '## Evidence and companion contracts', '',
 '- [External benchmark comparison](https://lukegre.github.io/regridding-benchmarks/comparison.html)',
 '- [Human-readable guide](https://lukegre.github.io/regridding-benchmarks/tool-guide.html)',
 '- [Machine-readable input contracts](https://lukegre.github.io/regridding-benchmarks/tool_contracts.json)',
 '- [Recommendation rules](https://lukegre.github.io/regridding-benchmarks/tool_recommendations.json)',
 '- [Large-grid evidence](https://lukegre.github.io/regridding-benchmarks/large-results.json)',
 '- [Chunked evidence](https://lukegre.github.io/regridding-benchmarks/chunked-results.json)',
 '- [Small-grid adversarial survey](https://lukegre.github.io/regridding-benchmarks/small-data.html)', '',
 'In a checkout of lukegre/regridding-benchmarks, the source files are tool_recommendations.json, tool_contracts.json, large_results/combined.json and chunked_results/combined.json. Rebuild this skill and the guide with build_guide.py, or regenerate all Pages output with build_pages.py using the documented Python environment. Do not hand-edit generated recommendations or reinterpret advisory contracts as a formal validator.', '']
skill_path = ROOT / 'skills/regridding-tool-selection/SKILL.md'
skill_path.parent.mkdir(parents=True, exist_ok=True)
skill_text = '\n'.join(skill)
skill_path.write_text(skill_text)
(ROOT/'docs/tool-selection-skill.md').write_text(skill_text)
css='''
:root{color-scheme:light;--ink:#172b35;--muted:#526570;--paper:#f5f7f7;--line:#d9e2e5;--accent:#075e65;--warm:#a65328}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,-apple-system,sans-serif}a{color:var(--accent);overflow-wrap:anywhere}header,main,footer{max-width:1180px;margin:auto;padding:36px 28px}header{padding-top:64px;padding-bottom:24px}.eyebrow{letter-spacing:.14em;font-size:12px;font-weight:700;color:var(--accent);text-transform:uppercase}h1{font-size:clamp(32px,5vw,56px);line-height:1.1;letter-spacing:-.045em;max-width:820px;margin:18px 0}h2{font-size:27px;letter-spacing:-.025em;margin:0 0 20px}h3{font-size:21px;margin:20px 0 12px}p{max-width:900px}.intro{font-size:19px;color:var(--muted);max-width:850px}nav{display:flex;gap:24px;flex-wrap:wrap;margin-top:30px}nav a{text-decoration:none;border-bottom:2px solid var(--accent);padding:6px 0;font-weight:600}nav a[aria-current]{color:var(--ink);border-color:var(--warm)}section{padding:42px 0;border-bottom:1px solid var(--line);scroll-margin-top:24px}li{padding-left:5px;margin-bottom:14px}code,pre{background:#e9eef0;border-radius:3px;font-size:.88em}code{padding:2px 5px;overflow-wrap:anywhere}pre{padding:18px;overflow:auto;max-width:100%}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px}th{text-align:left;background:#e8edef;font-weight:600}th,td{padding:12px;border-bottom:1px solid var(--line);vertical-align:top}td{overflow-wrap:anywhere}details{background:white;border:1px solid var(--line);border-radius:6px;margin:12px 0;padding:16px 20px}summary{cursor:pointer;font-weight:700;font-size:18px}dl{margin-bottom:0}dt{font-weight:700}dd{margin:2px 0 14px}a:focus-visible,summary:focus-visible{outline:3px solid #367caa;outline-offset:3px}footer{color:var(--muted);font-size:14px}@media(max-width:700px){header,main,footer{padding-left:18px;padding-right:18px}th,td{padding:10px}}@media print{body{background:white}details{break-inside:avoid}nav{display:none}}
'''
out=['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Which tool for which data?</title><style>'+css+'</style></head><body>',
 '<header><div class="eyebrow">Geospatial interoperability · practical guide</div><h1>Which tool for which data?</h1><p class="intro">'+esc(intro)+'</p><nav aria-label="Report pages"><a href="index.html">Large &amp; chunked</a><a href="small-data.html">Small-grid survey</a><a href="tool-guide.html" aria-current="page">Tool guide</a><a href="comparison.html">External benchmarks</a></nav><nav aria-label="On this page"><a href="#recommendations">Preferred tools</a><a href="#choose">Choose a method</a><a href="#semantics">Non-float data</a><a href="#validate">Validate inputs</a><a href="#contracts">Tool contracts</a></nav></header><main>',
 '<section id="choose"><h2>Choose geometry and method</h2><div class="table-wrap"><table><thead><tr><th scope="col">Source or task</th><th scope="col">Starting point</th><th scope="col">Required decision</th></tr></thead><tbody>']
for row in choices: out.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>')
out += ['</tbody></table></div></section><section id="recommendations"><h2>Preferred tools: accuracy and speed</h2>']
out += ['<p>'+esc(n)+'</p>' for n in recommendation_notes]
out += ['<p><a href="index.html#large-timings">Explore large timing evidence</a> · <a href="index.html#chunked-timings">Explore chunked evidence</a> · <a href="tool_recommendations.json" download>Download recommendation rules</a> · <a href="tool-selection-skill.md" download>Download agent skill (Markdown)</a> · <a href="comparison.html">Compare external benchmarks</a></p>']
for r in recommendations['recommendations']:
 out += ['<article><h3>'+esc(r['task'])+'</h3><p><strong>Preferred: '+esc(r['preferred'])+'.</strong> '+esc(r['reason'])+'</p><p class="note">Measured family: '+esc(r['grid'])+'; shared scale '+str(r['scale'])+'.</p><div class="table-wrap"><table><thead><tr>'+''.join('<th scope="col">'+h+'</th>' for h in ['Tool / method','Setup mean (s)','Apply mean (s)','Total mean (min–max), s','Accuracy','Finite coverage'])+'</tr></thead><tbody>']
 out += ['<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in measured(r)]
 out += ['</tbody></table></div></article>']
out += ['</section><section id="semantics"><h2>Non-float data: choose by semantics, not dtype</h2><p>Native acceptance of integer arrays does not preserve classes or totals. Define the output meaning first.</p><div class="table-wrap"><table><thead><tr><th scope="col">Meaning</th><th scope="col">Scheme</th><th scope="col">Avoid</th></tr></thead><tbody>']
for x in contract['semantic_policy']: out.append('<tr>'+''.join('<td>'+esc(x[k])+'</td>' for k in ('semantics','scheme','avoid'))+'</tr>')
out += ['</tbody></table></div></section><section id="validate"><h2>Before running</h2><ul>'] + ['<li>'+esc(s)+'</li>' for s in checks] + ['</ul><h3>Geometry, missing data and execution</h3>'] + ['<p>'+esc(s)+'</p>' for s in notes] + ['<details><summary>Runnable categorical example</summary><p>This nearest-neighbour example selects the nearest source cell, including its validity; it does not search for the nearest valid cell.</p><pre><code>'+esc(example)+'</code></pre></details></section><section id="contracts"><h2>Per-tool input contracts</h2><p>Expand a tool for input shape, geometry, missing data, execution, tested scope and limitations. These are advisory descriptions; consult the linked primary documentation for your version. <a href="tool_contracts.json" download>Download the machine-readable contracts</a>.</p>']
for t in contract['tools']:
 out += ['<details><summary>'+esc(t['name'])+'</summary><dl>']
 for key,label in labels: out += ['<dt>'+esc(label)+'</dt><dd>'+esc(t[key])+'</dd>']
 out += ['<dt>Primary documentation</dt><dd>'+ ' · '.join('<a href="'+esc(u)+'">'+esc(u)+'</a>' for u in t['documentation'])+'</dd></dl></details>']
out += ['</section></main><footer>Tool contracts are advisory and version-sensitive. Benchmark evidence and reproduction details are in the linked reports.</footer></body></html>']
(ROOT/'docs').mkdir(exist_ok=True)
(ROOT/'docs/tool-guide.html').write_text('\n'.join(out))
(ROOT/'docs/tool_recommendations.json').write_text(json.dumps(recommendations,indent=2)+'\n')
(ROOT/'docs/tool_contracts.json').write_text(json.dumps(contract,indent=2,ensure_ascii=False)+'\n')
print('Generated TOOL_GUIDE.md and docs/tool-guide.html')
