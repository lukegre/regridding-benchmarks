"""Small numerical controls for xarray-regrid; not controlled performance rankings."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS']:os.environ[name]='1'
import json,time,traceback
from pathlib import Path
from importlib.metadata import version
import numpy as np
import xarray as xr
import xarray_regrid
from suite import field
ROOT=Path(__file__).parent
rows=[]
def record(package,case,func):
 start=time.perf_counter();row=dict(package=package,grid='rectilinear',case=case,engine_version=version('xarray-regrid'))
 try:row.update(func(),status='completed')
 except Exception as exc:row.update(status='error',error=repr(exc),traceback=traceback.format_exc())
 row['seconds']=time.perf_counter()-start;rows.append(row)
def conservation():
 lon=np.arange(-177.5,180,5);lat=np.arange(-87.5,90,5)
 x,y=np.meshgrid(lon,lat);a=xr.DataArray(field(x,y),dims=('lat','lon'),coords={'lat':lat,'lon':lon})
 target=xr.Dataset(coords={'lat':np.arange(-85.,90,10),'lon':np.arange(-175.,180,10)})
 out=a.regrid.conservative(target,latitude_coord='lat',skipna=False)
 def areas(lo,la,step):return np.outer(np.diff(np.sin(np.deg2rad(np.r_[la-step/2,la[-1]+step/2]))),np.full(len(lo),np.deg2rad(step)))
 before=float((a.values*areas(lon,lat,5)).sum());after=float((out.values*areas(target.lon.values,target.lat.values,10)).sum())
 error=abs(after-before)/abs(before)
 return dict(source_shape=list(a.shape),target_shape=list(out.shape),finite_fraction=float(np.isfinite(out).mean()),relative_integral_error=error,source_integral=before,target_integral=after,flags=[] if error<1e-12 else ['integral_error'],note='Closed global meridian/parallel cells, sphere radius one, complete coverage. Values are treated as cell means; this validates this geometry, not ESMF great-circle equivalence.')
def mode(named=True):
 a=xr.DataArray(np.tile([[1,1],[1,0]],(2,2)),dims=('lat','lon'),coords={'lat':np.arange(4)+.5,'lon':np.arange(4)+.5},name='classes' if named else None)
 dst=xr.Dataset(coords={'lat':[1.,3.],'lon':[1.,3.]})
 out=a.regrid.most_common(dst,values=np.array([0,1]),fill_value=-1)
 return dict(source_shape=[4,4],target_shape=[2,2],output=out.values.tolist(),finite_fraction=1.,max_error=float(np.max(abs(out.values-1))),flags=[] if np.all(out==1) else ['mode_error'],note='Count-based mode on equally spaced 2×2 source blocks with no ties. Does not test area-weighted mode; version 0.4.2 documents nondeterministic ties.')
def large_ids(compact):
 labels=np.array([2**53+1,2**53+3],dtype=np.int64)
 values=np.tile(np.arange(2) if compact else labels,(2,1));a=xr.DataArray(values,dims=('lat','lon'),coords={'lat':[.5,1.5],'lon':[.5,1.5]})
 dst=xr.Dataset(coords={'lat':[.6,1.4],'lon':[.6,1.4]});out=a.regrid.nearest(dst).values
 restored=labels[out.astype(int)] if compact else out
 expected=np.tile(labels,(2,1));mismatch=sum(int(x)!=int(y) for x,y in zip(restored.flat,expected.flat))
 return dict(input_dtype=str(values.dtype),output_dtype=str(out.dtype),input_ids=labels.tolist(),decoded_ids=[[int(x) for x in row] for row in restored],integer_id_mismatches=mismatch,flags=[] if not mismatch else ['integer_precision_loss'],note='Compact-code output is decoded through the original int64 lookup.' if compact else 'Probe native nearest preservation of IDs above 2^53; a returned output is not a correctness verdict.')
record('xarray_regrid_conservative','closed_global_integral',conservation)
record('xarray_regrid_most_common','categorical_coarsening_unnamed_input',lambda:mode(False))
record('xarray_regrid_most_common','categorical_coarsening_no_ties',mode)
record('xarray_regrid_nearest','large_integer_ids_native',lambda:large_ids(False))
record('xarray_regrid_nearest','large_integer_ids_compact_codes',lambda:large_ids(True))
(ROOT/'results/xarray_regrid_controls.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
for row in rows:print(row['case'],row['status'],row.get('relative_integral_error'),row.get('integer_id_mismatches'),row.get('flags'),row.get('error'))
