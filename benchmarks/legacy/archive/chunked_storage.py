"""Warm-cache NetCDF4 companion to the in-memory xarray rectilinear experiment."""
from chunked_bench import *
import tempfile

def main():
    lo,la,v,tx,ty,_,info=fixtures('rectilinear',N);cube=make_cube(v)
    da=xr.DataArray(cube,name='field',dims=('time','lat','lon'),coords={'lat':la[:,0],'lon':lo[0]})
    t=time.perf_counter();ref=da.interp(lat=ty[:,0],lon=tx[0]).values;ref_s=time.perf_counter()-t
    fixture={'source_geometry_sha256':info['source_geometry_sha256'],'destination_geometry_sha256':info['destination_geometry_sha256'],'values_sha256':digest(cube),'shape':list(cube.shape),'missing_count':int(np.isnan(cube).sum())}
    rows=[]
    with tempfile.TemporaryDirectory(prefix='chunked-bench-') as tmp:
        path=Path(tmp)/'input.nc'
        da.to_dataset().to_netcdf(path,engine='netcdf4',encoding={'field':{'chunksizes':(1,128,128)}})
        # Populate OS cache; actual compute timings below include reading from file.
        with xr.open_dataset(path,engine='netcdf4') as warm: warm['field'].load()
        for rep in range(REPEATS):
            with xr.open_dataset(path,engine='netcdf4',chunks={'time':1,'lat':128,'lon':128}) as ds:
                data=ds['field'];storage_chunks=list(data.encoding['chunksizes'])
                t=time.perf_counter();out=data.interp(lat=ty[:,0],lon=tx[0]);graph_s=time.perf_counter()-t
                graph=out.data.__dask_graph__();tasks=len(graph);layers=[str(k) for k in graph.layers if 'rechunk' in str(k).lower()]
                t=time.perf_counter();value=out.compute(scheduler='synchronous').values;compute_s=time.perf_counter()-t
                rows.append({'repeat':rep+1,'graph_seconds':graph_s,'compute_read_seconds':compute_s,'input_chunks':chunks(data),'output_chunks':chunks(out),'graph_tasks':tasks,'rechunk_layers':layers,'correctness':compare(value,ref)})
    result={'tool':'xarray','grid':'rectilinear','group':'netcdf4_warm_cache','fixture':fixture,'storage_chunks':storage_chunks,'layout':[1,128,128],'scheduler':'synchronous','reference_seconds':ref_s,'repeats':rows,'median_graph_seconds':float(np.median([r['graph_seconds'] for r in rows])),'median_compute_read_seconds':float(np.median([r['compute_read_seconds'] for r in rows])),'note':'File creation and opening excluded; full compute includes warm-cache NetCDF reads. OS cache was not cleared; not a cold-disk benchmark.'}
    (OUT/'storage_netcdf4.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print('storage',len(rows),'runs',flush=True)
if __name__=='__main__':main()
