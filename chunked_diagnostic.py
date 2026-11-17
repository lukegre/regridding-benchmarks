"""Observe xESMF's default output graph without executing that graph."""
from chunked_bench import *
import xesmf as xe
N=1024
lo,la,v,tx,ty,_,_=fixtures('rectilinear',N)
src=xr.Dataset({'lon':(('y','x'),lo),'lat':(('y','x'),la)})
dst=xr.Dataset({'lon':(('y','x'),tx),'lat':(('y','x'),ty)})
t=time.perf_counter();op=xe.Regridder(src,dst,'bilinear',unmapped_to_nan=True);setup=time.perf_counter()-t
arr=xr.DataArray(make_cube(v),dims=('time','y','x')).chunk({'time':1,'y':128,'x':128})
t=time.perf_counter();out=op(arr);graph_seconds=time.perf_counter()-t
graph=out.data.__dask_graph__()
r={'tool':'xesmf','grid':'rectilinear','layout':[1,128,128],'output_chunks_argument':'default','setup_seconds':setup,'graph_seconds':graph_seconds,'input_chunks':chunks(arr),'output_chunks':chunks(out),'graph_tasks':len(graph),'rechunk_layers':[str(k) for k in graph.layers if 'rechunk' in str(k).lower()],'computed':False,'interrupted_pilots':[{'output_chunks':'default','approx_elapsed_seconds':150,'status':'interrupted; no completed result'},{'output_chunks':[1024,1024],'approx_elapsed_seconds':120,'status':'interrupted; no completed result'}],'pilot':'Separate earlier default-output compute pilot interrupted after approximately 150 seconds, without a result; a second 1024 pilot with full-horizontal output was also stopped after approximately 120 seconds. Neither is a completed execution measurement.'}
(OUT/'diagnostic_default.json').write_text(json.dumps(r,indent=2)+'\n');print('diagnostic graph only',r['graph_tasks'],flush=True)
