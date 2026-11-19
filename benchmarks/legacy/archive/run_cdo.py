import os,subprocess,concurrent.futures
from pathlib import Path
r=Path(__file__).parent
env=os.environ.copy();env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
def run(p):
 with (r/'results'/f'{p}.log').open('w') as f:
  return p,subprocess.run([str(r/'compiled/bin/python'),str(r/'suite.py'),p],env=env,stdout=f,stderr=f,timeout=240).returncode
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
 for x in ex.map(run,['cdo','cdo_bilinear','cdo_conservative']):print(x,flush=True)
