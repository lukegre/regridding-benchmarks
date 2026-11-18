"""Run fixed shared grid sizes serially; no per-package size tuning or concurrent timings."""
import os,sys,json,time,subprocess,platform
from pathlib import Path
ROOT=Path(__file__).parent;OUT=ROOT/'large_results';OUT.mkdir(exist_ok=True);(OUT/'logs').mkdir(exist_ok=True)
ENVROOT=Path(os.environ.get('BENCH_ENV_ROOT',ROOT))
CASES=[]
def add(pkg,grids,compiled=False):
 for grid in grids:CASES.append((pkg,grid,compiled))
add('scipy',['rectilinear','gaussian']);add('xarray',['rectilinear','gaussian']);add('xarray_axes',['rectilinear','gaussian'])
for p in ['xarray_regrid_linear','xarray_regrid_nearest','xarray_regrid_conservative']:add(p,['rectilinear','gaussian'])
for p in ['pyresample_nearest','pyresample_gauss']:add(p,['rectilinear','roms','satellite_swath','icosahedral','healpix','gaussian'])
for p in ['healpy','astropy_healpix']:add(p,['healpix'])
for p in ['rasterio','rioxarray','odc_geo','pyproj']:add(p,['crs_4326_to_2056','crs_4326_to_3857'])
for p in ['xesmf_bilinear','xesmf_nearest_s2d']:add(p,['rectilinear','roms','satellite_swath','gaussian'],True)
add('xesmf_conservative',['rectilinear','roms','gaussian'],True)
add('cdo_nearest',['rectilinear','roms','satellite_swath','icosahedral','healpix','gaussian'],True)
add('cdo_bilinear',['rectilinear','roms','satellite_swath','healpix','gaussian'],True)
add('cdo_conservative',['rectilinear','roms','satellite_swath','icosahedral','gaussian'],True)
add('xugrid',['roms_mesh']);add('earthkit_mir',['healpix','gaussian']);add('uxarray',['icosahedral']);add('esmpy',['icosahedral'],True);add('iris',['rectilinear'],True);add('tempest',['icosahedral'],True);add('nco',['icosahedral'],True)

def run(scales,repeats,only=None):
 env=os.environ.copy();env.update(BENCH_ENV_ROOT=str(ENVROOT),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',NUMBA_NUM_THREADS='1')
 config={'date_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'platform':platform.platform(),'cpu_quota':'2 vCPU','threads_per_worker':1,'serial':True,'scales':scales,'repeats':repeats,'timing_target':'Approximately 10 seconds for setup plus eager application; grid geometry and input values identical across packages within a grid/scale profile. No artificial repetition used to pad timings.','cases':CASES}
 
 prior=OUT/'configuration.json'
 if prior.exists() and all(n>=512 for n in scales):
  old=json.loads(prior.read_text());config['scales']=sorted(set(old.get('scales',[])+scales));config['invocations']=old.get('invocations',[])+[{'scales':scales,'only':only,'repeats':repeats}]
 prior.write_text(json.dumps(config,indent=2))
 for n in scales:
  for pkg,grid,compiled in CASES:
   if only and pkg not in only:continue
   tag=f'{pkg}__{grid}__{n}';out=OUT/f'{tag}.json'
   previous=[]
   if out.exists():
    old=json.loads(out.read_text())
    if old.get('status')=='completed' and len(old.get('runs',[]))==repeats:print('EXISTING',tag,flush=True);continue
    previous=old.get('runs',[]) if len(old.get('runs',[]))<repeats else []
   python=ENVROOT/('compiled' if compiled else '.venv')/'bin/python'
   print('START',tag,flush=True);t=time.monotonic()
   with (OUT/'logs'/f'{tag}.log').open('w') as log:
    try:p=subprocess.run([str(python),str(ROOT/'large_bench.py'),pkg,grid,str(n),str(repeats-len(previous)),str(out)],env=env,stdout=log,stderr=log,timeout=900)
    except subprocess.TimeoutExpired:p=None
   if not out.exists():out.write_text(json.dumps({'status':'timeout' if p is None else 'crashed','package':pkg,'grid':grid,'scale':n,'returncode':None if p is None else p.returncode,'worker_seconds':time.monotonic()-t},indent=2))
   result=json.loads(out.read_text())
   if previous and result.get('status')=='completed':
    result['runs']=previous+result['runs']
    for i,row in enumerate(result['runs']):row['repeat']=i
    result['resumed_repetitions']=len(previous);out.write_text(json.dumps(result,indent=2))
   runs=result.get('runs',[])
   print('DONE',tag,result['status'],[round(x['total_seconds'],3) for x in runs],result.get('error','')[:150],flush=True)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--scales',nargs='+',type=int,default=[512,1024]);p.add_argument('--repeats',type=int,default=3);p.add_argument('--only',nargs='*');a=p.parse_args();run(a.scales,a.repeats,a.only)
