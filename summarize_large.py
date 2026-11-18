"""Aggregate only shared production-size observations; verify geometry equality."""
import json,csv,statistics,collections
from pathlib import Path
ROOT=Path(__file__).parent;out=ROOT/'large_results'
records=[];failures=[]
for p in sorted(out.glob('*__*.json')):
 x=json.loads(p.read_text())
 if x.get('scale') not in (512,1024,4096):continue
 if x['status']=='completed':records+=x['runs']
 else:failures.append(x)
# Enforce the user's same-input requirement, rather than merely describing it.
for key,group in __import__('itertools').groupby(sorted(records,key=lambda r:(r['grid'],r['scale'])),lambda r:(r['grid'],r['scale'])):
 group=list(group)
 for field in ['source_geometry_sha256','destination_geometry_sha256','values_sha256']:
  assert len({r[field] for r in group})==1,(key,field)
summary=[]
for key,group in __import__('itertools').groupby(sorted(records,key=lambda r:(r['grid'],r['scale'],r['package'])),lambda r:(r['grid'],r['scale'],r['package'])):
 g=list(group);base={k:g[0][k] for k in ['package','grid','scale','source_cells','target_cells','source_shape','target_shape','source_geometry_sha256','destination_geometry_sha256','values_sha256','timing_mode']}
 for metric in ['setup_seconds','apply_seconds','total_seconds']:
  v=[r[metric] for r in g];base[metric+'_mean']=statistics.mean(v);base[metric+'_median']=statistics.median(v);base[metric+'_min']=min(v);base[metric+'_max']=max(v)
 base['comparison_group']=base['grid']+('__coordinates' if base['package']=='pyproj' else '')
 if 'actual_source_cells' in g[0]:
  base['source_cells']=g[0]['actual_source_cells'];base['source_shape']=g[0]['actual_source_shape'];base['target_cells']=g[0]['actual_target_cells'];base['target_shape']=g[0]['actual_target_shape']
 base.update(repeats=len(g),finite_fraction=min(r['finite_fraction'] for r in g),rmse=max((r['rmse'] for r in g if r.get('rmse') is not None),default=None),setup_note=g[0].get('setup_note',''),native_io_included=g[0]['package'].startswith('cdo_') or g[0]['package'] in ('tempest','nco'))
 if 'roundtrip_max_degrees' in g[0]:base['roundtrip_max_degrees']=max(r['roundtrip_max_degrees'] for r in g)
 summary.append(base)
result={'records':records,'summary':summary,'failures':failures,'configuration':json.loads((out/'configuration.json').read_text())}
(out/'combined.json').write_text(json.dumps(result,indent=2))
if records:
 keys=sorted(set().union(*(r.keys() for r in records)))
 with (out/'measurements.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=keys,lineterminator='\n');w.writeheader();w.writerows(records)
print('Recorded repeats:',len(records),'profiles:',len(summary),'errors:',len(failures),'same-input hashes: verified')
for r in summary:
 if r['total_seconds_mean']>=5:print(r['package'],r['grid'],r['scale'],round(r['setup_seconds_mean'],2),round(r['apply_seconds_mean'],2))
