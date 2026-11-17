"""Larger synthetic remapping benchmarks; fixture prep, weight setup and application separated.
Run through run_large.py. Inputs are deterministic; no malformed-input stress in this timing tier.
"""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS']:os.environ[key]='1'
os.environ.setdefault('NUMBA_CACHE_DIR','/tmp/geobench-numba');os.environ.setdefault('MPLCONFIGDIR','/tmp/geobench-mpl');os.environ.setdefault('EARTHKIT_GEO_CONFIG_FILE','/tmp/geobench-earthkit.yaml')
import sys,json,time,traceback,gc,tempfile,subprocess,shutil,warnings,resource
from pathlib import Path
import numpy as np,xarray as xr
from suite import field,xyz_to_ll
ROOT=Path(__file__).parent
ENVROOT=Path(os.environ.get('BENCH_ENV_ROOT',ROOT))
os.environ['PATH']=str(ENVROOT/'compiled/bin')+':'+os.environ['PATH']
CLOCK=time.perf_counter

def global_target(n):
 step=180/n;k=int(80/step)
 return np.meshgrid(np.arange(2*n)*step,np.arange(k,-k-1,-1)*step)

def fixtures(grid,n):
 info={'grid':grid,'scale':n}
 if grid in ('rectilinear','roms','roms_mesh','satellite_swath'):
  if grid=='satellite_swath':
   x=np.linspace(-12,12,n);y=np.linspace(-55,55,n*2);a,b=np.meshgrid(x,y);lo=175+a+8*np.sin(np.deg2rad(b));la=b+.08*a
   tx,ty=np.meshgrid(np.linspace(170.2,189.8,n),np.linspace(-44.8,44.8,n*2))
  else:
   x=np.linspace(-30,30,n);y=np.linspace(-20,20,n);a,b=np.meshgrid(x,y)
   lo=a;la=b
   if grid in ('roms','roms_mesh'):lo=a+2*np.sin(np.deg2rad(b*4));la=b+1.5*np.sin(np.deg2rad(a*3))
   tx,ty=np.meshgrid(np.linspace(-24.9,24.9,n),np.linspace(-14.9,14.9,n))
 elif grid=='gaussian':
  # Gaussian latitudes obtained with scipy's fast roots routine; not numpy's dense eigenproblem.
  from scipy.special import roots_legendre
  mu,w=roots_legendre(n);x=np.arange(2*n)*360/(2*n);y=np.rad2deg(np.arcsin(mu));lo,la=np.meshgrid(x,y)
  tx,ty=global_target(n)
 elif grid=='healpix':
  import healpy as hp
  side=n//2;lo,la=hp.pix2ang(side,np.arange(hp.nside2npix(side)),lonlat=True);info['nside']=side
  tx,ty=global_target(n)
 elif grid=='icosahedral':
  import trimesh
  sub=max(1,int(np.log2(n))-3);mesh=trimesh.creation.icosphere(subdivisions=sub)
  lo,la=xyz_to_ll(mesh.vertices[mesh.faces].mean(axis=1));info.update(subdivisions=sub,vertices=mesh.vertices,faces=mesh.faces)
  tx,ty=global_target(n)
 elif grid.startswith('crs_'):
  # WGS84 lon/lat -> Swiss LV95 or Web Mercator, with raster values resampled.
  from rasterio.transform import from_bounds
  from rasterio.warp import calculate_default_transform
  from pyproj import Transformer
  dst_crs=2056 if grid.endswith('2056') else 3857
  transform=from_bounds(5,44,11,48,n,n)
  lo,la=np.meshgrid(5+(np.arange(n)+.5)*6/n,48-(np.arange(n)+.5)*4/n)
  dt,width,height=calculate_default_transform(4326,dst_crs,n,n,5,44,11,48)
  # Fixed square output for comparable packages on each CRS profile.
  from rasterio.transform import from_bounds as bounds_transform
  dt=bounds_transform(dt.c,dt.f+dt.e*height,dt.c+dt.a*width,dt.f,n,n)
  col,row=np.meshgrid(np.arange(n)+.5,np.arange(n)+.5);xx,yy=dt*(col,row)
  tx,ty=Transformer.from_crs(dst_crs,4326,always_xy=True).transform(xx,yy)
  info.update(src_transform=transform,dst_transform=dt,dst_crs=dst_crs,dst_x=xx[0],dst_y=yy[:,0])
 else:raise ValueError(grid)
 if grid=='roms_mesh':lo=8+lo/30;la=46+la/20;tx=8+tx/30;ty=46+ty/20
 v=field(lo,la);truth=field(tx,ty)
 import hashlib
 info['source_geometry_sha256']=hashlib.sha256(lo.tobytes()+la.tobytes()).hexdigest()
 info['destination_geometry_sha256']=hashlib.sha256(tx.tobytes()+ty.tobytes()).hexdigest()
 info['values_sha256']=hashlib.sha256(v.tobytes()).hexdigest()
 info.update(source_shape=list(v.shape),target_shape=list(tx.shape),source_cells=v.size,target_cells=tx.size)
 return lo,la,v,tx,ty,truth,info

