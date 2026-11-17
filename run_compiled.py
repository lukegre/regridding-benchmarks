import os,subprocess,concurrent.futures
from pathlib import Path
r=Path(__file__).parent
env=os.environ.copy();env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',NUMBA_NUM_THREADS='1',MPLCONFIGDIR='/tmp/geobench-mpl',PATH=str(r/'compiled/bin')+':'+env['PATH'])
def run(p):
 with (r/'results'/f'{p}.log').open('w') as f:
  try:s=subprocess.run([str(r/'compiled/bin/python'),str(r/'suite.py'),p],env=env,stdout=f,stderr=f,timeout=240);return p,s.returncode
  except subprocess.TimeoutExpired:return p,'timeout'
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
 for x in ex.map(run,['xesmf_bilinear','xesmf_conservative','xesmf_nearest_s2d','cdo']):print(x,flush=True)
