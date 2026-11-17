"""Build the self-contained, multi-page GitHub Pages report from recorded results."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / 'docs'


def run(script):
    subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT, check=True)


def nav(current):
    links = [('index.html', 'Large &amp; chunked'), ('small-data.html', 'Small-grid survey'), ('tool-guide.html', 'Tool guide')]
    return '<nav class="site-nav" aria-label="Report pages">' + ''.join(
        f'<a href="{url}"' + (' aria-current="page"' if url == current else '') + f'>{label}</a>'
        for url, label in links) + '</nav>'


def embed_json(value):
    return json.dumps(value, allow_nan=False).replace('</', '<\\/')


for script in ['report.py', 'plot.py', 'build_artifact.py', 'update_figures.py']:
    run(script)
DOCS.mkdir(exist_ok=True)
small = (ROOT / 'geospatial-benchmark-report.html').read_text()
small = small.replace('<title>Geospatial interoperability — synthetic benchmark report</title>', '<title>Small-grid survey — Geospatial regridding benchmarks</title>')
small = small.replace('<header><div class="eyebrow">', '<header>' + nav('small-data.html') + '<div class="eyebrow">', 1)
small = small.replace('Where geospatial tools work.<br>And where they break.', 'Small-grid interoperability survey')
small = small.replace('<nav aria-label="Report sections">', '<nav aria-label="Small-grid sections">')
small = small.replace('<div class="provenance">', '<p><a href="benchmark-source-and-results.tar.gz" download>Download code, inputs, results and logs</a> · <a href="results.csv" download>Small-grid results CSV</a> · <a href="results.json" download>Small-grid results JSON</a></p><div class="provenance">', 1)
site_css = '\n.site-nav{margin:0 0 42px;gap:20px}.site-nav a[aria-current="page"]{color:var(--ink);border-bottom-color:var(--ink)}\n'
small = small.replace('</style>', site_css + '</style>', 1)
(DOCS / 'small-data.html').write_text(small)

large_path = ROOT / 'large_results/combined.json'
if not large_path.exists():
    raise FileNotFoundError('large_results/combined.json is required to build the home page')
run('large_report.py')
large = json.loads(large_path.read_text())
section = (ROOT / 'large-figures.html').read_text().replace(
    '<h2>Setup and interpolation at realistic sizes</h2>',
    '<h2>Setup and interpolation at realistic sizes</h2><p class="note">'
    f'{len(large["records"])} measured repetitions across {len(large["summary"])} successful profiles. Canonical geometry/value hashes verified.</p>')
css = re.search(r'<style>(.*?)</style>', small, re.S).group(1)
chunk_path = ROOT / 'chunked_results/combined.json'
chunk_section = ''
chunk_scripts = ''
if chunk_path.exists():
    chunk = json.loads(chunk_path.read_text())
    chunk_section = (ROOT / 'chunked-figures.html').read_text()
    css += '\n' + (ROOT / 'chunked-figures.css').read_text()
    chunk_scripts = '<script id="chunked-data" type="application/json">' + embed_json(chunk) + '</script><script>\n' + (ROOT / 'chunked-figures.js').read_text() + '\n</script>'
    shutil.copy2(chunk_path, DOCS / 'chunked-results.json')
else:
    raise FileNotFoundError('chunked_results/combined.json is required to build the home page')
css += '\n' + (ROOT / 'large-figures.css').read_text()
home = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Large and chunked benchmarks — Geospatial regridding</title><style>''' + css + '''</style></head><body><header>''' + nav('index.html') + '''<div class="eyebrow">Research engineering / 17 November 2026</div><h1>Geospatial regridding benchmarks</h1><p class="intro">Explore shared larger-grid timings and chunked-array experiments across geospatial regridding tools. Compare timing boundaries, accuracy and execution constraints before choosing a workflow.</p><nav aria-label="Home page sections"><a href="#large-timings">Large-grid timings</a><a href="#chunked-timings">Chunked arrays</a><a href="#downloads">Downloads</a><button class="print" onclick="window.print()">Print / save PDF</button></nav></header><main>''' + section + chunk_section + '''<section id="downloads"><h2>Reproduce and explore</h2><p>The archive contains source code, inputs, recorded results and logs. These pages embed recorded data and do not rerun benchmarks.</p><div class="actions"><a href="benchmark-source-and-results.tar.gz" download>Download code, inputs, results and logs</a><a href="large-results.json" download>Large results JSON</a><a href="large-measurements.csv" download>Large per-repeat CSV</a><a href="chunked-results.json" download>Chunked results JSON</a><a href="results.json" download>Small-grid results JSON</a><a href="results.csv" download>Small-grid results CSV</a></div></section></main><footer>Geospatial regridding benchmarks · Synthetic fixtures · Recorded local runs</footer><script id="large-data" type="application/json">''' + embed_json(large) + '</script><script>\n' + (ROOT / 'large-figures.js').read_text() + '\n</script>' + chunk_scripts + '</body></html>'
(DOCS / 'index.html').write_text(home)
for source, target in [('all_results.csv', 'results.csv'), ('all_results.json', 'results.json'), ('large_results/combined.json', 'large-results.json'), ('large_results/measurements.csv', 'large-measurements.csv')]:
    shutil.copy2(ROOT / source, DOCS / target)
(DOCS / '.nojekyll').touch()
if (ROOT / 'build_guide.py').exists():
    run('build_guide.py')
excluded = {'.git', '.venv', 'compiled', 'mamba-root', 'bin', '__pycache__', 'docs', '.openai', 'finish_large.py'}
with tarfile.open(DOCS / 'benchmark-source-and-results.tar.gz', 'w:gz') as archive:
    for path in sorted(ROOT.iterdir()):
        if path.name not in excluded and path.name != 'geospatial-benchmark-report.html':
            archive.add(path, arcname=path.name, filter=lambda item: None if '__pycache__' in item.name.split('/') else item)
print('Pages output:', DOCS)