def corners(a):
 p=np.pad(a,1,mode='edge');p[0,1:-1]=2*a[0]-a[1];p[-1,1:-1]=2*a[-1]-a[-2];p[:,0]=2*p[:,1]-p[:,2];p[:,-1]=2*p[:,-2]-p[:,-3]
 return (p[:-1,:-1]+p[1:,:-1]+p[:-1,1:]+p[1:,1:])/4

def import_engine(pkg):
 if pkg.startswith('xesmf'):import xesmf
 elif pkg.startswith('pyresample'):from pyresample import kd_tree
 elif pkg=='scipy':from scipy.interpolate import RegularGridInterpolator
 elif pkg=='xarray':import scipy.interpolate
 elif pkg in ('healpy','astropy_healpix'):
  import healpy
  if pkg=='astropy_healpix':import astropy_healpix
 elif pkg in ('rasterio','rioxarray','odc_geo','gdal_cli'):
  import rasterio,rioxarray
  if pkg=='odc_geo':import odc.geo.xr
 elif pkg=='earthkit_mir':from earthkit.geo import regrid
 elif pkg=='uxarray':import uxarray
 elif pkg=='esmpy':
  import esmpy as E;E.Manager(debug=False)
 elif pkg=='iris':import iris,esmf_regrid
 elif pkg=='xugrid':import xugrid
 elif pkg=='pyproj':import pyproj

