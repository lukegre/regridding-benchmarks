(()=>{
 const payload=JSON.parse(document.getElementById('large-data').textContent),summaries=payload.summary;
 const grid=document.getElementById('large-grid'),scale=document.getElementById('large-scale');
 const names={rectilinear:'Rectilinear → rectilinear',roms:'ROMS-style curvilinear → rectilinear',satellite_swath:'Satellite swath → rectilinear',icosahedral:'Icosahedral triangles → lat/lon',healpix:'HEALPix → lat/lon',gaussian:'Full Gaussian → lat/lon',crs_4326_to_2056:'WGS84 → Swiss LV95 (EPSG:2056)',crs_4326_to_3857:'WGS84 → Web Mercator (EPSG:3857)',roms_mesh:'Local projected triangular meshes (Xugrid)',crs_4326_to_2056__coordinates:'Coordinates only: WGS84 → LV95',crs_4326_to_3857__coordinates:'Coordinates only: WGS84 → Web Mercator'};
 for(const k of Object.keys(names))if(summaries.some(r=>r.comparison_group===k))grid.add(new Option(names[k],k));
 grid.value=summaries.some(r=>r.grid==='rectilinear')?'rectilinear':grid.options[0]?.value;
 const display=p=>({nco:'NCO (TempestRemap weights)',tempest:'TempestRemap',esmpy:'ESMPy conservative',uxarray:'UXarray nearest',iris:'Iris conservative'}[p]||p);
 const fmt=v=>Number.isFinite(v)?v<.001?v.toExponential(2):v.toFixed(3):'—';
 function detail(r){const v={profile:r,repetitions:payload.records.filter(x=>x.package===r.package&&x.grid===r.grid&&x.scale===r.scale)};document.getElementById('large-detail-content').textContent=JSON.stringify(v,null,2);document.getElementById('large-detail').open=true;}
 function adjustScales(){const sizes=[...new Set(summaries.filter(r=>r.comparison_group===grid.value).map(r=>r.scale))].sort((a,b)=>a-b);const previous=Number(scale.value);scale.replaceChildren(...sizes.map(n=>new Option(n+' scale',String(n))));scale.value=String(sizes.includes(previous)?previous:sizes[sizes.length-1]);}
 function renderLarge(){
  document.getElementById('large-detail').open=false;document.getElementById('large-detail-content').textContent='Select a bar to inspect a profile.';
  const chosen=summaries.filter(r=>r.comparison_group===grid.value&&r.scale===Number(scale.value)).sort((a,b)=>a.package.localeCompare(b.package));
  const chart=document.getElementById('large-chart'),table=document.getElementById('large-table');chart.replaceChildren();table.replaceChildren();
  if(!chosen.length){document.getElementById('large-profile').textContent='No successful timing profiles at this size; see the failure records.';return;}
  const first=chosen[0],max=Math.max(...chosen.map(r=>r.total_seconds_mean));
  document.getElementById('large-profile').textContent=`${first.source_cells.toLocaleString()} source cells (${first.source_shape.join(' × ')}) → ${first.target_cells.toLocaleString()} target cells (${first.target_shape.join(' × ')}); ${chosen.length} adapters. Source, target and scalar-value hashes match within this profile.`;
  for(const r of chosen){const row=document.createElement('div');row.className='large-bar-row';const name=document.createElement('span');name.textContent=display(r.package)+(r.timing_mode==='fused'?' *':'');const track=document.createElement('div');
   const b=document.createElement('button');b.type='button';b.className='large-bar';b.style.width=(100*r.total_seconds_mean/max)+'%';b.setAttribute('aria-label',`${r.package}: setup ${fmt(r.setup_seconds_mean)} seconds, application ${fmt(r.apply_seconds_mean)} seconds, total ${fmt(r.total_seconds_mean)} seconds. Show repeat measurements.`);
   b.title=`${r.package}: setup ${fmt(r.setup_seconds_mean)} s; application ${fmt(r.apply_seconds_mean)} s; total ${fmt(r.total_seconds_mean)} s; ${r.repeats} repeats`;
   const setup=document.createElement('span');setup.className='large-setup';setup.style.width=(100*r.setup_seconds_mean/r.total_seconds_mean)+'%';const apply=document.createElement('span');apply.className='large-apply';apply.style.width=(100*r.apply_seconds_mean/r.total_seconds_mean)+'%';b.append(setup,apply);b.onclick=()=>detail(r);track.append(b);const time=document.createElement('span');time.className='large-time';time.textContent=fmt(r.total_seconds_mean)+' s';row.append(name,track,time);chart.append(row);
   const tr=document.createElement('tr');const accuracy=r.package==='pyproj'?'Round-trip '+(r.roundtrip_max_degrees||0).toExponential(2)+'°':'RMSE '+fmt(r.rmse);
   for(const [i,v] of [display(r.package)+(r.timing_mode==='fused'?' *':''),fmt(r.setup_seconds_mean),fmt(r.apply_seconds_mean),fmt(r.total_seconds_mean),fmt(r.total_seconds_min)+'–'+fmt(r.total_seconds_max),accuracy+'; '+(r.finite_fraction*100).toFixed(2)+'%'].entries()){const td=document.createElement('td');td.textContent=v;if(i>0&&i<5)td.className='num';tr.append(td);}table.append(tr);
  }
 }
 grid.onchange=()=>{adjustScales();renderLarge();};scale.onchange=renderLarge;adjustScales();renderLarge();
 const failures=payload.failures||[];document.getElementById('large-failures').textContent=failures.length?`${failures.length} TempestRemap/NCO profiles timed out after 300 seconds in overlap-mesh construction, before completed weight/application measurements. NCO uses the same TempestRemap setup, so these are not independent interpolation failures. Details are retained in the JSON and excluded from successful timings.`:'All recorded production profiles completed. * Geometry/weights and interpolation are fused in this interface; see per-profile notes.';
})();
