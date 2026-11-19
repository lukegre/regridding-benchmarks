(()=>{
 const grids=['rectilinear','roms','satellite_swath','icosahedral','healpix','gaussian'];
 const labels={rectilinear:'Rect.',roms:'ROMS',satellite_swath:'Swath',icosahedral:'Icos.',healpix:'HEALPix',gaussian:'Gauss.'};
 const baseline=data.filter(r=>r.scenario);
 const methods=[...new Set(baseline.map(r=>r.package))].sort();
 const scenario=document.getElementById('figure-scenario');
 const readout=document.getElementById('figure-detail');
 const fmt=v=>typeof v==='number'&&Number.isFinite(v)?(v!==0&&(Math.abs(v)<.001||Math.abs(v)>10000)?v.toExponential(2):v.toPrecision(3)):'—';
 function inspect(row,select){
  const coverage=typeof row.finite_fraction==='number'?(100*row.finite_fraction).toFixed(1)+'%':'—';
  readout.textContent=`${row.package} · ${row.grid} · ${row.scenario} · ${row.status==='completed'?'Output returned':row.status==='error'?'Error':'Not exercised'} · RMSE ${fmt(row.rmse)} · finite ${coverage} · wall time ${fmt(row.seconds*1000)} ms`+(row.error?' · '+row.error:'')+(row.warnings?.length?' · '+row.warnings.join('; '):'');
  if(select){els.pkg.value=row.package;els.grid.value=row.grid;els.status.value='';els.search.value=row.scenario;render(true);document.querySelectorAll('.heat-selected').forEach(e=>e.classList.remove('heat-selected'));document.querySelectorAll('button[data-probe]').forEach(e=>{if(e.dataset.probe===`${row.package}|${row.grid}|${row.scenario}`)e.classList.add('heat-selected');});}
 }
 function draw(metric,id){
  const table=document.createElement('table');table.className='heat-table';table.setAttribute('aria-label',metric==='coverage'?'Finite output coverage heatmap':'Analytic-field RMSE heatmap');
  const head=table.createTHead().insertRow();head.append(document.createElement('th'));
  grids.forEach(g=>{const th=document.createElement('th');th.scope='col';th.textContent=labels[g];th.title=g;head.append(th);});
  const body=table.createTBody();
  methods.forEach(method=>{const tr=body.insertRow(),th=document.createElement('th');th.scope='row';th.textContent=method;tr.append(th);
   grids.forEach(grid=>{const td=tr.insertCell(),row=baseline.find(r=>r.package===method&&r.grid===grid&&r.scenario===scenario.value);if(!row){td.textContent='—';return;}
    const b=document.createElement('button');b.type='button';b.dataset.probe=`${method}|${grid}|${scenario.value}`;
    let label;
    if(row.status!=='completed'){label=row.status==='error'?'ERR':'—';b.className='heat-cell unavailable';}
    else{const raw=metric==='coverage'?row.finite_fraction:row.rmse;const t=metric==='coverage'?raw:Math.max(0,Math.min(1,(Math.log10(Math.max(raw||0,1e-4))+4)/3));b.className='heat-cell';b.style.setProperty('--heat-opacity',String(.08+.72*(Number.isFinite(t)?t:0)));label=metric==='coverage'?(100*raw).toFixed(0)+'%':fmt(raw);}
    b.textContent=label;b.setAttribute('aria-label',`${method}, ${grid}, ${scenario.value}, ${metric}: ${label}, ${row.status}`);b.title=`${method} / ${grid}: ${metric==='coverage'?(100*(row.finite_fraction||0)).toFixed(3)+'%':fmt(row.rmse)}; ${row.status}. Click to filter recorded evidence.`;
    b.addEventListener('mouseenter',()=>inspect(row,false));b.addEventListener('focus',()=>inspect(row,false));b.addEventListener('click',()=>inspect(row,true));td.append(b);
   });
  });document.getElementById(id).replaceChildren(table);
 }
 function figures(){draw('coverage','coverage-figure');draw('rmse','rmse-figure');}
 scenario.addEventListener('change',figures);figures();
 const timingGrid=document.getElementById('timing-grid');
 function timings(){const tbody=document.getElementById('timing-rows');tbody.replaceChildren();baseline.filter(r=>r.grid===timingGrid.value&&r.scenario==='smooth'&&r.status==='completed').sort((a,b)=>a.package.localeCompare(b.package)).forEach(r=>{const tr=document.createElement('tr');[r.package,(r.seconds*1000).toFixed(2),typeof r.build_seconds==='number'?(r.build_seconds*1000).toFixed(2):'—',(100*r.finite_fraction).toFixed(1)+'%'].forEach((v,i)=>{const td=document.createElement('td');td.textContent=v;if(i)td.className='num';tr.append(td);});tbody.append(tr);});}
 timingGrid.addEventListener('change',timings);timings();
 const commands=JSON.parse(document.getElementById('native-timings').textContent);
 const group=new Map();commands.forEach(r=>{const name=r.command[0];if(!group.has(name))group.set(name,[]);group.get(name).push(r.seconds*1000);});
 for(const [name,values] of group){const tr=document.createElement('tr');const label=document.createElement('td');label.textContent=name;const value=document.createElement('td');value.className='num';value.textContent=values.length===1?values[0].toFixed(2)+' ms':Math.min(...values).toFixed(2)+'–'+Math.max(...values).toFixed(2)+' ms ('+values.length+' applications)';tr.append(label,value);document.getElementById('native-timing-rows').append(tr);}
})();
