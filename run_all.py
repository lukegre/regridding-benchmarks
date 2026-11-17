import os,subprocess,concurrent.futures,json,time
from pathlib import Path
root=Path(__file__).parent
packages=['scipy','xarray','pyresample_nearest','pyresample_gauss','healpy','astropy_healpix','rasterio','rioxarray','odc_geo','earthkit_mir']
def run(p):
 env=os.environ.copy();env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',NUMBA_NUM_THREADS='1',NUMBA_CACHE_DIR='/tmp/geobench-numba',MPLCONFIGDIR='/tmp/geobench-mpl')
 with (root/'results'/f'{p}.log').open('w') as f:
  try:r=subprocess.run([str(root/'.venv/bin/python'),str(root/'suite.py'),p],stdout=f,stderr=f,env=env,timeout=240);return p,r.returncode
  except subprocess.TimeoutExpired:return p,'timeout'
(root/'results').mkdir(exist_ok=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
 for r in ex.map(run,packages):print(r,flush=True)
