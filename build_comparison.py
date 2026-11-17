"""Render the sourced external comparison in HTML and Markdown.

Input is external_comparisons.json; no source claims are invented here.
"""
from pathlib import Path
from urllib.parse import urlsplit
import html
import json
import shutil

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / 'docs'
source = ROOT / 'external_comparisons.json'
data = json.loads(source.read_text(encoding='utf-8'))


def esc(value):
    return html.escape(str(value), quote=True)


def url(value):
    parts = urlsplit(value)
    if parts.scheme not in ('http', 'https') or not parts.netloc:
        raise ValueError(f'Expected an absolute HTTP(S) source URL: {value!r}')
    return value


def md(value):
    # Escape Markdown punctuation in source data while preserving ordinary prose.
    return str(value).replace('\\', '\\\\').replace('[', '\\[').replace(']', '\\]')


def list_html(values):
    return '<ul>' + ''.join('<li>' + esc(item) + '</li>' for item in values) + '</ul>'


sources = data['sources']
for item in sources:
    url(item['url'])
nav = [('index.html', 'Large &amp; chunked'), ('small-data.html', 'Small-grid survey'),
       ('tool-guide.html', 'Tool guide'), ('comparison.html', 'External benchmarks')]
nav_html = '<nav class="site-nav" aria-label="Report pages">' + ''.join(
    f'<a href="{href}"' + (' aria-current="page"' if href == 'comparison.html' else '') + f'>{label}</a>'
    for href, label in nav) + '</nav>'
css = '''
:root{color-scheme:light;--ink:#172b35;--muted:#526570;--paper:#f5f7f7;--line:#d9e2e5;--accent:#075e65}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,-apple-system,sans-serif}a{color:var(--accent)}header,main,footer{max-width:1180px;margin:auto;padding:36px 28px}header{padding-top:64px;padding-bottom:24px}.site-nav{display:flex;gap:20px;flex-wrap:wrap;margin:0 0 42px}.site-nav a{text-decoration:none;border-bottom:2px solid var(--accent);padding:6px 0;font-weight:600}.site-nav a[aria-current=page]{color:var(--ink);border-bottom-color:var(--ink)}.eyebrow{text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:700;color:var(--accent)}h1{font-size:clamp(32px,5vw,56px);line-height:1.1;letter-spacing:-.045em;max-width:820px;margin:18px 0}h2{font-size:27px;letter-spacing:-.025em;margin:0 0 20px}h3{font-size:21px;margin:0 0 12px}p{max-width:900px}.intro{font-size:19px;color:var(--muted);max-width:850px}section{padding:42px 0;border-bottom:1px solid var(--line);scroll-margin-top:24px}.note,footer{color:var(--muted);font-size:14px}.cards{display:grid;gap:18px}.card{background:white;border:1px solid var(--line);border-radius:7px;padding:22px;overflow-wrap:anywhere}.card h4{font-size:15px;margin:18px 0 4px}.card p,.card ul{margin-top:4px}.meta{color:var(--muted);font-size:14px}.filters{display:flex;flex-wrap:wrap;gap:18px;margin:20px 0}label{display:flex;flex-direction:column;gap:6px;font-size:14px;font-weight:600}select{font:inherit;border:1px solid #9badb6;border-radius:5px;padding:10px 12px;background:white;color:var(--ink)}select:focus-visible,a:focus-visible{outline:3px solid #367caa;outline-offset:3px}li{margin-bottom:8px}[hidden]{display:none!important}@media(max-width:700px){header,main,footer{padding-left:18px;padding-right:18px}.card{padding:16px}}@media print{nav,.filters{display:none}body{background:white}.card{break-inside:avoid}}
'''
content = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>External comparison — Geospatial regridding benchmarks</title><style>', css, '</style></head><body><header>', nav_html, '<div class="eyebrow">Research engineering / external evidence</div><h1>How these results compare</h1><p class="intro">', esc(data['introduction']), '</p><p class="note">Sources accessed ', esc(data['accessed']), '. Workloads, hardware, methods and timing boundaries vary; these sources do not establish a universal ranking.</p></header><main><section id="synthesis"><h2>What the external evidence adds</h2><div class="cards">']
for item in data['synthesis']:
    content += ['<article class="card"><h3>', esc(item['title']), '</h3><p>', esc(item['finding']), '</p><p><strong>Implication:</strong> ', esc(item['implication']), '</p></article>']
