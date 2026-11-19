from pathlib import Path
import json,base64,html,re,collections
P=Path(__file__).parent
rows=json.loads((P/'all_results.json').read_text())
def inline(s):
 s=html.escape(s)
 s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
 s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
 return s

def markdown(s):
 out=[];lines=s.splitlines();i=0
 while i<len(lines):
  line=lines[i]
  if not line.strip():i+=1;continue
  if line.startswith('!['):i+=1;continue
  h=re.match(r'^(#{1,3}) (.*)',line)
  if h:
   n=len(h[1]);out.append(f'<h{n}>{inline(h[2])}</h{n}>');i+=1;continue
  if line.startswith('|'):
   table=[]
   while i<len(lines) and lines[i].startswith('|'):
    cells=[x.strip() for x in lines[i].strip('|').split('|')]
    if not all(re.fullmatch(r'[-: ]+',x) for x in cells):table.append(cells)
    i+=1
   out.append('<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+inline(x)+'</th>' for x in table[0])+'</tr></thead><tbody>')
   for r in table[1:]:out.append('<tr>'+''.join('<td>'+inline(x)+'</td>' for x in r)+'</tr>')
   out.append('</tbody></table></div>');continue
  if re.match(r'^(- |\d+\. )',line):
   ordered=bool(re.match(r'^\d+\.',line));tag='ol' if ordered else 'ul';out.append('<'+tag+'>')
   while i<len(lines) and re.match(r'^(- |\d+\. )',lines[i]):
    out.append('<li>'+inline(re.sub(r'^(- |\d+\. )','',lines[i]))+'</li>');i+=1
   out.append('</'+tag+'>');continue
  parts=[]
  while i<len(lines) and lines[i].strip() and not re.match(r'^(#|\||- |\d+\. |!\[)',lines[i]):parts.append(lines[i]);i+=1
  out.append('<p>'+inline(' '.join(parts))+'</p>')
 return '\n'.join(out)
report=(P/'REPORT.md').read_text()
summary=report.split('## What I would use')[1].split('## Most consequential findings')[0]
findings=report.split('## Most consequential findings')[1].split('## Setup and interface friction')[0]
detail='## Setup and interface friction'+report.split('## Setup and interface friction')[1]
# Full baseline table is already accessible in the interactive explorer.
detail=detail.split('## Smooth-field results')[0]+ '## Versions and artifacts'+detail.split('## Versions and artifacts')[1]
image=base64.b64encode((P/'overview.png').read_bytes()).decode()
template=r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Geospatial interoperability — synthetic benchmark report</title>
<style>
:root{color-scheme:light;--ink:#172b35;--muted:#526570;--paper:#f5f7f7;--line:#d9e2e5;--accent:#075e65;--warm:#a65328}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,-apple-system,sans-serif}a{color:var(--accent)}header,main,footer{max-width:1180px;margin:auto;padding:36px 28px}header{padding-top:64px;padding-bottom:24px}.eyebrow{letter-spacing:.14em;font-size:12px;font-weight:700;color:var(--accent);text-transform:uppercase}h1{font-size:clamp(32px,5vw,56px);line-height:1.1;letter-spacing:-.045em;max-width:820px;margin:18px 0}h2{font-size:27px;letter-spacing:-.025em;margin:0 0 20px}h3{font-size:21px;margin:32px 0 12px}p{max-width:900px}.intro{font-size:19px;color:var(--muted);max-width:850px}nav{display:flex;gap:24px;flex-wrap:wrap;margin-top:30px}nav a{text-decoration:none;border-bottom:2px solid var(--accent);padding:6px 0;font-weight:600}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;padding:24px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.stats strong{display:block;font-size:36px;line-height:1.2;font-variant-numeric:tabular-nums}.stats span{font-size:14px;color:var(--muted)}section{padding:42px 0;border-bottom:1px solid var(--line);scroll-margin-top:24px}.note{color:var(--muted);font-size:14px}.recommendations ul{columns:2;column-gap:42px;padding-left:20px}.recommendations li{break-inside:avoid;margin:0 0 18px}li{padding-left:5px;margin-bottom:14px}ol{padding-left:25px}code{background:#e9eef0;border-radius:3px;padding:2px 5px;font-size:.88em;overflow-wrap:anywhere}img{width:100%;height:auto}.filters{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:24px 0}label{display:flex;flex-direction:column;gap:6px;font-size:14px;font-weight:600}select,input,button{font:inherit;border:1px solid #9badb6;border-radius:5px;padding:10px 12px;background:white;color:var(--ink)}button{cursor:pointer}button:disabled{opacity:.4;cursor:default}button:hover:not(:disabled){background:#e6eeee}input{width:100%}label.search{grid-column:1/-1}button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible{outline:3px solid #367caa;outline-offset:3px}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px}th{text-align:left;background:#e8edef;font-weight:600;white-space:nowrap}th,td{padding:12px;border-bottom:1px solid var(--line);vertical-align:top}td{overflow-wrap:anywhere}td.num{font-variant-numeric:tabular-nums;white-space:nowrap;text-align:right}details>summary{cursor:pointer;font-weight:500}details pre{white-space:pre-wrap;overflow-wrap:anywhere;max-width:720px;font-size:12px}.status{font-size:12px;border-radius:4px;padding:3px 7px;white-space:nowrap}.completed{background:#dceee6;color:#24533c}.error{background:#fae9df;color:#853c19}.not_exercised{background:#e8edef;color:#526570}.toolbar{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;margin:20px 0}.toolbar p{margin:0}.actions{display:flex;gap:10px;flex-wrap:wrap}.methodology{max-width:980px}.provenance{padding:18px 0;color:var(--muted);font-size:14px}footer{color:var(--muted);font-size:14px}.print{margin-left:auto}.empty{padding:28px;text-align:center}@media(max-width:700px){header,main,footer{padding-left:18px;padding-right:18px}.stats{grid-template-columns:repeat(2,1fr)}.recommendations ul{columns:1}.filters{grid-template-columns:1fr}th,td{padding:10px}.print{margin-left:0}}@media print{nav,.filters,.actions,.toolbar button,.print{display:none!important}header,main,footer{max-width:none;padding:10px}section{break-inside:auto}body{background:white;font-size:11px}h1{font-size:32px}.stats strong{font-size:24px}#explorer{display:none}details{display:block}}
</style></head><body>
<header><div class="eyebrow">Research engineering / 17 November 2026</div><h1>Where geospatial tools work.<br>And where they break.</h1><p class="intro">Synthetic interoperability stress tests across satellite swaths, rectilinear grids, ROMS-style curvilinear grids, icosahedral meshes, HEALPix and Gaussian grids.</p><nav aria-label="Report sections"><a href="#recommendations">Tool choices</a><a href="#findings">Findings</a><a href="#explorer">Explore evidence</a><a href="#methods">Methods & versions</a><button class="print" onclick="window.print()">Print / save PDF</button></nav></header>
<main><div class="stats" aria-label="Test counts"><div><strong>@@ATTEMPTED@@</strong><span>Operations attempted</span></div><div><strong>@@COMPLETED@@</strong><span>Returned an output</span></div><div><strong>@@ERRORS@@</strong><span>Raised an error</span></div><div><strong>@@NOT_EXERCISED@@</strong><span>Outside tested adapter scope</span></div></div><p class="note">An output is not a correctness verdict. Errors include deliberately malformed inputs. Adapter scope does not establish a package’s full capability.</p>
<section id="recommendations" class="recommendations"><h2>Choose by grid and operation</h2>@@SUMMARY@@</section>
<section id="findings"><h2>What the tests exposed</h2>@@FINDINGS@@</section>
<section><h2>The baseline at a glance</h2><p class="note">Raw smooth-field workflows. Kernels, targets and longitude conventions differ; this chart is not a ranking. Topology-aware native tests are documented above and available in the evidence explorer.</p><img src="data:image/png;base64,@@IMAGE@@" alt="Two heatmaps show finite coverage and analytic-field RMSE for the tested adapters across six grids. Some raw longitude conventions reduce coverage; missing adapter combinations are marked with dashes."></section>
<section id="explorer"><h2>Explore the evidence</h2><p>Inspect every recorded probe, including warnings and original error messages. RMSE is measured in synthetic field units; finite coverage is the proportion of output samples with finite values.</p>
<div class="filters"><label>Package or adapter<select id="pkg"><option value="">All packages</option></select></label><label>Grid family<select id="grid"><option value="">All grids and native probes</option></select></label><label>Result<select id="status"><option value="">All results</option><option value="completed">Returned output</option><option value="error">Raised error</option><option value="not_exercised">Not exercised</option></select></label><label class="search">Search scenario, case or diagnostic<input id="search" type="search" placeholder="e.g. dateline, constant, stale, invalid"></label></div>
<div class="toolbar"><p id="count" role="status" aria-live="polite"></p><div class="actions"><button id="csv">Download filtered CSV</button><button id="json">Download all results JSON</button></div></div>
<div class="table-wrap"><table><thead><tr><th>Package / grid</th><th>Probe</th><th>Result</th><th>RMSE</th><th>Finite</th><th>Diagnostics</th></tr></thead><tbody id="results"></tbody></table></div>
<div class="toolbar"><span id="page-label"></span><div class="actions"><button id="prev">Previous</button><button id="next">Next</button></div></div></section>
<section id="methods" class="methodology"><h2>Methods, limits and reproducibility</h2>@@DETAIL@@</section>
<div class="provenance">Based on actual local runs recorded on 17 November 2026. Source survey: <a href="https://sdsc.atlassian.net/wiki/spaces/Verticals/pages/4712333313">Geospatial data interoperability: regridding and reprojection tools</a>. Source code, inputs and logs accompany the report in the benchmark archive. This self-contained report embeds the recorded results; it does not rerun benchmarks.</div>
</main><footer>Geospatial interoperability benchmark report · Synthetic fixtures · No memory stress testing · Diagnostic timings, not a controlled speed benchmark</footer>
<script id="data" type="application/json">@@DATA@@</script><script>
'use strict';
const data=JSON.parse(document.getElementById('data').textContent);
const els=Object.fromEntries(['pkg','grid','status','search','results','count','page-label','prev','next','csv','json'].map(id=>[id,document.getElementById(id)]));
for(const [key,id] of [['package','pkg'],['grid','grid']]){[...new Set(data.map(x=>x[key]).filter(Boolean))].sort().forEach(v=>els[id].add(new Option(v,v)));}
let page=0,filtered=data;const pageSize=25;
function num(x){return typeof x==='number'&&Number.isFinite(x)?(Math.abs(x)!==0&&(Math.abs(x)<.001||Math.abs(x)>1e5)?x.toExponential(3):x.toPrecision(4)):'—';}
function cell(tr,text,cls){const td=document.createElement('td');td.textContent=text;if(cls)td.className=cls;tr.append(td);return td;}
function render(reset=false){if(reset)page=0;const q=els.search.value.toLowerCase();filtered=data.filter(x=>(!els.pkg.value||x.package===els.pkg.value)&&(!els.grid.value||x.grid===els.grid.value)&&(!els.status.value||x.status===els.status.value)&&(!q||JSON.stringify(x).toLowerCase().includes(q)));page=Math.max(0,Math.min(page,Math.ceil(filtered.length/pageSize)-1));els.results.replaceChildren();
for(const x of filtered.slice(page*pageSize,(page+1)*pageSize)){const tr=document.createElement('tr');cell(tr,x.package+' / '+(x.grid||'native / targeted'));cell(tr,x.scenario||x.case||'—');const s=cell(tr,'');const tag=document.createElement('span');tag.className='status '+x.status;tag.textContent={completed:'Output returned',error:'Error',not_exercised:'Not exercised'}[x.status]||x.status;s.append(tag);cell(tr,num(x.rmse),'num');cell(tr,typeof x.finite_fraction==='number'?(x.finite_fraction*100).toFixed(1)+'%':'—','num');const d=cell(tr,'');const details=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');summary.textContent=x.error?x.error.slice(0,95):x.flags?.length?x.flags.join(', '):x.warnings?.length?'Warnings & metrics':'Metrics & provenance';pre.textContent=JSON.stringify(x,null,2);details.append(summary,pre);d.append(details);els.results.append(tr);}
if(!filtered.length){const tr=document.createElement('tr');const td=cell(tr,'No probes match these filters.','empty');td.colSpan=6;els.results.append(tr);}els.count.textContent=filtered.length+' of '+data.length+' recorded probes';els['page-label'].textContent='Page '+(page+1)+' of '+Math.max(1,Math.ceil(filtered.length/pageSize));els.prev.disabled=page===0;els.next.disabled=(page+1)*pageSize>=filtered.length;}
for(const id of ['pkg','grid','status'])els[id].addEventListener('change',()=>render(true));els.search.addEventListener('input',()=>render(true));els.prev.onclick=()=>{page--;render();};els.next.onclick=()=>{page++;render();};
function download(name,text,type){const url=URL.createObjectURL(new Blob([text],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
els.json.onclick=()=>download('geospatial-benchmark-results.json',JSON.stringify(data,null,2),'application/json');
els.csv.onclick=()=>{const keys=['package','grid','scenario','case','status','rmse','finite_fraction','max_error','relative_integral_error','seconds','error','source_file'];const quote=v=>'"'+String(v??'').replaceAll('"','""')+'"';download('geospatial-benchmark-filtered.csv',[keys.map(quote).join(','),...filtered.map(r=>keys.map(k=>quote(r[k])).join(','))].join('\r\n'),'text/csv');};render();
</script></body></html>'''
counts=collections.Counter(r['status'] for r in rows)
for key,value in {'ATTEMPTED':str(counts['completed']+counts['error']),'COMPLETED':str(counts['completed']),'ERRORS':str(counts['error']),'NOT_EXERCISED':str(counts['not_exercised']),'SUMMARY':markdown(summary),'FINDINGS':markdown(findings),'IMAGE':image,'DETAIL':markdown(detail),'DATA':json.dumps(rows).replace('</','<\\/')}.items():template=template.replace('@@'+key+'@@',value)
(P/'geospatial-benchmark-report.html').write_text(template)
print(P/'geospatial-benchmark-report.html')
