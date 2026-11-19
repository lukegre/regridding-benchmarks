"""Topology-aware mesh, conservative ROMS, staggering, and reprojection probes."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',NUMBA_NUM_THREADS='1',NUMBA_CACHE_DIR='/tmp/geobench-numba',MPLCONFIGDIR='/tmp/geobench-mpl')
import sys,time,json,traceback,warnings
from pathlib import Path
import numpy as np,xarray as xr
from suite import field,xyz_to_ll,ROOT
rows=[]
def probe(package,case,f):
 t=time.perf_counter();r={'package':package,'case':case}
 try:
  with warnings.catch_warnings(record=True) as ws:
   warnings.simplefilter('always');r.update(f() or {})
  r.update(status='completed',warnings=[str(w.message) for w in ws][:8])
 except Exception as e:r.update(status='error',error=f'{type(e).__name__}: {e}',traceback=traceback.format_exc())
 r['seconds']=time.perf_counter()-t;rows.append(r)
 (ROOT/'results'/f'native_{sys.argv[1]}.json').write_text(json.dumps(rows,indent=2))
 print(package,case,r['status'],r.get('error',''),flush=True)
def metrics(a,b):
 a,b=np.asarray(a),np.asarray(b);ok=np.isfinite(a)
 return dict(rmse=float(np.sqrt(np.mean((a[ok]-b[ok])**2))),finite_fraction=float(ok.mean()),max_error=float(np.max(np.abs(a[ok]-b[ok]))))
def ico(sub=1):
 import trimesh
 m=trimesh.creation.icosphere(subdivisions=sub)
 lo,la=xyz_to_ll(m.vertices);clo,cla=xyz_to_ll(m.vertices[m.faces].mean(axis=1))
 return m,lo,la,clo,cla

def esmf_mesh(method='CONSERVE',constant=False):
 import esmpy as E
 m,lo,la,clo,cla=ico(2)
 mesh=E.Mesh(parametric_dim=2,spatial_dim=2,coord_sys=E.CoordSys.SPH_DEG)
 mesh.add_nodes(len(lo),np.arange(1,len(lo)+1,dtype=np.int32),np.stack([lo,la],-1).ravel(),np.zeros(len(lo),np.int32))
 mesh.add_elements(len(m.faces),np.arange(1,len(m.faces)+1,dtype=np.int32),np.full(len(m.faces),E.MeshElemType.TRI,np.int32),m.faces.astype(np.int32).ravel(),element_coords=np.stack([clo,cla],-1).ravel())
 # Closed triangulated sphere -> a different closed triangulated sphere, avoiding polar raster degeneracy.
 n,x,y,cx,cy=ico(1)
 dst=E.Mesh(parametric_dim=2,spatial_dim=2,coord_sys=E.CoordSys.SPH_DEG)
 dst.add_nodes(len(x),np.arange(1,len(x)+1,dtype=np.int32),np.stack([x,y],-1).ravel(),np.zeros(len(x),np.int32))
 dst.add_elements(len(n.faces),np.arange(1,len(n.faces)+1,dtype=np.int32),np.full(len(n.faces),E.MeshElemType.TRI,np.int32),n.faces.astype(np.int32).ravel(),element_coords=np.stack([cx,cy],-1).ravel())
 srcf=E.Field(mesh,meshloc=E.MeshLoc.ELEMENT);dstf=E.Field(dst,meshloc=E.MeshLoc.ELEMENT)
 srcf.data[:]=7 if constant else field(clo,cla)
 r=E.Regrid(srcf,dstf,regrid_method=getattr(E.RegridMethod,method),unmapped_action=E.UnmappedAction.ERROR)
 r(srcf,dstf);ans=metrics(dstf.data,np.full(len(cx),7) if constant else field(cx,cy))
 if method=='CONSERVE':
  sa=E.Field(mesh,meshloc=E.MeshLoc.ELEMENT);da=E.Field(dst,meshloc=E.MeshLoc.ELEMENT);sa.get_area();da.get_area()
  ans['relative_integral_error']=float(abs(np.sum(srcf.data*sa.data)-np.sum(dstf.data*da.data))/abs(np.sum(srcf.data*sa.data)))
 return ans

def roms_conserve(case):
 import xesmf as xe
 def make(nx,ny):
  x=np.linspace(-30,30,nx+1);y=np.linspace(-20,20,ny+1)
  a,b=np.meshgrid(x,y);lo=a+2*np.sin(np.deg2rad(b*4));la=b+1.5*np.sin(np.deg2rad(a*3))
  c,d=np.meshgrid((x[:-1]+x[1:])/2,(y[:-1]+y[1:])/2)
  return xr.Dataset({'lon':(('y','x'),c+2*np.sin(np.deg2rad(d*4))),'lat':(('y','x'),d+1.5*np.sin(np.deg2rad(c*3))),'lon_b':(('yb','xb'),lo),'lat_b':(('yb','xb'),la)})
 src=make(30,20);dst=make(15,10)
 if case=='missing_corners':src=src.drop_vars(['lon_b','lat_b']);dst=dst.drop_vars(['lon_b','lat_b'])
 if case=='folded_cell':src.lon_b.values[10,15]+=15
 if case=='mask':
  mask=np.ones((20,30),np.int32);mask[8:12,12:18]=0;src['mask']=(('y','x'),mask)
 
 if case=='constant_identity':dst=src.copy(deep=True)
 r=xe.Regridder(src,dst,'conservative_normed' if case=='constant_normed' else 'conservative',unmapped_to_nan=True)
 v=xr.DataArray(field(src.lon,src.lat),dims=('y','x'))
 if case.startswith('constant'):v[:]=7
 a=r(v).values;truth=np.full(a.shape,7) if case.startswith('constant') else field(dst.lon,dst.lat)
 out=metrics(a,truth)
 cov=np.asarray(r.weights.data.sum(axis=1).todense());out.update(weight_row_sum_min=float(cov.min()),weight_row_sum_max=float(cov.max()))
 # Integral conservation measured with the same ESMF spherical area engine and supplied corners.
 if case in ('smooth','constant'):
  import xesmf.util as util
  area_s=util.cell_area(src);area_d=util.cell_area(dst)
  out['relative_integral_error']=float(abs(np.nansum(a*area_d)-np.sum(v.values*area_s))/abs(np.sum(v.values*area_s)))
 if case=='staggered_vector':
  # ROMS u-points have nx-1 samples: cannot apply rho-point weights to them.
  r(xr.DataArray(np.ones((20,29)),dims=('y','x')))
 return out

def ux_mesh(case):
 import uxarray as ux
 m,lo,la,clo,cla=ico(2)
 verts=np.stack([lo[m.faces],la[m.faces]],-1)
 grid=ux.Grid.from_face_vertices(verts,latlon=True)
 v=field(clo,cla)
 if case.startswith('constant'):v[:]=7
 if case=='nan_hole':v[::19]=np.nan
 if case=='wrong_face_count':v=v[:-1]
 da=ux.UxDataArray(v,dims=['n_face'],uxgrid=grid)
 x=np.arange(-177.5,180,5);y=np.arange(-77.5,80,5)
 a=da.remap.to_rectilinear(x,y).values;tx,ty=np.meshgrid(x,y)
 return metrics(a,np.full(tx.shape,7) if case=='constant' else field(tx,ty))

def xu_mesh(case):
 import xugrid as xu
 # Cartesian local triangular mesh; its x/y units are metres by default.
 from scipy.spatial import Delaunay
 x,y=np.meshgrid(np.linspace(0,10,12),np.linspace(0,10,12));nodes=np.stack([x.ravel(),y.ravel()],-1)
 faces=Delaunay(nodes).simplices
 grid=xu.Ugrid2d(nodes[:,0],nodes[:,1],-1,faces,is_projected=case!='spherical')
 src=xu.UgridDataArray(xr.DataArray(np.full(len(faces),7.) if case=='constant' else np.sin(grid.face_x/10),dims=[grid.face_dimension]),grid)
 tx,ty=np.meshgrid(np.linspace(1,9,10),np.linspace(1,9,10));tn=np.stack([tx.ravel(),ty.ravel()],-1);tf=Delaunay(tn).simplices
 target=xu.Ugrid2d(tn[:,0],tn[:,1],-1,tf,is_projected=case!='spherical')
 target=xu.UgridDataArray(xr.DataArray(np.ones(len(tf)),dims=[target.face_dimension]),target)
 if case=='overlap':r=xu.OverlapRegridder(src,target,method='mean')
 else:r=xu.BarycentricInterpolator(src,target)
 a=r.regrid(src).values
 return metrics(a,np.full(len(tf),7.) if case=='constant' else np.sin(target.grid.face_x/10))

def raster_crs(case):
 import rasterio
 from rasterio.transform import from_origin
 from rasterio.warp import reproject,Resampling,calculate_default_transform
 from pyproj import Transformer
 from scipy.interpolate import RegularGridInterpolator
 ny,nx=40,60;dx=.1
 transform=from_origin(5,48,dx,dx)
 xx,yy=np.meshgrid(5+(np.arange(nx)+.5)*dx,48-(np.arange(ny)+.5)*dx)
 a=np.full((ny,nx),7.) if case=='constant' else field(xx,yy)
 dst_t,w,h=calculate_default_transform(4326,2056,nx,ny,5,44,11,48)
 dst=np.full((h,w),np.nan)
 reproject(a,dst,src_transform=transform,src_crs=4326,dst_transform=dst_t,dst_crs=2056,src_nodata=np.nan,dst_nodata=np.nan,resampling=Resampling.bilinear)
 u,v=np.meshgrid(np.arange(w)+.5,np.arange(h)+.5);east,north=dst_t*(u,v)
 lo,la=Transformer.from_crs(2056,4326,always_xy=True).transform(east,north)
 return metrics(dst,np.full(dst.shape,7.) if case=='constant' else field(lo,la))

def healpy_order(case):
 import healpy as hp
 lon,lat=hp.pix2ang(8,np.arange(768),lonlat=True);v=field(lon,lat)
 if case=='ud_grade_intensive':
  ans=hp.ud_grade(v,4,power=0);a,b=hp.pix2ang(4,np.arange(192),lonlat=True)
  return {**metrics(ans,field(a,b)),'mean_change':float(ans.mean()-v.mean())}
 if case=='ud_grade_extensive':
  ans=hp.ud_grade(v,4,power=-2);return {'relative_sum_error':float(abs(ans.sum()-v.sum())/v.sum())}
 if case=='wrong_scaling':
  ans=hp.ud_grade(v,4,power=-2);return {'mean_ratio':float(ans.mean()/v.mean())}
 nested=hp.reorder(v,r2n=True)
 sample_lon=np.arange(-175,180,10);sample_lat=np.linspace(-70,70,len(sample_lon))
 a=hp.get_interp_val(nested,sample_lon,sample_lat,lonlat=True,nest=case=='nested_correct')
 return metrics(a,field(sample_lon,sample_lat))

mode=sys.argv[1]
if __name__=='__main__' and mode=='compiled':
 for method in ['CONSERVE','NEAREST_STOD']:
  for const in [False,True]:probe('ESMPy',f'icosahedral_{method}_{const}',lambda m=method,c=const:esmf_mesh(m,c))
 for c in ['smooth','constant','constant_identity','constant_normed','mask','missing_corners','folded_cell','staggered_vector']:probe('xESMF',f'roms_conservative_{c}',lambda c=c:roms_conserve(c))
elif __name__=='__main__' and mode=='python':
 for c in ['smooth','constant','nan_hole','wrong_face_count']:probe('UXarray',f'icosahedral_{c}',lambda c=c:ux_mesh(c))
 for c in ['smooth','constant','overlap','spherical']:probe('Xugrid',c,lambda c=c:xu_mesh(c))
 for c in ['smooth','constant']:probe('Rasterio',f'4326_to_2056_{c}',lambda c=c:raster_crs(c))
 for c in ['nested_correct','nested_wrong','ud_grade_intensive','ud_grade_extensive','wrong_scaling']:probe('Healpy',c,lambda c=c:healpy_order(c))