content += ['</div></section><section id="sources"><h2>Sources and comparisons</h2><div class="filters"><label>Relation to our results<select id="relation-filter"><option value="">All relations</option>']
for relation in sorted({s['relation'] for s in sources}):
    content += ['<option value="', esc(relation), '">', esc(relation), '</option>']
content += ['</select></label><label>Topic<select id="topic-filter"><option value="">All topics</option>']
for topic in sorted({topic for s in sources for topic in s['topics']}):
    content += ['<option value="', esc(topic), '">', esc(topic), '</option>']
content += ['</select></label></div><p class="note" id="source-count" role="status" aria-live="polite"></p><div class="cards">']
for item in sources:
    topics = json.dumps(item['topics'], ensure_ascii=False)
    extra_links = '<p class="meta">Supporting artifacts: ' + ' · '.join('<a href="'+esc(url(u))+'">'+esc(u)+'</a>' for u in item.get('references', [])) + '</p>' if item.get('references') else ''
    content += ['<article class="card source-card" id="', esc(item['id']), '" data-relation="', esc(item['relation']), '" data-topics="', esc(topics), '"><h3><a href="', esc(item['url']), '">', esc(item['title']), '</a></h3><p class="meta">', esc(item['kind']), ' · Date/version ', esc(item['published']), ' · ', esc(item['relation']), ' · Topics: ', esc(', '.join(item['topics'])), '</p><h4>Setup</h4><p>', esc(item['setup']), '</p><h4>External evidence</h4>', list_html(item['evidence']), '<h4>Comparison with our results</h4><p>', esc(item['our_comparison']), '</p><h4>Local evidence</h4>', list_html(item['local_evidence']), '<h4>Limits</h4>', list_html(item['limitations']), '</article>']
content += ['</div></section><section id="gaps"><h2>Evidence gaps</h2>', list_html(data['gaps']), '<p><a href="external-comparisons.json" download>Download comparison data</a></p></section></main><footer>Geospatial regridding benchmarks · External evidence and local measurements</footer><script>\n', '''(() => {const relation=document.getElementById('relation-filter'),topic=document.getElementById('topic-filter'),cards=[...document.querySelectorAll('.source-card')],count=document.getElementById('source-count');function render(){let shown=0;for(const card of cards){const match=(!relation.value||card.dataset.relation===relation.value)&&(!topic.value||JSON.parse(card.dataset.topics).includes(topic.value));card.hidden=!match;if(match)shown++;}count.textContent=`${shown} of ${cards.length} sources`; }relation.addEventListener('change',render);topic.addEventListener('change',render);render();})();''', '\n</script></body></html>']
DOCS.mkdir(exist_ok=True)
(DOCS / 'comparison.html').write_text(''.join(content), encoding='utf-8')
shutil.copy2(source, DOCS / 'external-comparisons.json')

lines = ['# How these results compare', '', md(data['introduction']), '', f"Sources accessed {md(data['accessed'])}. Workloads, hardware, methods and timing boundaries vary; these sources do not establish a universal ranking.", '', '[Large & chunked](docs/index.html) · [Small-grid survey](docs/small-data.html) · [Tool guide](docs/tool-guide.html) · [External comparison](docs/comparison.html)', '', '## What the external evidence adds', '']
for item in data['synthesis']:
    lines += ['### ' + md(item['title']), '', md(item['finding']), '', '**Implication:** ' + md(item['implication']), '']
lines += ['## Sources and comparisons', '']
for item in sources:
    lines += ['### [' + md(item['title']) + '](' + item['url'].replace(')', '%29') + ')', '', f"{md(item['kind'])} · Date/version {md(item['published'])} · {md(item['relation'])} · Topics: {md(', '.join(item['topics']))}", '', '**Setup:** ' + md(item['setup']), '', '**External evidence:**', '']
    lines += ['- ' + md(x) for x in item['evidence']]
    lines += ['', '**Comparison with our results:** ' + md(item['our_comparison']), '', '**Local evidence:**', ''] + ['- ' + md(x) for x in item['local_evidence']]
    lines += ['', '**Limits:**', ''] + ['- ' + md(x) for x in item['limitations']] + ['']
lines += ['## Evidence gaps', ''] + ['- ' + md(x) for x in data['gaps']] + ['', '[Download comparison data](docs/external-comparisons.json)', '']
(ROOT / 'EXTERNAL_COMPARISON.md').write_text('\n'.join(lines), encoding='utf-8')
print('Generated external comparison:', DOCS / 'comparison.html')
