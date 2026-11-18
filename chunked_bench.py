"""Chunk-layout experiment. Run each profile in a fresh process; see CHUNKED_REPORT.md."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[k]='1'
os.environ.setdefault('NUMBA_CACHE_DIR','/tmp/geobench-numba')
os.environ.setdefault('MPLCONFIGDIR','/tmp/geobench-mpl')
import argparse, hashlib, json, time, traceback, gc, signal
from pathlib import Path
import numpy as np
import xarray as xr
from large_bench import fixtures

ROOT=Path(__file__).parent
OUT=ROOT/'chunked_results'
LAYOUTS=[(1,128,128),(1,256,256),(4,512,512)]
REPEATS=3
N=512

def digest(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def chunks(a):
    return [list(map(int,c)) for c in a.chunks] if a.chunks is not None else None
def make_cube(v):
    a=np.stack([v + 0.125*t for t in range(4)])
    # Missing island crosses several nominal input chunk boundaries.
    a[:,124:132,124:132]=np.nan
    return a

def compare(a,b):
    a=np.asarray(a);b=np.asarray(b)
    both=np.isfinite(a)&np.isfinite(b)
    diff=np.abs(a[both]-b[both])
    # A conservative seam diagnostic: rows/columns around all nominal source
    # chunk cuts, in target index space, compared against full eager output.
    mask=np.zeros(a.shape[-2:],bool)
    for i in range(128,N,128):
        mask[max(0,i-1):i+1,:]=True;mask[:,max(0,i-1):i+1]=True
    seam=np.broadcast_to(mask,a.shape)&both
    return {'finite_mask_mismatches':int(np.count_nonzero(np.isfinite(a)!=np.isfinite(b))),
            'max_abs_error':float(diff.max()) if diff.size else None,
            'seam_max_abs_error':float(np.max(np.abs(a[seam]-b[seam]))) if seam.any() else None,
            'finite_values':int(both.sum())}

def run(tool,grid):
    OUT.mkdir(exist_ok=True)
    result={'tool':tool,'grid':grid,'summary':[],'records':[],'failures':[]}
    def checkpoint():
        (OUT/f'{tool}_{grid}.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    def timed_out(signum, frame):
        raise TimeoutError('complete compute exceeded 60 seconds')
    signal.signal(signal.SIGALRM,timed_out)
    try:
        lo,la,v,tx,ty,truth,info=fixtures(grid,N)
        cube=make_cube(v)
        result['fixture']={'source_geometry_sha256':info['source_geometry_sha256'],
             'destination_geometry_sha256':info['destination_geometry_sha256'],
             'values_sha256':digest(cube),'shape':list(cube.shape),'missing_count':int(np.isnan(cube).sum())}
        import_start=time.perf_counter()
        if tool=='xesmf':
            import xesmf as xe
        elif tool.startswith('xarray_regrid_'):
            import xarray_regrid
        elif tool=='odc_geo':
            import rioxarray
            from odc.geo import GeoBox
            from odc.geo.xr import xr_reproject
        result['import_seconds']=time.perf_counter()-import_start
        if tool.startswith('xarray_regrid_'):
            from importlib.metadata import version
            result['engine_version']=version('xarray-regrid')
        start=time.perf_counter()
        if tool=='xesmf':
            src=xr.Dataset({'lon':(('y','x'),lo),'lat':(('y','x'),la)})
            dst=xr.Dataset({'lon':(('y','x'),tx),'lat':(('y','x'),ty)})
            op=xe.Regridder(src,dst,'bilinear',unmapped_to_nan=True)
            nnz=int(op.weights.data.nnz)
            def apply(data):return op(data, output_chunks={'y': N, 'x': N})
            da=xr.DataArray(cube,dims=('time','y','x'))
            note='Reusable bilinear sparse weights; explicit full-horizontal output chunks bound graph growth. Inspect rechunk layers; this is not a tiled-output benchmark.'
        elif tool=='xarray':
            da=xr.DataArray(cube,dims=('time','lat','lon'),coords={'lat':la[:,0],'lon':lo[0]})
            def apply(data):return data.interp(lat=ty[:,0],lon=tx[0],method='linear')
            nnz=None
            note='Interpolation machinery is constructed during each application; no reusable weights exposed.'
        elif tool.startswith('xarray_regrid_'):
            if grid!='rectilinear':raise ValueError('Chunked xarray-regrid adapter requires rectilinear axes')
            da=xr.DataArray(cube,dims=('time','lat','lon'),coords={'lat':la[:,0],'lon':lo[0]})
            dst=xr.Dataset(coords={'lat':ty[:,0],'lon':tx[0]})
            method=tool.removeprefix('xarray_regrid_')
            kwargs={'latitude_coord':'lat','skipna':True,'nan_threshold':1.0} if method=='conservative' else {}
            def apply(data):return getattr(data.regrid,method)(dst,**kwargs)
            nnz=None
            note='Public accessor; machinery/weights constructed per call, not shared setup. Native output chunking retained. Conservative: skipna=True, nan_threshold=1.0, latitude correction lat; cells follow meridians/parallels. Linear/nearest delegate to xarray interpolation.'
        elif tool=='odc_geo':
            da=xr.DataArray(cube,dims=('time','y','x'),coords={'x':lo[0],'y':la[:,0]}).rio.write_crs(4326).rio.write_nodata(np.nan)
            box=GeoBox(tx.shape,info['dst_transform'],f"EPSG:{info['dst_crs']}")
            def apply(data):return xr_reproject(data,box,resampling='bilinear')
            nnz=None
            note='Warp geometry and interpolation are fused in application; GeoBox construction alone is setup.'
        else:raise ValueError(tool)
        setup=time.perf_counter()-start
        start=time.perf_counter();ref_obj=apply(da);ref_lazy=hasattr(ref_obj.data,'__dask_graph__')
        reference=np.asarray(ref_obj.compute(scheduler='synchronous').values if ref_lazy else ref_obj.values)
        ref_s=time.perf_counter()-start
        result['setup_seconds']=setup;result['reference_seconds']=ref_s;result['reference_was_lazy']=ref_lazy;result['setup_note']=note;result['weights_nnz']=nnz
        for layout in LAYOUTS:
            data=da.chunk(dict(zip(da.dims,layout)))
            rows=[]
            for rep in range(REPEATS):
                try:
                    start=time.perf_counter();out=apply(data);graph_s=time.perf_counter()-start
                    lazy=hasattr(out.data,'__dask_graph__')
                    tasks=len(out.data.__dask_graph__()) if lazy else 0
                    graph_names=[str(k) for k in out.data.__dask_graph__().layers] if lazy and hasattr(out.data.__dask_graph__(),'layers') else []
                    rechunk_layers=[k for k in graph_names if 'rechunk' in k.lower()]
                    start=time.perf_counter();signal.alarm(60)
                    try: values=np.asarray(out.compute(scheduler='synchronous').values if lazy else out.values)
                    finally: signal.alarm(0)
                    compute_s=time.perf_counter()-start
                    row={'tool':tool,'grid':grid,'layout':list(layout),'repeat':rep+1,'setup_seconds_shared':setup,
                         'graph_seconds':graph_s,'compute_seconds':compute_s if lazy else None,
                         'eager_application_seconds':graph_s if not lazy else None,'output_lazy':lazy,
                         'input_chunks':chunks(data),'output_chunks':chunks(out),'graph_tasks':tasks,
                         'scheduler':'synchronous','rechunk_layers':rechunk_layers,'correctness':compare(values,reference),**result['fixture']}
                    rows.append(row);result['records'].append(row);print(tool,grid,layout,'repeat',rep+1,'compute',round(compute_s,3),flush=True);checkpoint()
                    del out,values;gc.collect()
                except Exception as e:
                    result['failures'].append({'tool':tool,'grid':grid,'layout':list(layout),'repeat':rep+1,'error':repr(e),'traceback':traceback.format_exc()})
                    checkpoint();print(tool,grid,layout,'failed',repr(e),flush=True);break
            if rows:
                result['summary'].append({'tool':tool,'grid':grid,'layout':list(layout),'repeats':len(rows),
                    'setup_seconds_shared':setup,'median_graph_seconds':float(np.median([r['graph_seconds'] for r in rows])),
                    'median_compute_seconds':float(np.median([r['compute_seconds'] for r in rows])) if rows[0]['output_lazy'] else None,
                    'median_eager_application_seconds':float(np.median([r['eager_application_seconds'] for r in rows])) if not rows[0]['output_lazy'] else None,
                    'output_lazy':rows[0]['output_lazy'],'input_chunks':rows[0]['input_chunks'],'output_chunks':rows[0]['output_chunks'],
                    'graph_tasks':rows[0]['graph_tasks'],'rechunk_layers':rows[0]['rechunk_layers'],
                    'reference_seconds':ref_s,'reference_was_lazy':ref_lazy,'correctness':{k:max(r['correctness'][k] for r in rows if r['correctness'][k] is not None) if any(r['correctness'][k] is not None for r in rows) else None for k in rows[0]['correctness']},'fixture':result['fixture'],'setup_note':note,'weights_nnz':nnz});checkpoint()
    except Exception as e:
        result['failures'].append({'tool':tool,'grid':grid,'error':repr(e),'traceback':traceback.format_exc()})
    checkpoint()
    print(tool,grid,len(result['summary']),'summaries',len(result['records']),'runs',len(result['failures']),'failures',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('tool',choices=['xesmf','xarray','odc_geo','xarray_regrid_linear','xarray_regrid_nearest','xarray_regrid_conservative']);p.add_argument('grid',choices=['rectilinear','roms','crs_2056','crs_3857']);a=p.parse_args();run(a.tool,a.grid)
