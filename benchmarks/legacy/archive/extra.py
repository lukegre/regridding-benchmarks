import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',NUMBA_NUM_THREADS='1',NUMBA_CACHE_DIR='/tmp/geobench-numba',MPLCONFIGDIR='/tmp/geobench-mpl')
import sys,json,time,traceback,warnings
import numpy as np,xarray as xr
from suite import ROOT,field,geometry,target
rows=[]
def probe(pkg,case,f):
 t=time.perf_counter();r=dict(package=pkg,case=case)
 try:
  with warnings.catch_warnings(record=True) as ws:
   warnings.simplefilter('always');r.update(f() or {})
  r.update(status='completed',warnings=[str(w.message) for w in ws][:8])
 except Exception as e:r.update(status='error',error=f'{type(e).__name__}: {e}',traceback=traceback.format_exc())
 r['seconds']=time.perf_counter()-t;rows.append(r);print(pkg,case,r['status'],r.get('error',''),flush=True)
 (ROOT/'results'/f'extra_{sys.argv[1]}.json').write_text(json.dumps(rows,indent=2))

def satellite(case):
 from rasterio.crs import CRS
 from rasterio.warp import reproject,Resampling
 from rasterio.transform import from_bounds
 lo,la=geometry('satellite_swath');tx,ty=target('satellite_swath');v=field(lo,la)
 if case=='constant':v[:]=7
 if case=='nan_hole':v[::8,::4]=np.nan
 if case=='unwrapped':lo=lo%360
 if case=='categorical':v=(lo>0).astype(float)
 ans=np.full(tx.shape,np.nan)
 reproject(v,ans,src_geoloc_array=(lo,la),src_crs=CRS.from_epsg(4326),dst_crs=CRS.from_epsg(4326),dst_transform=from_bounds(169.5,-46.5,190.5,46.5,21,31),src_nodata=np.nan,dst_nodata=np.nan,resampling=Resampling.bilinear)
 ans=ans[::-1];truth=field(tx,ty);ok=np.isfinite(ans)
 return dict(finite_fraction=float(ok.mean()),rmse=float(np.sqrt(np.mean((ans[ok]-(7 if case=='constant' else truth[ok]))**2))),fractional_categories=bool(np.any(ok & (abs(ans-np.round(ans))>1e-8))) if case=='categorical' else None)

def proj(case):
 from pyproj import Transformer
 xy=case!='wrong_axis_order';t=Transformer.from_crs(4326,2056,always_xy=xy)
 lo=np.array([6.,8.,10.]);la=np.array([46.,47.,48.])
 if case=='invalid_lat':la[1]=95
 east,north=t.transform(lo,la,errcheck=case=='invalid_lat')
 if case=='wrong_axis_order':
  good=Transformer.from_crs(4326,2056,always_xy=True).transform(lo,la)
  return {'max_position_error_metres':float(np.max(np.hypot(east-good[0],north-good[1])))}
 a,b=Transformer.from_crs(2056,4326,always_xy=True).transform(east,north)
 return {'roundtrip_max_degrees':float(np.max(abs(a-lo)+abs(b-la)))}

def iris_remap(case):
 import iris
 from iris.coords import DimCoord,AuxCoord
 from iris.cube import Cube
 from esmf_regrid.schemes import ESMFAreaWeighted,ESMFBilinear
 lat=DimCoord(np.arange(-20.,21.,2),standard_name='latitude',units='degrees');lon=DimCoord(np.arange(-30.,31.,2),standard_name='longitude',units='degrees')
 lat.guess_bounds();lon.guess_bounds()
 lo,la=np.meshgrid(lon.points,lat.points)
 data=field(lo,la)
 if case=='constant':data[:]=7
 src=Cube(data,dim_coords_and_dims=[(lat,0),(lon,1)])
 tlat=DimCoord(np.arange(-15.,16.,3),standard_name='latitude',units='degrees');tlon=DimCoord(np.arange(-24.,25.,3),standard_name='longitude',units='degrees');tlat.guess_bounds();tlon.guess_bounds()
 dst=Cube(np.zeros((len(tlat.points),len(tlon.points))),dim_coords_and_dims=[(tlat,0),(tlon,1)])
 if case=='missing_bounds':src.coord('longitude').bounds=None
 if case=='mask':src.data=np.ma.masked_where(np.indices(data.shape)[1]%19==0,data)
 a=src.regrid(dst,ESMFBilinear() if case=='bilinear' else ESMFAreaWeighted())
 x,y=np.meshgrid(tlon.points,tlat.points);ans=np.ma.filled(a.data,np.nan);truth=np.full(x.shape,7.) if case=='constant' else field(x,y);ok=np.isfinite(ans)
 return {'rmse':float(np.sqrt(np.mean((ans[ok]-truth[ok])**2))),'finite_fraction':float(ok.mean())}

def xugrid_sphere(case):
 from native import ico
 import xugrid as xu
 m,lo,la,clo,cla=ico(2);n,x,y,cx,cy=ico(1)
 s=xu.Ugrid2d(lo,la,-1,m.faces,is_projected=False);d=xu.Ugrid2d(x,y,-1,n.faces,is_projected=False)
 src=xu.UgridDataArray(xr.DataArray(field(clo,cla),dims=s.face_dimension),s)
 dst=xu.UgridDataArray(xr.DataArray(np.zeros(len(n.faces)),dims=d.face_dimension),d)
 r=xu.OverlapRegridder(src,dst,method='mean') if case=='overlap' else xu.BarycentricInterpolator(src,dst)
 a=r.regrid(src).values;truth=field(cx,cy);ok=np.isfinite(a)
 return {'rmse':float(np.sqrt(np.mean((a[ok]-truth[ok])**2))),'finite_fraction':float(ok.mean()),'qualification':'Coordinates are lon/lat degrees; Xugrid algorithms use planar geometry.'}

if sys.argv[1]=='python':
 for c in ['smooth','unwrapped','constant','nan_hole','categorical']:probe('GDAL geolocation via Rasterio',c,lambda c=c:satellite(c))
 for c in ['roundtrip','wrong_axis_order','invalid_lat']:probe('pyproj',c,lambda c=c:proj(c))
 for c in ['barycentric','overlap']:probe('Xugrid global sphere',c,lambda c=c:xugrid_sphere(c))
else:
 for c in ['smooth','constant','mask','missing_bounds','bilinear']:probe('iris-esmf-regrid',c,lambda c=c:iris_remap(c))
