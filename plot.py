import os
os.environ['MPLCONFIGDIR']='/tmp/geobench-mpl'
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from suite import ROOT
r=[x for x in json.load(open(ROOT/'all_results.json')) if x.get('scenario')=='smooth']
packages=sorted({x['package'] for x in r});grids=['rectilinear','roms','satellite_swath','icosahedral','healpix','gaussian']
a=np.full((len(packages),len(grids)),np.nan);b=a.copy();texts={}
for x in r:
 i,j=packages.index(x['package']),grids.index(x['grid'])
 if x['status']=='completed':a[i,j]=x['finite_fraction']*100;b[i,j]=np.log10(max(x['rmse'],1e-16))
 else:texts[i,j]='ERR' if x['status']=='error' else '—'
fig,axes=plt.subplots(1,2,figsize=(14,9),layout='constrained')
for ax,values,title,cmap,vmin,vmax in [(axes[0],a,'Finite output coverage (%)','viridis',0,100),(axes[1],b,'log₁₀ RMSE (clipped at 0.1 for display)','magma_r',-4,-1)]:
 im=ax.imshow(values,cmap=cmap,vmin=vmin,vmax=vmax,aspect='auto')
 ax.set_xticks(range(len(grids)),grids,rotation=35,ha='right');ax.set_yticks(range(len(packages)),packages)
 for (i,j),txt in texts.items():ax.text(j,i,txt,ha='center',va='center',fontsize=8,color='#777777')
 fig.colorbar(im,ax=ax,shrink=.7)
fig.suptitle('Synthetic grid probes: raw smooth-field workflows\nDifferent kernels, targets and longitude conventions; this is not a ranking',fontsize=14)
fig.savefig(ROOT/'overview.png',dpi=160)
