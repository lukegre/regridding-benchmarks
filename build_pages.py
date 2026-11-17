"""Build the self-contained GitHub Pages report from recorded results."""
from pathlib import Path
import subprocess,sys,shutil,tarfile
root=Path(__file__).parent
for script in ['report.py','plot.py','build_artifact.py','update_figures.py']:
 subprocess.run([sys.executable,str(root/script)],cwd=root,check=True)
docs=root/'docs';docs.mkdir(exist_ok=True)
html=(root/'geospatial-benchmark-report.html').read_text()
html=html.replace('<div class="provenance">','<p><a href="benchmark-source-and-results.tar.gz" download>Download code, inputs, results and logs</a> · <a href="results.csv" download>Results CSV</a> · <a href="results.json" download>Results JSON</a></p><div class="provenance">')
(docs/'index.html').write_text(html)
shutil.copy2(root/'all_results.csv',docs/'results.csv');shutil.copy2(root/'all_results.json',docs/'results.json')
(docs/'.nojekyll').touch()
excluded={'.git','.venv','compiled','mamba-root','bin','__pycache__','docs','.openai'}
with tarfile.open(docs/'benchmark-source-and-results.tar.gz','w:gz') as archive:
 for path in sorted(root.iterdir()):
  if path.name not in excluded and path.name!='geospatial-benchmark-report.html':
   archive.add(path,arcname=path.name,filter=lambda i:None if '__pycache__' in i.name.split('/') else i)
print('Pages output:',docs)
