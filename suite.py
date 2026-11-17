"""Synthetic horizontal remapping probes. All geometries small; no memory stress."""
import os
os.environ.setdefault('NUMBA_CACHE_DIR','/tmp/geobench-numba')
os.environ.setdefault('MPLCONFIGDIR','/tmp/geobench-mpl')
os.environ.setdefault('EARTHKIT_GEO_CONFIG_FILE','/tmp/geobench-earthkit.yaml')
import sys,json,time,traceback,warnings,subprocess,importlib.metadata as md
from pathlib import Path
import numpy as np
import xarray as xr
from scipy.spatial import ConvexHull
ROOT=Path(__file__).parent
OUT=ROOT/'results'; OUT.mkdir(exist_ok=True)

def field(lon,lat):
    l,p=np.deg2rad(lon),np.deg2rad(lat)
    return 2+np.cos(p)*np.cos(l)+.25*np.sin(2*p)+.1*np.cos(3*l)*np.cos(p)**2

def xyz_to_ll(v):
    v=v/np.linalg.norm(v,axis=-1,keepdims=True)
    return np.rad2deg(np.arctan2(v[...,1],v[...,0])),np.rad2deg(np.arcsin(v[...,2]))

def geometry(kind):
    # Cell centres. Rectilinear and ROMS share a regional target; others global.
    if kind=='rectilinear':
        lon,lat=np.meshgrid(np.arange(-30.,31.,2),np.arange(-20.,21.,2))
    elif kind=='roms':
        x,y=np.meshgrid(np.linspace(-30,30,31),np.linspace(-20,20,21))
        lon=x+2*np.sin(np.deg2rad(y*4));lat=y+1.5*np.sin(np.deg2rad(x*3))
    elif kind=='satellite_swath':
        a,b=np.meshgrid(np.linspace(-12,12,25),np.linspace(-55,55,45))
        lon=((175+a+8*np.sin(np.deg2rad(b))+180)%360)-180;lat=b+.08*a
    elif kind=='healpix':
        import healpy as hp
        lon,lat=hp.pix2ang(8,np.arange(hp.nside2npix(8)),lonlat=True)
    elif kind=='icosahedral':
        import trimesh
        mesh=trimesh.creation.icosphere(subdivisions=2)
        lon,lat=xyz_to_ll(mesh.vertices[mesh.faces].mean(axis=1))
    elif kind=='gaussian':
        mu,_=np.polynomial.legendre.leggauss(32)
        lon,lat=np.meshgrid(np.arange(0.,360.,5.625),np.rad2deg(np.arcsin(mu)))
    return np.asarray(lon),np.asarray(lat)

def target(kind):
    if kind in ('rectilinear','roms'):
        return np.meshgrid(np.arange(-25.,26.,1.5),np.arange(-15.,16.,1.5))
    if kind=='satellite_swath':
        x,y=np.meshgrid(np.arange(170.,191.,1.),np.arange(-45.,46.,3.)); return (x+180)%360-180,y
    return np.meshgrid(np.arange(-177.5,180,5),np.arange(-77.5,80,5))

SCENARIOS=['smooth','constant','nan_hole','mask_hole','reverse','lon360','duplicate','bad_lat','categorical']

