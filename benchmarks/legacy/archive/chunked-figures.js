(() => {
'use strict';
const payload=JSON.parse(document.getElementById('chunked-data').textContent);
const rows=payload.summary || [];
const records=payload.records || [];
const controls={tool:document.getElementById('chunk-tool'),grid:document.getElementById('chunk-grid'),layout:document.getElementById('chunk-layout')};
const table=document.getElementById('chunk-table');
const layout=x=>Array.isArray(x)?'('+x.join(', ')+')':String(x??'—');
const fmt=x=>typeof x==='number'&&Number.isFinite(x)?(x!==0&&(Math.abs(x)<0.001||Math.abs(x)>=10000)?x.toExponential(3):x.toPrecision(4)):'—';
for(const [key,selector] of Object.entries(controls)){
 const values=[...new Set(rows.map(r=>key==='layout'?layout(r.layout):r[key]).filter(Boolean))].sort();
 values.forEach(value=>selector.add(new Option(value,value)));
}
function add(tr,text){const td=document.createElement('td');td.textContent=text;tr.append(td);return td;}
function render(){
 const filtered=rows.filter(r=>(!controls.tool.value||r.tool===controls.tool.value)&&(!controls.grid.value||r.grid===controls.grid.value)&&(!controls.layout.value||layout(r.layout)===controls.layout.value));
 table.replaceChildren();
 for(const r of filtered){
  const tr=document.createElement('tr');add(tr,`${r.tool} / ${r.grid}`);add(tr,layout(r.layout));
  for(const key of ['setup_seconds_shared','median_graph_seconds','median_compute_seconds','median_eager_application_seconds','graph_tasks'])add(tr,key==='median_graph_seconds'&&!r.output_lazy?'—':fmt(r[key]));
  const c=r.correctness||{};add(tr,`Max ${fmt(c.max_abs_error)}; seam ${fmt(c.seam_max_abs_error)}; mask mismatches ${fmt(c.finite_mask_mismatches)}`);
  const td=add(tr,''),details=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');summary.textContent='Chunks, scheduler and repeats';
  const repeats=records.filter(x=>x.tool===r.tool&&x.grid===r.grid&&JSON.stringify(x.layout)===JSON.stringify(r.layout));
  pre.textContent=JSON.stringify({output_lazy:r.output_lazy,input_chunks:r.input_chunks,output_chunks:r.output_chunks,rechunk_layers:r.rechunk_layers,reference_seconds:r.reference_seconds,reference_was_lazy:r.reference_was_lazy,setup_note:r.setup_note,weights_nnz:r.weights_nnz,fixture:r.fixture,repetitions:repeats.map(x=>({repeat:x.repeat,scheduler:x.scheduler,graph_seconds:x.graph_seconds,compute_seconds:x.compute_seconds,eager_application_seconds:x.eager_application_seconds}))},null,2);
  details.append(summary,pre);td.append(details);table.append(tr);
 }
 if(!filtered.length){const tr=document.createElement('tr'),td=add(tr,'No profiles match these filters.');td.colSpan=9;td.className='empty';table.append(tr);}
 document.getElementById('chunk-count').textContent=`${filtered.length} of ${rows.length} profiles`;
}
Object.values(controls).forEach(el=>el.addEventListener('change',render));
const mismatches=rows.filter(r=>(r.correctness?.finite_mask_mismatches||0)>0);
document.getElementById('chunk-accuracy-note').textContent=mismatches.length ? 'Accuracy caveat: '+mismatches.map(r=>`${r.tool} / ${r.grid} at ${layout(r.layout)} has ${r.correctness.finite_mask_mismatches} finite-mask mismatches against its reference`).join('; ')+'. Summary accuracy reports the worst recorded repeat.' : 'Summary accuracy reports the worst recorded repeat.';
function paragraph(parent,text){const p=document.createElement('p');p.textContent=text;parent.append(p);}
const storage=payload.storage, storageEl=document.getElementById('chunk-storage');
if(storage){
 const memory=rows.find(r=>r.tool===storage.tool&&r.grid===storage.grid&&JSON.stringify(r.layout)===JSON.stringify(storage.layout));
 paragraph(storageEl,`${storage.tool} / ${storage.grid}, NetCDF4 storage chunks ${layout(storage.storage_chunks)}, input layout ${layout(storage.layout)}: median graph ${fmt(storage.median_graph_seconds)} s; median compute including reads ${fmt(storage.median_compute_read_seconds)} s over ${storage.repeats.length} repeats. Scheduler: ${storage.scheduler}.`);
 if(memory)paragraph(storageEl,`The matching in-memory profile has median graph ${fmt(memory.median_graph_seconds)} s and compute ${fmt(memory.median_compute_seconds)} s. This is a separate control with the same fixture; timing differences include storage and execution effects.`);
 paragraph(storageEl,storage.note+' File creation and opening are excluded, and the filesystem cache was warm; these are not cold-disk timings.');
 const d=document.createElement('details'),summ=document.createElement('summary'),pre=document.createElement('pre');summ.textContent='Storage fixture, chunks and repeat measurements';pre.textContent=JSON.stringify(storage,null,2);d.append(summ,pre);storageEl.append(d);
}else paragraph(storageEl,'No storage control was recorded.');
const diagnostic=payload.diagnostic_default, diagnosticEl=document.getElementById('chunk-diagnostic');
if(diagnostic){
 paragraph(diagnosticEl,`${diagnostic.tool} / ${diagnostic.grid}, 4 × 1024 × 1024 input, layout ${layout(diagnostic.layout)}, default output chunks: graph construction ${fmt(diagnostic.graph_seconds)} s and ${diagnostic.graph_tasks.toLocaleString()} tasks. This is graph construction only; no computation completed.`);
 paragraph(diagnosticEl,diagnostic.pilot);
 const d=document.createElement('details'),summ=document.createElement('summary'),pre=document.createElement('pre');summ.textContent='Diagnostic chunks and pilot details';pre.textContent=JSON.stringify(diagnostic,null,2);d.append(summ,pre);diagnosticEl.append(d);
}else paragraph(diagnosticEl,'No graph-only diagnostic was recorded.');
const failures=payload.failures||[];const failureContent=document.getElementById('chunk-failure-content');
if(failures.length){const pre=document.createElement('pre');pre.textContent=JSON.stringify(failures,null,2);failureContent.append(pre);}else failureContent.textContent='No failures were recorded.';
render();
})();
