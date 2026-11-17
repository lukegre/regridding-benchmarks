import os,json,time,subprocess,traceback
from pathlib import Path
import numpy as np,xarray as xr
from scipy.sparse import coo_matrix
from suite import ROOT,field
P=ROOT/'results/cli';P.mkdir(exist_ok=True)
env=os.environ.copy();env['PATH']=str(ROOT/'compiled/bin')+':'+env['PATH'];env['OMP_NUM_THREADS']='1'
rows=[]
def cmd(args):
 t=time.perf_counter();p=subprocess.run(args,env=env,cwd=P,text=True,capture_output=True,timeout=90)
 (P/(args[0].replace('/','_')+f'_{len(rows)}.log')).write_text(p.stdout+'\n'+p.stderr)
 rows.append(dict(command=args,returncode=p.returncode,seconds=time.perf_counter()-t,stderr=p.stderr[-2000:]))
 (ROOT/'results/cli_commands.json').write_text(json.dumps(rows,indent=2))
 if p.returncode:raise RuntimeError(str(args)+p.stderr[-1000:])
 return p
cmd(['GenerateICOMesh','--res','4','--file','ico.g'])
cmd(['GenerateRLLMesh','--lon','36','--lat','18','--file','rll.g'])
cmd(['GenerateOverlapMesh','--a','ico.g','--b','rll.g','--out','overlap.g'])
cmd(['GenerateOfflineMap','--in_mesh','ico.g','--out_mesh','rll.g','--ov_mesh','overlap.g','--in_type','fv','--out_type','fv','--out_map','weights.nc','--mono'])
w=xr.open_dataset(P/'weights.nc');w.load();print(w,flush=True)
S=coo_matrix((w.S.values,(w.row.values.astype(int)-1,w.col.values.astype(int)-1)),shape=(w.sizes['n_b'],w.sizes['n_a'])).tocsr()
# Tempest map stores centres in degrees; area_a/b are spherical cell areas.
v=field(w.xc_a.values,w.yc_a.values);truth=field(w.xc_b.values,w.yc_b.values)
metrics=[]
for name,data in [('smooth',v),('constant',np.full(v.shape,7.)),('categorical',(v>2).astype(float)),('nan_hole',np.where(np.arange(v.size)%19==0,np.nan,v))]:
 ans=S@data
 ok=np.isfinite(ans)
 metrics.append({'package':'TempestRemap','case':name,'status':'completed','rmse':float(np.sqrt(np.mean((ans[ok]-(np.full(truth.shape,7.) if name=='constant' else truth)[ok])**2))) if name in ('smooth','constant') else None,'finite_fraction':float(ok.mean()),'constant_max_error':float(np.max(abs(ans-7))) if name=='constant' else None,'relative_integral_error':float(abs(np.sum(ans*w.area_b.values)-np.sum(data*w.area_a.values))/abs(np.sum(data*w.area_a.values))) if np.isfinite(data).all() else None})
 ds=xr.Dataset({'z':('ncol',data)})
 ds.to_netcdf(P/f'{name}.nc')
 cmd(['ApplyOfflineMap','--map','weights.nc','--in_data',f'{name}.nc','--out_data',f'{name}_tempest.nc','--var','z','--out_double'])
 out=xr.open_dataset(P/f'{name}_tempest.nc').z.values.ravel()
 metrics[-1]['cli_vs_sparse_max_error']=float(np.nanmax(abs(out-ans)))
 # NCO applies the same externally generated weights: this tests integration, not an independent numerical algorithm.
 try:
  cmd(['ncremap','-m','weights.nc','-i',f'{name}.nc','-o',f'{name}_nco.nc'])
  n=xr.open_dataset(P/f'{name}_nco.nc').z.values.ravel();metrics.append({'package':'NCO ncremap','case':name,'status':'completed','finite_fraction':float(np.isfinite(n).mean()),'vs_tempest_max_error':float(np.nanmax(abs(n-out)))})
 except Exception as e:metrics.append({'package':'NCO ncremap','case':name,'status':'error','error':str(e)})
 (ROOT/'results/cli_metrics.json').write_text(json.dumps(metrics,indent=2))
