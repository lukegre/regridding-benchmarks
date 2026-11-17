"""Combine raw per-profile measurements without altering them."""
import json,platform
from pathlib import Path
p=Path(__file__).parent/'chunked_results'
profiles=[json.loads(x.read_text()) for x in sorted(p.glob('*.json')) if x.name not in ('combined.json','storage_netcdf4.json','diagnostic_default.json')]
storage_path=p/'storage_netcdf4.json'
data={'configuration':{'grid_size':[512,512],'time_steps':4,'repeats':3,'layouts':[[1,128,128],[1,256,256],[4,512,512]],'scheduler':'synchronous','thread_limits':1,'platform':platform.platform(),'input':'in-memory NumPy arrays wrapped as Dask chunks','missing_values':'64 pixels per time slice at [124:132,124:132]','xesmf_output_chunks':[512,512],'method':'bilinear / linear','timing':'graph construction and complete synchronous compute timed separately; setup shared by layouts'},'summary':[s for p in profiles for s in p['summary']],'records':[r for p in profiles for r in p['records']],'failures':[f for p in profiles for f in p['failures']],'storage':json.loads(storage_path.read_text()) if storage_path.exists() else None,'diagnostic_default':json.loads((p/'diagnostic_default.json').read_text()) if (p/'diagnostic_default.json').exists() else None}
(p/'combined.json').write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
print(len(data['summary']),len(data['records']),len(data['failures']))