def sample(kind,scenario):
    lo,la=geometry(kind);tx,ty=target(kind)
    val=field(lo,la);truth=field(tx,ty)
    if scenario=='constant':val[:]=7;truth[:]=7
    if scenario=='categorical':val=(np.sin(np.deg2rad(lo))>0).astype(float);truth=(np.sin(np.deg2rad(tx))>0).astype(float)
    mask=np.ones(lo.shape,dtype=np.int32)
    if scenario in ('nan_hole','mask_hole'):
        # Five percent of samples removed in a deterministic band; mask_hole keeps a poison sentinel.
        hole=(np.arange(lo.size).reshape(lo.shape)%19==0)
        if scenario=='nan_hole':val[hole]=np.nan
        else:mask[hole]=0;val[hole]=1e6
    if scenario=='reverse':lo,la,val,mask=[a[::-1].copy() for a in (lo,la,val,mask)]
    if scenario=='lon360':lo=lo%360
    if scenario=='duplicate':
        if lo.ndim==2:
            lo[:,-1]=lo[:,-2];la[:,-1]=la[:,-2]
        else:lo[-1]=lo[-2];la[-1]=la[-2]
    if scenario=='bad_lat':la.flat[lo.size//2]=95.
    return lo,la,val,mask,tx,ty,truth

class Unsupported(Exception):pass

def array2d(lo,la,v,mask=None):
    if lo.ndim!=2:raise Unsupported('Requires structured 2-D topology; no implicit scattered-point fallback')
    return xr.DataArray(v,dims=('y','x'),coords={'lon':(('y','x'),lo),'lat':(('y','x'),la)})

def apply(pkg,kind,scenario,lo,la,v,mask,tx,ty):
    v=v.copy();v[mask==0]=np.nan # explicit mask adapter; xESMF receives mask natively below
    if pkg in ('scipy','xarray'):
        if kind not in ('rectilinear','gaussian'):raise Unsupported('Rectilinear coordinates required')
        if pkg=='scipy':
            from scipy.interpolate import RegularGridInterpolator
            return RegularGridInterpolator((la[:,0],lo[0]),v,bounds_error=False,fill_value=np.nan)(np.stack([ty,tx],-1))
        da=xr.DataArray(v,dims=('lat','lon'),coords={'lat':la[:,0],'lon':lo[0]})
        return da.interp(lat=xr.DataArray(ty,dims=('y','x')),lon=xr.DataArray(tx,dims=('y','x'))).values
    if pkg.startswith('pyresample'):
        from pyresample import geometry as pr_geometry,kd_tree
        src=pr_geometry.SwathDefinition(lons=lo,lats=la);dst=pr_geometry.SwathDefinition(lons=tx,lats=ty)
        # Omit missing samples explicitly: avoids depending on fill-value interpretations.
        valid=np.isfinite(v)
        src=pr_geometry.SwathDefinition(lons=lo[valid],lats=la[valid]);values=v[valid]
        if pkg=='pyresample_nearest':return kd_tree.resample_nearest(src,values,dst,radius_of_influence=900000,fill_value=np.nan)
        return kd_tree.resample_gauss(src,values,dst,radius_of_influence=900000,sigmas=250000,fill_value=np.nan)
    if pkg in ('healpy','astropy_healpix'):
        if kind!='healpix':raise Unsupported('HEALPix-only input')
        # Reverse traversal is not a valid HEALPix storage ordering; deliberately leave it uncorrected.
        if pkg=='healpy':
            import healpy as hp
            return hp.get_interp_val(v,tx,ty,lonlat=True)
        from astropy_healpix import HEALPix
        import astropy.units as u
        return HEALPix(nside=8,order='ring').interpolate_bilinear_lonlat(tx*u.deg,ty*u.deg,v)
    if pkg.startswith('xesmf'):
        import xesmf as xe
        if lo.ndim!=2:raise Unsupported('This structured adapter requires 2D grids; unstructured cells need ESMF mesh handling')
        src=xr.Dataset({'lon':(('y','x'),lo),'lat':(('y','x'),la),'mask':(('y','x'),mask)})
        dst=xr.Dataset({'lon':(('y','x'),tx),'lat':(('y','x'),ty)})
        method=pkg.split('_',1)[1]
        if method=='conservative':
            if kind not in ('rectilinear','gaussian'):raise Unsupported('Conservative curvilinear/swath remapping needs supplied cell corners; centres alone are insufficient')
            def bounds(a):return np.r_[a[0]-(a[1]-a[0])/2,(a[1:]+a[:-1])/2,a[-1]+(a[-1]-a[-2])/2]
            src=src.assign_coords(lon_b=('xb',bounds(lo[0])),lat_b=('yb',bounds(la[:,0])))
            dst=dst.assign_coords(lon_b=('xb',bounds(tx[0])),lat_b=('yb',bounds(ty[:,0])))
        start=time.perf_counter();r=xe.Regridder(src,dst,method,periodic=(kind=='gaussian' and method!='conservative'),unmapped_to_nan=True)
        build=time.perf_counter()-start
        ans=r(xr.DataArray(v,dims=('y','x')),skipna=True,na_thres=.5).values
        return ans,{'build_seconds':build,'weights_nnz':int(r.weights.data.nnz)}
    if pkg in ('rasterio','rioxarray','odc_geo'):
        if kind!='rectilinear':raise Unsupported('Affine raster workflow: curvilinear/swath/mesh geolocation requires a different adapter')
        import rasterio
        from rasterio.transform import from_bounds
        from rasterio.warp import reproject,Resampling
        # GeoTIFF rows run north-to-south; sort coordinates and values explicitly.
        ix=np.argsort(lo[0]);iy=np.argsort(la[:,0])[::-1];data=v[iy][:,ix]
        xs=lo[0,ix];ys=la[iy,0]
        transform=from_bounds(xs[0]-1,ys[-1]-1,xs[-1]+1,ys[0]+1,len(xs),len(ys))
        dst_transform=from_bounds(tx.min()-.75,ty.min()-.75,tx.max()+.75,ty.max()+.75,tx.shape[1],tx.shape[0])
        if pkg=='rasterio':
            dest=np.full(tx.shape,np.nan)
            reproject(data,dest,src_transform=transform,src_crs='EPSG:4326',dst_transform=dst_transform,dst_crs='EPSG:4326',src_nodata=np.nan,dst_nodata=np.nan,resampling=Resampling.bilinear)
            return dest[::-1]
        import rioxarray
        da=xr.DataArray(data,dims=('y','x'),coords={'x':xs,'y':ys}).rio.write_crs(4326).rio.write_nodata(np.nan)
        if pkg=='rioxarray':return da.rio.reproject(4326,shape=tx.shape,transform=dst_transform,resampling=Resampling.bilinear).values[::-1]
        from odc.geo import GeoBox
        from odc.geo.xr import xr_reproject
        return xr_reproject(da.chunk({'y':10,'x':10}),GeoBox((tx.shape[0],tx.shape[1]),dst_transform,'EPSG:4326'),resampling='bilinear').compute().values[::-1]
    if pkg=='earthkit_mir':
        from earthkit.geo import regrid
        if kind=='healpix':spec={'grid':'H8','ordering':'ring'}
        elif kind=='gaussian':spec={'grid':'F16'}
        else:raise Unsupported('MIR gridspec workflow tested for HEALPix and full Gaussian only')
        da=xr.DataArray(v.ravel(),dims='values',name='z')
        # Gaussian F16 requires north-to-south scanning.
        if kind=='gaussian' and scenario!='reverse':da=xr.DataArray(v[::-1].ravel(),dims='values',name='z')
        
        slon,slat=lo.ravel(),la.ravel()
        if kind=='gaussian' and scenario!='reverse':slon,slat=lo[::-1].ravel(),la[::-1].ravel()
        da=da.assign_coords(longitude=('values',slon),latitude=('values',slat))
        return regrid(da,in_grid=spec,out_grid={'grid':[5,5]},interpolation='linear') # separate target generated by MIR
    if pkg.startswith('cdo'):
        import shutil
        exe=shutil.which('cdo') or str(ROOT/'compiled/bin/cdo')
        
        if lo.ndim==1:gridtype='unstructured'; dims=('cell',)
        else:gridtype='curvilinear';dims=('y','x')
        p=OUT/f'{pkg}_{kind}_{scenario}';p.mkdir(exist_ok=True)
        ds=xr.Dataset({'z':(dims,v),'lon':(dims,lo),'lat':(dims,la)})
        ds.lon.attrs.update(standard_name='longitude',units='degrees_east');ds.lat.attrs.update(standard_name='latitude',units='degrees_north');ds.z.attrs['coordinates']='lon lat'
        
        if pkg=='cdo_conservative' and kind!='healpix':
            if kind=='icosahedral':
                import trimesh
                m=trimesh.creation.icosphere(subdivisions=2)
                bx,by=xyz_to_ll(m.vertices[m.faces])
            else:
                # Infer synthetic quadrilateral corners by linear extrapolation of centres.
                # This is an adapter convenience, not a substitute for measured satellite footprints.
                def corner(a):
                    pad=np.pad(a,1,mode='edge')
                    pad[0,1:-1]=2*a[0]-a[1];pad[-1,1:-1]=2*a[-1]-a[-2]
                    pad[:,0]=2*pad[:,1]-pad[:,2];pad[:,-1]=2*pad[:,-2]-pad[:,-3]
                    return (pad[:-1,:-1]+pad[1:,:-1]+pad[:-1,1:]+pad[1:,1:])/4
                # Use baseline geometry; reversing storage must reverse cell corner arrays too.
                a,b=geometry(kind)
                a=np.rad2deg(np.unwrap(np.deg2rad(a),axis=1))
                cx,cy=corner(a),corner(b)
                bx=np.stack([cx[:-1,:-1],cx[:-1,1:],cx[1:,1:],cx[1:,:-1]],-1)
                by=np.stack([cy[:-1,:-1],cy[:-1,1:],cy[1:,1:],cy[1:,:-1]],-1)
                by=np.clip(by,-90,90)
            if scenario=='reverse':bx,by=bx[::-1],by[::-1]
            ds['lon_bnds']=((*dims,'nv'),bx);ds['lat_bnds']=((*dims,'nv'),by)
            ds.lon.attrs['bounds']='lon_bnds';ds.lat.attrs['bounds']='lat_bnds'
        if kind=='healpix':
            ds=ds.drop_vars(['lon','lat']);ds.z.attrs.pop('coordinates',None)
            (p/'source.txt').write_text('gridtype = healpix\ngridsize = 768\nrefinement_level = 3\nindexing_scheme = ring\n')
        ds.to_netcdf(p/'input.nc')
        dx=tx[0,1]-tx[0,0]
        # Swath target uses continuous longitudes 170..190 to avoid a false negative increment at dateline.
        xfirst=float(tx[0,0]); dx=1 if kind=='satellite_swath' else float(dx)
        (p/'target.txt').write_text(f'gridtype = lonlat\nxsize = {tx.shape[1]}\nysize = {tx.shape[0]}\nxfirst = {xfirst}\nxinc = {dx}\nyfirst = {ty[0,0]}\nyinc = {ty[1,0]-ty[0,0]}\n')
        op={'cdo':'remapnn','cdo_bilinear':'remapbil','cdo_conservative':'remapcon'}[pkg]
        source=[f'-setgrid,{p}/source.txt',str(p/'input.nc')] if kind=='healpix' else [str(p/'input.nc')]
        cmd=[exe,'-O',f'{op},{p}/target.txt',*source,str(p/'output.nc')]
        proc=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
        (p/'stderr.log').write_text(proc.stderr)
        if proc.returncode:raise RuntimeError(proc.stderr[-3000:])
        with xr.open_dataset(p/'output.nc') as d:return d.z.values.squeeze()
    raise Unsupported('No adapter')

def run(pkg):
    rows=[]
    for kind in ['rectilinear','roms','satellite_swath','icosahedral','healpix','gaussian']:
      for scenario in SCENARIOS:
        row=dict(package=pkg,grid=kind,scenario=scenario)
        t=time.perf_counter()
        try:
          args=sample(kind,scenario)
          with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter('always');res=apply(pkg,kind,scenario,*args[:-1])
          extra={}
          if isinstance(res,tuple):res,extra=res
          if isinstance(res,xr.DataArray):
            # MIR owns its output grid. Extract coordinates for the analytic oracle.
            res=res.squeeze(); coords=res.coords
            ll=coords.get('longitude',coords.get('lon'));pp=coords.get('latitude',coords.get('lat'))
            if ll is None or pp is None:raise RuntimeError(f'MIR output missing recognizable coordinates: {list(coords)}')
            bl, bp=xr.broadcast(ll,pp); bl=bl.transpose(*res.dims); bp=bp.transpose(*res.dims)
            truth=field(bl.values,bp.values)
            if scenario=='constant':truth=np.full_like(truth,7)
            if scenario=='categorical':truth=(np.sin(np.deg2rad(bl.values))>0).astype(float)
            a=res.values
          else:a=np.asarray(res);truth=args[-1]
          if a.shape!=truth.shape:raise RuntimeError(f'Output shape {a.shape} does not match oracle {truth.shape}')
          ok=np.isfinite(a);err=a[ok]-truth[ok]
          row.update(status='completed',finite_fraction=float(ok.mean()),rmse=float(np.sqrt(np.mean(err**2))) if ok.any() else None,max_error=float(np.max(np.abs(err))) if ok.any() else None,output_min=float(np.min(a[ok])) if ok.any() else None,output_max=float(np.max(a[ok])) if ok.any() else None,warnings=[str(w.message) for w in ws][:8],**extra)
          # Indicators, not verdicts: nearest and weighted methods have different accuracy.
          flags=[]
          if not ok.any():flags.append('all_missing')
          if scenario=='constant' and (not ok.all() or (ok.any() and np.max(np.abs(err))>1e-9)):flags.append('constant_or_coverage')
          if scenario=='mask_hole' and ok.any() and np.max(np.abs(a[ok]))>10:flags.append('masked_sentinel_leak')
          if scenario=='categorical' and np.any(ok & (np.abs(a-np.round(a))>1e-9)):flags.append('fractional_categories')
          if scenario=='bad_lat':flags.append('invalid_coordinate_accepted')
          if row.get('rmse') is not None and row['rmse']>.1:flags.append('large_error')
          row['flags']=flags
        except Unsupported as e:row.update(status='not_exercised',error=str(e))
        except BaseException as e:row.update(status='error',error=f'{type(e).__name__}: {e}',traceback=traceback.format_exc())
        row['seconds']=time.perf_counter()-t;rows.append(row)
        (OUT/f'{pkg}.json').write_text(json.dumps(rows,indent=2,allow_nan=False))
        print(pkg,kind,scenario,row['status'],row.get('flags',[]),flush=True)
    return rows

if __name__=='__main__':run(sys.argv[1])
