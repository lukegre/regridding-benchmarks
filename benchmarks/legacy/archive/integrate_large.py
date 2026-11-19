"""Insert the large timing tier into the self-contained report; original records remain historical."""
from pathlib import Path
import json,re,shutil
ROOT=Path(__file__).parent;file=ROOT/'geospatial-benchmark-report.html';s=file.read_text()
payload=json.loads((ROOT/'large_results/combined.json').read_text())
assert payload['summary']
section=(ROOT/'large-figures.html').read_text()
section=section.replace('<h2>Setup and interpolation at realistic sizes</h2>', '<h2>Setup and interpolation at realistic sizes</h2><p class="note">'+str(len(payload['records']))+' measured repetitions across '+str(len(payload['summary']))+' successful profiles. Canonical geometry/value hashes verified.</p>')
m=re.search(r'<main>(.*?)<section id="recommendations"',s,re.S)
assert m,'Missing original report structure'
s=s[:m.start()]+'<main>'+section+'<details><summary>Original small-grid survey counts</summary>'+m[1]+'</details><section id="recommendations"'+s[m.end():]
s=s.replace('</style>',(ROOT/'large-figures.css').read_text()+'\n</style>',1)
s=s.replace('<a href="#recommendations">Tool choices</a>','<a href="#large-timings">Larger benchmarks</a><a href="#recommendations">Tool choices</a>',1)
s=s.replace('Synthetic interoperability stress tests across','Large shared-grid timings and original interoperability stress tests across',1)
s=s.replace('aria-label="Test counts"','aria-label="Original small-grid test counts"',1)
s=s.replace('<a href="#timings">Timings</a>','<a href="#timings">Original timings</a>')
s=s.replace('<h1>Where geospatial tools work.<br>And where they break.</h1>','<h1>Geospatial regridding benchmarks</h1>')
s=s.replace('<h2>Recorded timings</h2>','<h2>Original small-grid diagnostic timings</h2>')
s=s.replace('<h2>Explore the figures</h2>','<h2>Original small-grid correctness figures</h2>')
s=s.replace('</body>','<script id="large-data" type="application/json">'+json.dumps(payload).replace('</','<\\/')+'</script><script>\n'+(ROOT/'large-figures.js').read_text()+'\n</script></body>')
file.write_text(s)
