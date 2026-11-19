import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MPLCONFIGDIR='/tmp/geobench-mpl')
import sys,json,warnings,time,traceback
import numpy as np,xarray as xr
from suite import ROOT,sample,field
rows=[]
def probe(p,c,f):
 t=time.perf_counter();r=dict(package=p,case=c)
 try:
  with warnings.catch_warnings(record=True) as ws:
   warnings.simplefilter('always');r.update(f())
  r.update(status='completed',warnings=[str(w.message) for w in ws][:8])
 except Exception as e:r.update(status='error',error=str(e),traceback=traceback.format_exc())
 r['seconds']=time.perf_counter()-t;rows.append(r);print(p,c,r['status'],flush=True)
 (ROOT/'results'/f'controls_{sys.argv[1]}.json').write_text(json.dumps(rows,indent=2))
def astropy(wrap):
 from astropy_healpix import HEALPix
 import astropy.units as u
 lo,la,v,m,x,y,truth=sample('healpix','smooth')
 a=HEALPix(nside=8,order='ring').interpolate_bilinear_lonlat((x%360 if wrap else x)*u.deg,y*u.deg,v)
 ok=np.isfinite(a)
 return {'finite_fraction':float(ok.mean()),'rmse':float(np.sqrt(np.mean((a[ok]-truth[ok])**2))),'max_abs_value':float(np.max(abs(a[ok])))}
def resample(grid,wrap):
 from pyresample import geometry,kd_tree
 lo,la,v,m,x,y,truth=sample(grid,'smooth')
 if wrap:lo=(lo+180)%360-180;x=(x+180)%360-180
 a=kd_tree.resample_nearest(geometry.SwathDefinition(lons=lo,lats=la),v,geometry.SwathDefinition(lons=x,lats=y),radius_of_influence=900000,fill_value=np.nan)
 ok=np.isfinite(a)
 return {'finite_fraction':float(ok.mean()),'rmse':float(np.sqrt(np.mean((a[ok]-truth[ok])**2)))}
def scipy(wrap):
 from scipy.interpolate import RegularGridInterpolator
 lo,la,v,m,x,y,truth=sample('gaussian','smooth')
 if wrap:x=x%360
 a=RegularGridInterpolator((la[:,0],lo[0]),v,bounds_error=False,fill_value=np.nan)(np.stack([y,x],-1));ok=np.isfinite(a)
 return {'finite_fraction':float(ok.mean()),'rmse':float(np.sqrt(np.mean((a[ok]-truth[ok])**2)))}
def stale():
 import xesmf as xe
 lo,la,v,m,x,y,truth=sample('rectilinear','smooth')
 s=xr.Dataset({'lon':(('y','x'),lo),'lat':(('y','x'),la)});d=xr.Dataset({'lon':(('y','x'),x),'lat':(('y','x'),y)})
 weights=ROOT/'results/stale_weights.nc'
 first=xe.Regridder(s,d,'bilinear');first.to_netcdf(weights)
 shifted=s.copy(deep=True);shifted.lon.values[:]+=3
 new_values=xr.DataArray(field(shifted.lon,shifted.lat),dims=('y','x'))
 old=xe.Regridder(shifted,d,'bilinear',filename=weights,reuse_weights=True)
 new=xe.Regridder(shifted,d,'bilinear')
 a=old(new_values).values;b=new(new_values).values
 return {'stale_rmse':float(np.sqrt(np.mean((a-truth)**2))),'rebuilt_rmse':float(np.sqrt(np.mean((b-truth)**2))),'accepted_reuse_with_changed_coordinates':True}
def hpforce():
 import subprocess
 p=ROOT/'results/cdo_conservative_healpix_smooth';out=p/'forced.nc'
 t=subprocess.run([str(ROOT/'compiled/bin/cdo'),'--force','-O',f'remapcon,{p}/target.txt',f'-setgrid,{p}/source.txt',str(p/'input.nc'),str(out)],capture_output=True,text=True,timeout=30)
 (p/'forced.log').write_text(t.stderr)
 if t.returncode:raise RuntimeError(t.stderr)
 a=xr.open_dataset(out).z.values.squeeze();truth=sample('healpix','smooth')[-1];ok=np.isfinite(a)
 return {'rmse':float(np.sqrt(np.mean((a[ok]-truth[ok])**2))),'finite_fraction':float(ok.mean()),'stderr':t.stderr[-1200:]}
if sys.argv[1]=='python':
 for wrap in [False,True]:
  probe('astropy-healpix',f'longitude_wrapped_{wrap}',lambda w=wrap:astropy(w))
  probe('SciPy',f'longitude_wrapped_{wrap}',lambda w=wrap:scipy(w))
  for g in ['healpix','gaussian']:probe('Pyresample',f'{g}_longitude_wrapped_{wrap}',lambda w=wrap,g=g:resample(g,w))
else:
 probe('xESMF','stale_weight_file',stale)
 probe('CDO','forced_healpix_conservative',hpforce)
