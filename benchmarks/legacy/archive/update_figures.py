from pathlib import Path
import re,json
P=Path(__file__).parent
site=P/'geospatial-benchmark-report.html'
s=site.read_text()
# Replace the static overview section, preserving findings, evidence, methods and source archive.
s,n=re.subn(r'<section><h2>The baseline at a glance</h2>.*?</section>',(P/'interactive-figures.html').read_text(),s,count=1,flags=re.S)
assert n==1
s=s.replace('</style>',(P/'interactive-figures.css').read_text()+'\n</style>',1)
s=s.replace('<a href="#explorer">Explore evidence</a>','<a href="#interactive-figures">Interactive figures</a><a href="#timings">Timings</a><a href="#explorer">Explore evidence</a>')
commands=(P/'results/cli_commands.json').read_text().replace('</','<\\/')
s=s.replace('</body>', '<script id="native-timings" type="application/json">'+commands+'</script>\n<script>\n'+(P/'interactive-figures.js').read_text()+'\n</script>\n</body>')
site.write_text(s)
(P/'geospatial-benchmark-report.html').write_text(s)
print('Updated report with scenario-linked heatmaps, exact values, evidence selection and timing tables.')