# API contract: return an eager apply callable, setup metadata, optional cleanup callback.
def build(pkg,grid,f,work):
 lo,la,v,tx,ty,truth,info=f;extra={};cleanup=lambda:None
 if pkg=='scipy':
  from scipy.interpolate import RegularGridInterpolator
  xx=lo[0];vv=v
  if grid=='gaussian':xx=np.r_[xx,360.];vv=np.concatenate([v,v[:,:1]],axis=1)
  r=RegularGridInterpolator((la[:,0],xx),vv,bounds_error=False,fill_value=np.nan)
  points=np.stack([ty,tx],axis=-1)
  return lambda:r(points),extra,cleanup
 if pkg=='xarray':
  xx=lo[0];vv=v
  if grid=='gaussian':xx=np.r_[xx,360.];vv=np.concatenate([v,v[:,:1]],axis=1)
  da=xr.DataArray(vv,dims=('lat','lon'),coords={'lat':la[:,0],'lon':xx});x=xr.DataArray(tx,dims=('y','x'));y=xr.DataArray(ty,dims=('y','x'))
  extra['setup_note']='xarray interp constructs interpolation machinery during apply; weights not exposed separately'
  return lambda:da.interp(lat=y,lon=x).values,extra,cleanup
 if pkg.startswith('xesmf'):
  import xesmf as xe
  method=pkg.split('_',1)[1]
  src=xr.Dataset({'lon':(('y','x'),lo),'lat':(('y','x'),la)});dst=xr.Dataset({'lon':(('y','x'),tx),'lat':(('y','x'),ty)})
  if method=='conservative':
   src['lon_b']=(('yb','xb'),corners(lo));src['lat_b']=(('yb','xb'),np.clip(corners(la),-90,90));dst['lon_b']=(('yb','xb'),corners(tx));dst['lat_b']=(('yb','xb'),np.clip(corners(ty),-90,90))
  da=xr.DataArray(v,dims=('y','x'));r=xe.Regridder(src,dst,method,periodic=grid=='gaussian' and method!='conservative',unmapped_to_nan=True)
  extra['weights_nnz']=int(r.weights.data.nnz)
  return lambda:r(da).values,extra,cleanup
 if pkg.startswith('pyresample'):
  from pyresample import geometry,kd_tree
  src=geometry.SwathDefinition(lons=(lo+180)%360-180,lats=la);dst=geometry.SwathDefinition(lons=(tx+180)%360-180,lats=ty)
  # Keep radius large enough to avoid sparse low-resolution pilot gaps; Gaussian kernel is explicit.
  radius=900000 if grid!='satellite_swath' else 300000
  a,b,idx,dist=kd_tree.get_neighbour_info(src,dst,radius_of_influence=radius,neighbours=1 if pkg.endswith('nearest') else 8,nprocs=1)
  if pkg.endswith('nearest'):return lambda:kd_tree.get_sample_from_neighbour_info('nn',tx.shape,v,a,b,idx,fill_value=np.nan),extra,cleanup
  return lambda:kd_tree.get_sample_from_neighbour_info('custom',tx.shape,v,a,b,idx,distance_array=dist,weight_funcs=lambda d:np.exp(-(d/100000)**2),fill_value=np.nan),extra,cleanup
 if pkg in ('healpy','astropy_healpix'):
  if pkg=='healpy':
   import healpy as hp
   idx,weights=hp.get_interp_weights(info['nside'],tx,ty,lonlat=True)
   return lambda:np.sum(v[idx]*weights,axis=0),{'setup_note':'Healpy four-neighbour weights built once; same weights used in application'},cleanup
  from astropy_healpix import HEALPix
  import astropy.units as u
  h=HEALPix(nside=info['nside'],order='ring');idx,weights=h.bilinear_interpolation_weights((tx%360)*u.deg,ty*u.deg)
  return lambda:np.sum(v[idx]*weights,axis=0),{'setup_note':'Astropy weights built with nonnegative longitudes to avoid known failure'},cleanup
 if pkg in ('rasterio','rioxarray','odc_geo'):
  from rasterio.warp import reproject,Resampling
  if not grid.startswith('crs_'):raise ValueError('Raster tests require explicit CRS conversion profile')
  if pkg=='rasterio':
   dst=np.empty(tx.shape)
   def apply():
    reproject(v,dst,src_transform=info['src_transform'],src_crs='EPSG:4326',dst_transform=info['dst_transform'],dst_crs=info['dst_crs'],src_nodata=np.nan,dst_nodata=np.nan,resampling=Resampling.bilinear,num_threads=1)
    return dst
   return apply,{'setup_note':'GDAL warp geometry and resampling are fused during apply; separate reusable weights unavailable'},cleanup
  import rioxarray
  da=xr.DataArray(v,dims=('y','x'),coords={'x':lo[0],'y':la[:,0]}).rio.write_crs(4326).rio.write_nodata(np.nan)
  if pkg=='rioxarray':return lambda:da.rio.reproject(info['dst_crs'],shape=tx.shape,transform=info['dst_transform'],resampling=Resampling.bilinear).values,{'setup_note':'Warp geometry and resampling fused during apply'},cleanup
  from odc.geo import GeoBox
  from odc.geo.xr import xr_reproject
  box=GeoBox(tx.shape,info['dst_transform'],f"EPSG:{info['dst_crs']}")
  # Explicit synchronous scheduler makes one thread comparable to other runs; compute inside apply.
  return lambda:xr_reproject(da.chunk({'y':512,'x':512}),box,resampling='bilinear').compute(scheduler='synchronous').values,{'setup_note':'Dask graph creation, warp geometry and eager compute included in apply'},cleanup
 if pkg=='pyproj':
  from pyproj import Transformer
  transformer=Transformer.from_crs(4326,info['dst_crs'],always_xy=True)
  return lambda:transformer.transform(lo,la,errcheck=True),{'setup_note':'Coordinate transformation only; no raster interpolation','output_kind':'coordinate_arrays'},cleanup
 if pkg=='earthkit_mir':
  from earthkit.geo import regrid
  if grid=='healpix':spec={'grid':'H'+str(info['nside']),'ordering':'ring'};vals=v.ravel();lons=lo.ravel();lats=la.ravel()
  else:spec={'grid':'F'+str(info['scale']//2)};vals=v[::-1].ravel();lons=lo[::-1].ravel();lats=la[::-1].ravel()
  da=xr.DataArray(vals,dims='values',name='z',coords={'longitude':('values',lons),'latitude':('values',lats)})
  step=180/info['scale']
  return lambda:regrid(da,in_grid=spec,out_grid={'grid':[step,step],'area':[float(ty.max()),0.,float(ty.min()),float(tx.max())]},interpolation='linear'),{'setup_note':'MIR high-level interface fuses weight work and application; total is measured in apply','mir_step':step,'output_kind':'mir'},cleanup
 if pkg=='uxarray':
  import uxarray as ux
  vertices=info['vertices'];faces=info['faces'];x,y=xyz_to_ll(vertices);g=ux.Grid.from_face_vertices(np.stack([x[faces],y[faces]],-1),latlon=True)
  da=ux.UxDataArray(v,dims=['n_face'],uxgrid=g)
  return lambda:da.remap.to_rectilinear(tx[0],ty[:,0]).values,{'setup_note':'UXarray nearest search is performed during apply; no independent weights timer'},cleanup
 if pkg=='iris':
  from iris.coords import DimCoord
  from iris.cube import Cube
  from esmf_regrid.schemes import ESMFAreaWeighted
  lat=DimCoord(la[:,0],standard_name='latitude',units='degrees');lon=DimCoord(lo[0],standard_name='longitude',units='degrees');lat.guess_bounds();lon.guess_bounds()
  a=DimCoord(ty[:,0],standard_name='latitude',units='degrees');b=DimCoord(tx[0],standard_name='longitude',units='degrees');a.guess_bounds();b.guess_bounds()
  src=Cube(v,dim_coords_and_dims=[(lat,0),(lon,1)]);dst=Cube(np.zeros(tx.shape),dim_coords_and_dims=[(a,0),(b,1)])
  r=ESMFAreaWeighted().regridder(src,dst)
  return lambda:np.ma.filled(r(src).data,np.nan),extra,cleanup
 if pkg=='esmpy':
  import esmpy as E
  def mesh(vs,fs):
   x,y=xyz_to_ll(vs);cx,cy=xyz_to_ll(vs[fs].mean(axis=1));m=E.Mesh(parametric_dim=2,spatial_dim=2,coord_sys=E.CoordSys.SPH_DEG)
   m.add_nodes(len(x),np.arange(1,len(x)+1,dtype=np.int32),np.stack([x,y],-1).ravel(),np.zeros(len(x),np.int32));m.add_elements(len(fs),np.arange(1,len(fs)+1,dtype=np.int32),np.full(len(fs),E.MeshElemType.TRI,np.int32),fs.astype(np.int32).ravel(),element_coords=np.stack([cx,cy],-1).ravel());return m,cx,cy
  sm,_,_=mesh(info['vertices'],info['faces'])
  ny,nx=tx.shape
  dm=E.Grid(np.array([nx,ny],dtype=np.int32),coord_sys=E.CoordSys.SPH_DEG,staggerloc=[E.StaggerLoc.CENTER,E.StaggerLoc.CORNER])
  dm.get_coords(0,staggerloc=E.StaggerLoc.CENTER)[:]=tx.T;dm.get_coords(1,staggerloc=E.StaggerLoc.CENTER)[:]=ty.T
  dm.get_coords(0,staggerloc=E.StaggerLoc.CORNER)[:]=corners(tx).T;dm.get_coords(1,staggerloc=E.StaggerLoc.CORNER)[:]=corners(ty).T
  src=E.Field(sm,meshloc=E.MeshLoc.ELEMENT);dst=E.Field(dm,staggerloc=E.StaggerLoc.CENTER);src.data[:]=v
  r=E.Regrid(src,dst,regrid_method=E.RegridMethod.CONSERVE,unmapped_action=E.UnmappedAction.ERROR)
  extra.update(setup_note='Triangular mesh to the shared lat/lon destination; source/destination geometry matches other icosahedral adapters')
  def apply():r(src,dst);return dst.data.T.copy()
  def clean():r.destroy();src.destroy();dst.destroy();sm.destroy();dm.destroy()
  return apply,extra,clean
 if pkg=='xugrid':
  import xugrid as xu
  # Real CRS conversion first, followed by remapping on a projected local triangular mesh.
  from scipy.spatial import Delaunay
  from pyproj import Transformer
  # Use the shared rectilinear point grid and shared raster destinations, converted to LV95.
  proj=Transformer.from_crs(4326,2056,always_xy=True)
  x,y=proj.transform(lo,la);dx,dy=proj.transform(tx,ty)
  # Two deterministic triangles per structured cell, avoiding unbounded triangulation work.
  ny,nx=v.shape;i=np.arange((ny-1)*nx).reshape(ny-1,nx)[:,:-1].ravel()
  faces=np.concatenate([np.stack([i,i+1,i+nx],-1),np.stack([i+1,i+nx+1,i+nx],-1)])
  srcgrid=xu.Ugrid2d(x.ravel(),y.ravel(),-1,faces)
  # Xugrid face-field overlap expects destination mesh. The adapter has its own explicit
  # mesh-to-mesh test family; its geometry hashes identify the real mesh centroids below.
  dny,dnx=tx.shape;j=np.arange((dny-1)*dnx).reshape(dny-1,dnx)[:,:-1].ravel();df=np.concatenate([np.stack([j,j+1,j+dnx],-1),np.stack([j+1,j+dnx+1,j+dnx],-1)])
  dstgrid=xu.Ugrid2d(dx.ravel(),dy.ravel(),-1,df)
  source_values=np.mean(v.ravel()[faces],axis=1)
  da=xu.UgridDataArray(xr.DataArray(source_values,dims=srcgrid.face_dimension),srcgrid)
  target=xu.UgridDataArray(xr.DataArray(np.zeros(len(df)),dims=dstgrid.face_dimension),dstgrid)
  r=xu.BarycentricInterpolator(da,target)
  back=Transformer.from_crs(2056,4326,always_xy=True);a,b=back.transform(dstgrid.face_x,dstgrid.face_y)
  extra.update(actual_source_cells=len(faces),actual_source_shape=[len(faces)],actual_target_shape=[len(df)],actual_truth=field(a,b),actual_target_cells=len(df),setup_note='Projected local triangular mesh; own mesh-centred test family, not ranked against raster targets')
  return lambda:r.regrid(da).values,extra,cleanup
 if pkg in ('tempest','nco'):
  # Convert the exact same source triangles and destination quadrilaterals into Tempest meshes.
  def command(args):
   command_start=CLOCK()
   p=subprocess.run([str(ENVROOT/'compiled/bin'/args[0]),*args[1:]],capture_output=True,text=True,timeout=300)
   extra.setdefault('native_command_timings',[]).append({'command':args[0],'seconds':CLOCK()-command_start})
   with (work/'commands.log').open('a') as log:log.write(str(args)+'\n'+p.stdout+'\n'+p.stderr+'\n')
   if p.returncode or 'EXCEPTION' in p.stdout:raise RuntimeError(str(args)+'\n'+p.stderr[-2000:]+p.stdout[-3000:])
  def scrip(path,lon,lat,bx,by,shape):
   size=lon.size;k=bx.shape[-1]
   ds=xr.Dataset({'grid_dims':('grid_rank',np.array(shape,np.int32)),'grid_center_lon':('grid_size',lon.ravel()),'grid_center_lat':('grid_size',lat.ravel()),'grid_corner_lon':(('grid_size','grid_corners'),bx.reshape(size,k)),'grid_corner_lat':(('grid_size','grid_corners'),by.reshape(size,k)),'grid_imask':('grid_size',np.ones(size,np.int32))})
   for key in ['grid_center_lon','grid_center_lat','grid_corner_lon','grid_corner_lat']:ds[key].attrs['units']='degrees'
   ds.to_netcdf(path)
  io_start=CLOCK();bx,by=xyz_to_ll(info['vertices'][info['faces']]);scrip(work/'src_scrip.nc',lo,la,bx,by,[lo.size])
  cx,cy=corners(tx),corners(ty);dx=np.stack([cx[:-1,:-1],cx[:-1,1:],cx[1:,1:],cx[1:,:-1]],-1);dy=np.stack([cy[:-1,:-1],cy[:-1,1:],cy[1:,1:],cy[1:,:-1]],-1)
  # Tempest requires counterclockwise corners; reversing corner traversal leaves geometry unchanged.
  if ty[0,0]>ty[-1,0]:dx=dx[...,::-1];dy=dy[...,::-1]
  scrip(work/'dst_scrip.nc',tx,ty,dx,dy,[tx.shape[1],tx.shape[0]])
  xr.Dataset({'z':('ncol',v)}).to_netcdf(work/'data.nc');io=CLOCK()-io_start
  command(['ConvertMeshToExodus','--in',str(work/'src_scrip.nc'),'--out',str(work/'src.g')]);command(['ConvertMeshToExodus','--in',str(work/'dst_scrip.nc'),'--out',str(work/'dst.g')])
  command(['GenerateOverlapMesh','--a',str(work/'src.g'),'--b',str(work/'dst.g'),'--out',str(work/'overlap.g'),'--allow_no_overlap'])
  command(['GenerateOfflineMap','--in_mesh',str(work/'src.g'),'--out_mesh',str(work/'dst.g'),'--ov_mesh',str(work/'overlap.g'),'--in_type','fv','--out_type','fv','--out_map',str(work/'weights.nc'),'--mono'])
  extra.update(io_prepare_seconds=io,setup_note='Same SCRIP geometry as other icosahedral tests; native mesh conversion, overlap and weight generation in setup. Native commands include I/O and launch overhead.')
  def apply():
   if pkg=='tempest':command(['ApplyOfflineMap','--map',str(work/'weights.nc'),'--in_data',str(work/'data.nc'),'--out_data',str(work/'output.nc'),'--var','z','--out_double'])
   else:command(['ncremap','-m',str(work/'weights.nc'),'-i',str(work/'data.nc'),'-o',str(work/'output.nc')])
   t=CLOCK()
   with xr.open_dataset(work/'output.nc') as d:a=d.z.values.reshape(tx.shape).copy()
   extra['output_read_seconds']=CLOCK()-t
   return a
  return apply,extra,cleanup
 if pkg.startswith('cdo_'):
  method=pkg.split('_',1)[1];exe=str(ENVROOT/'compiled/bin/cdo');gen={'nearest':'gennn','bilinear':'genbil','conservative':'gencon'}[method]
  # Input construction and disk I/O accounted separately from native commands.
  io_start=CLOCK();dims=('cell',) if lo.ndim==1 else ('y','x');ds=xr.Dataset({'z':(dims,v),'lon':(dims,lo),'lat':(dims,la)})
  ds.lon.attrs.update(standard_name='longitude',units='degrees_east');ds.lat.attrs.update(standard_name='latitude',units='degrees_north');ds.z.attrs['coordinates']='lon lat'
  source_extra=[]
  if grid=='healpix':
   ds=ds.drop_vars(['lon','lat']);ds.z.attrs.pop('coordinates',None);(work/'source.txt').write_text(f"gridtype=healpix\ngridsize={v.size}\nrefinement_level={int(np.log2(info['nside']))}\nindexing_scheme=ring\n");source_extra=[f'-setgrid,{work}/source.txt']
  if method=='conservative' and grid!='healpix':
   if grid=='icosahedral':bx,by=xyz_to_ll(info['vertices'][info['faces']])
   else:
    cx,cy=corners(lo),corners(la);bx=np.stack([cx[:-1,:-1],cx[:-1,1:],cx[1:,1:],cx[1:,:-1]],-1);by=np.clip(np.stack([cy[:-1,:-1],cy[:-1,1:],cy[1:,1:],cy[1:,:-1]],-1),-90,90)
   ds['lon_bounds']=((*dims,'nv'),bx);ds['lat_bounds']=((*dims,'nv'),by);ds.lon.attrs['bounds']='lon_bounds';ds.lat.attrs['bounds']='lat_bounds'
  ds.to_netcdf(work/'input.nc');(work/'target.txt').write_text(f"gridtype=lonlat\nxsize={tx.shape[1]}\nysize={tx.shape[0]}\nxfirst={tx[0,0]}\nxinc={tx[0,1]-tx[0,0]}\nyfirst={ty[0,0]}\nyinc={ty[1,0]-ty[0,0]}\n")
  io=CLOCK()-io_start;t=CLOCK();p=subprocess.run([exe,'-O',f'{gen},{work}/target.txt',*source_extra,str(work/'input.nc'),str(work/'weights.nc')],capture_output=True,text=True,timeout=120)
  if p.returncode:raise RuntimeError(p.stderr[-2000:])
  build_native=CLOCK()-t
  extra.update(io_prepare_seconds=io,native_weight_command_seconds=build_native,setup_note='CDO setup includes writing source/target files; core setup subtracts input I/O. Native commands include process launch and native file I/O.')
  def apply():
   p=subprocess.run([exe,'-O',f'remap,{work}/target.txt,{work}/weights.nc',*source_extra,str(work/'input.nc'),str(work/'output.nc')],capture_output=True,text=True,timeout=120)
   if p.returncode:raise RuntimeError(p.stderr[-2000:])
   t=CLOCK()
   with xr.open_dataset(work/'output.nc') as d:a=d.z.values.squeeze().copy()
   extra['output_read_seconds']=CLOCK()-t
   return a
  return apply,extra,cleanup
 raise ValueError('No adapter: '+pkg)

def quality(a,truth,extra,f):
 if extra.get('output_kind')=='coordinate_arrays':
  from pyproj import Transformer
  # Bounded verification sample keeps validation outside timing and avoids another giant allocation.
  x,y=a;step=max(1,x.size//100000);back=Transformer.from_crs(f[-1]['dst_crs'],4326,always_xy=True);lo,la=back.transform(x.ravel()[::step],y.ravel()[::step]);return {'roundtrip_max_degrees':float(np.max(abs(lo-f[0].ravel()[::step])+abs(la-f[1].ravel()[::step]))),'finite_fraction':float((np.isfinite(x)&np.isfinite(y)).mean())}
 if extra.get('output_kind')=='mir':
  da=a.squeeze();x=da.coords.get('longitude',da.coords.get('lon'));y=da.coords.get('latitude',da.coords.get('lat'));x,y=xr.broadcast(x,y);x=x.transpose(*da.dims);y=y.transpose(*da.dims);assert x.shape==f[3].shape and np.allclose(x.values,f[3]) and np.allclose(y.values,f[4]),'MIR destination geometry differs from shared target'
  truth=field(x.values,y.values);a=da.values
 if 'actual_truth' in extra:truth=extra['actual_truth']
 a=np.asarray(a);valid=np.isfinite(a);e=a[valid]-np.asarray(truth)[valid]
 return {'rmse':float(np.sqrt(np.mean(e*e))) if valid.any() else None,'max_error':float(np.max(abs(e))) if valid.any() else None,'finite_fraction':float(valid.mean()),'actual_output_cells':a.size}

def run(pkg,grid,n,repeats,checkpoint=None):
 t=CLOCK();import_engine(pkg);imports=CLOCK()-t
 # One tiny, unrecorded warmup removes package lazy import/JIT startup from large timings.
 with tempfile.TemporaryDirectory(prefix='regrid-warm-') as tmp:
  warm=fixtures(grid,32)
  app,ext,clean=build(pkg,grid,warm,Path(tmp));a=app();clean();del a,app,warm;gc.collect()
 t=CLOCK();f=fixtures(grid,n);prep=CLOCK()-t
 info={k:v for k,v in f[-1].items() if k not in ('vertices','faces','src_transform','dst_transform','dst_x','dst_y')}
 runs=[]
 for repeat in range(repeats):
  with tempfile.TemporaryDirectory(prefix='regrid-large-') as tmp:
   gc.collect();t=CLOCK()
   with warnings.catch_warnings(record=True) as ws:
    warnings.simplefilter('always');app,extra,clean=build(pkg,grid,f,Path(tmp));setup_wall=CLOCK()-t;t=CLOCK();a=app();apply_wall=CLOCK()-t
   setup=setup_wall-extra.get('io_prepare_seconds',0);apply=apply_wall-extra.get('output_read_seconds',0)
   q=quality(a,f[-2],extra,f)
   mode='split' if pkg.startswith(('xesmf_','pyresample_','cdo_')) or pkg in ('healpy','astropy_healpix','esmpy','iris','tempest','nco','xugrid') else 'fused'
   extra['timing_mode']=mode
   extra['warmup']='One complete 32-scale operation before recorded repetitions'
   if pkg=='earthkit_mir':extra['cache_note']='High-level MIR may reuse internal caches across repetitions; per-repeat timings retained'
   if extra.get('output_kind')!='coordinate_arrays':
    av=np.asarray(a.values if isinstance(a,xr.DataArray) else a).ravel();sample_indices=np.linspace(0,len(av)-1,min(32,len(av)),dtype=int);extra['output_sample']=[float(z) if np.isfinite(z) else None for z in av[sample_indices]]
   row=dict(package=pkg,repeat=repeat,setup_seconds=setup,apply_seconds=apply,total_seconds=setup+apply,setup_wall_seconds=setup_wall,apply_wall_seconds=apply_wall,input_preparation_seconds=prep,import_seconds=imports,**info,**q,**{k:v for k,v in extra.items() if k!='actual_truth'},warnings=[str(w.message) for w in ws][:5])
   clean();del app,a;gc.collect();runs.append(row)
   if checkpoint:
    tmp=checkpoint.with_suffix('.checkpoint.tmp');tmp.write_text(json.dumps({'status':'partial','package':pkg,'grid':grid,'scale':n,'runs':runs},indent=2,allow_nan=False));tmp.replace(checkpoint)
 return {'status':'completed','package':pkg,'grid':grid,'scale':n,'runs':runs,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}

if __name__=='__main__':
 pkg,grid,n,repeats,out=sys.argv[1:];t=CLOCK()
 try:
  if pkg=='earthkit_mir' and os.environ.get('BENCH_MIR_ISOLATED')!='1':
   # Global MIR caches survive adapter reconstruction. Isolate every measured repeat
   # in a fresh process and fresh persistent-cache directory, while retaining the same inputs.
   collected=[];peaks=[]
   for repeat in range(int(repeats)):
    with tempfile.TemporaryDirectory(prefix='regrid-mir-cold-') as tmp:
     path=Path(tmp)/'record.json';env=os.environ.copy();env['MIR_CACHE_PATH']=str(Path(tmp)/'cache');env['BENCH_MIR_ISOLATED']='1'
     p=subprocess.run([sys.executable,__file__,pkg,grid,n,'1',str(path)],env=env,capture_output=True,text=True,timeout=300)
     if not path.exists():raise RuntimeError(p.stderr[-2000:])
     record=json.loads(path.read_text())
     if record['status']!='completed':raise RuntimeError(record.get('error','MIR child failed'))
     row=record['runs'][0];row['repeat']=repeat;row['cache_note']='Fresh process and fresh MIR_CACHE_PATH per repeat; warmup uses a different 32-scale grid';collected.append(row);peaks.append(record['peak_rss_mib'])
   result={'status':'completed','package':pkg,'grid':grid,'scale':int(n),'runs':collected,'peak_rss_mib':max(peaks),'cache_policy':'fresh_process_and_cache_per_repeat'}
  else:result=run(pkg,grid,int(n),int(repeats),Path(out))
 except Exception as e:
  result={'status':'error','package':pkg,'grid':grid,'scale':int(n),'error':str(e),'traceback':traceback.format_exc()}
  if Path(out).exists():result['runs']=json.loads(Path(out).read_text()).get('runs',[])
 result['worker_seconds']=CLOCK()-t;temp_out=Path(out).with_suffix('.result.tmp');temp_out.write_text(json.dumps(result,indent=2,allow_nan=False));temp_out.replace(out);print(json.dumps({k:v for k,v in result.items() if k not in ('runs','traceback')}),flush=True)
