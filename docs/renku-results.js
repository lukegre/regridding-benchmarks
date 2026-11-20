"use strict";
// Aggregation helpers (pure, tested under node) ------------------------------
function median(xs) {
  const s = xs.slice().sort((a, b) => a - b), n = s.length;
  if (!n) return null;
  return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2;
}
function countBy(items, key) {
  const out = {};
  for (const it of items) { const k = key(it); out[k] = (out[k] || 0) + 1; }
  return out;
}
function filterSamples(samples, f) {
  return samples.filter(s =>
    (!f.family || s.family === f.family) && (!f.method || s.method === f.method) && (!f.status || s.status === f.status));
}
// One row per case: status counts, plus median/min/max of `phase` across repeats.
function aggregateCases(samples, phase) {
  const by = {};
  for (const s of samples) (by[s.case_id] = by[s.case_id] || []).push(s);
  return Object.keys(by).sort().map(id => {
    const g = by[id];
    const t = g.map(s => (s.timings || {})[phase]).filter(v => typeof v === "number");
    return { case_id: id, family: g[0].family, method: g[0].method, quantity: g[0].quantity,
             n: g.length, statuses: countBy(g, s => s.status),
             median: median(t), min: t.length ? Math.min(...t) : null, max: t.length ? Math.max(...t) : null };
  });
}
function unavailableCases(samples) {
  const by = {};
  for (const s of samples) if (s.status === "unavailable") {
    const r = by[s.case_id] = by[s.case_id] || { case_id: s.case_id, family: s.family, n: 0, reasons: new Set() };
    r.n++; if (s.reason) r.reasons.add(s.reason);
  }
  return Object.values(by).sort((a, b) => a.case_id.localeCompare(b.case_id));
}
function phasesOf(samples) {
  const p = new Set();
  for (const s of samples) for (const k of Object.keys(s.timings || {})) p.add(k);
  return [...p].sort();
}
if (typeof module !== "undefined") module.exports = { median, countBy, filterSamples, aggregateCases, unavailableCases, phasesOf };

// Page (browser only) ---------------------------------------------------------
if (typeof document !== "undefined") (function () {
  const $ = id => document.getElementById(id);
  const runs = new Map(); // run_id -> run document
  let entries = [];

  function el(tag, text, cls) { const e = document.createElement(tag); if (text != null) e.textContent = text; if (cls) e.className = cls; return e; }
  function banner(text) { $("msg").appendChild(el("p", text, "banner")); }
  function fmt(v) { return v == null ? "–" : v >= 100 ? v.toFixed(1) : v >= 1 ? v.toFixed(2) : v.toPrecision(3); }
  function badges(counts) {
    const c = el("td");
    for (const k of Object.keys(counts).sort()) c.appendChild(el("span", k + " " + counts[k], "status s-" + k));
    return c;
  }
  function fill(table, head, rows, empty) {
    table.replaceChildren();
    if (!rows.length) { const tr = el("tr"); const td = el("td", empty, "empty"); td.colSpan = head.length; tr.appendChild(td); table.appendChild(tr); return; }
    const hr = el("tr"); head.forEach(h => hr.appendChild(el("th", h))); table.appendChild(el("thead")).appendChild(hr);
    const tb = el("tbody");
    for (const cells of rows) {
      const tr = el("tr");
      for (const c of cells) tr.appendChild(c instanceof Node ? c : el("td", c.t != null ? c.t : c, c.num ? "num" : null));
      tb.appendChild(tr);
    }
    table.appendChild(tb);
  }
  function setOptions(sel, values, any, keep) {
    const old = keep ? sel.value : "";
    sel.replaceChildren();
    if (any != null) sel.appendChild(new Option(any, ""));
    for (const v of values) sel.appendChild(new Option(v.label || v, v.value != null ? v.value : v));
    if ([...sel.options].some(o => o.value === old)) sel.value = old;
  }
  const uniq = (xs) => [...new Set(xs.filter(Boolean))].sort();

  function renderRuns() {
    const rows = entries.map(e => {
      const counts = e.status_counts || (runs.get(e.run_id) ? countBy(runs.get(e.run_id).samples, s => s.status) : {});
      return [e.run_id, e.profile || "", e.series || "", (e.started_at || "").slice(0, 16).replace("T", " "), { t: e.n_samples != null ? e.n_samples : "", num: true }, badges(counts)];
    });
    fill($("runs"), ["Run", "Profile", "Series", "Started (UTC)", "Samples", "Status counts"], rows, "No runs.");
  }
  function runChoices() {
    const p = $("f-profile").value;
    return entries.filter(e => runs.has(e.run_id) && (!p || e.profile === p)).map(e => ({ value: e.run_id, label: e.run_id + " (" + (e.profile || "?") + ")" }));
  }
  function render() {
    const run = runs.get($("f-run").value);
    if (!run) { for (const id of ["families", "cases", "unavail"]) fill($(id), [""], [], "No run selected."); $("run-info").textContent = ""; return; }
    const cmp = runs.get($("f-cmp").value);
    const f = { family: $("f-family").value, method: $("f-method").value, status: $("f-status").value };
    const phase = $("f-phase").value;
    const eng = Object.entries(run.engines || {}).map(([k, v]) => k + " " + v).join(", ");
    $("run-info").textContent = "Run " + run.run_id + ": profile " + run.profile + ", series " + run.series + ", " + run.repeats + " repeats, commit " + String(run.source_commit || "?").slice(0, 10) + (eng ? ". Engines: " + eng : "") + ".";

    const fams = {};
    for (const s of run.samples) (fams[s.family || "?"] = fams[s.family || "?"] || []).push(s);
    fill($("families"), ["Family", "Samples", "Status counts"],
      Object.keys(fams).sort().map(k => [k, { t: fams[k].length, num: true }, badges(countBy(fams[k], s => s.status))]), "No samples.");

    const rows = aggregateCases(filterSamples(run.samples, f), phase);
    const other = cmp ? Object.fromEntries(aggregateCases(cmp.samples, phase).map(r => [r.case_id, r])) : null;
    const head = ["Case", "Family", "Method", "Status", "Median (s)", "Min–max (s)"].concat(other ? ["Compare median (s)", "Ratio"] : []);
    fill($("cases"), head, rows.map(r => {
      const base = [r.case_id, r.family || "", r.method || "", badges(r.statuses), { t: fmt(r.median), num: true }, { t: r.min == null ? "–" : fmt(r.min) + "–" + fmt(r.max), num: true }];
      if (!other) return base;
      const o = other[r.case_id];
      return base.concat([{ t: o ? fmt(o.median) : "–", num: true }, { t: o && o.median && r.median != null ? (r.median / o.median).toFixed(2) : "–", num: true }]);
    }), "No cases match the filters.");

    fill($("unavail"), ["Case", "Family", "Samples", "Reason"],
      unavailableCases(run.samples).map(u => [u.case_id, u.family || "", { t: u.n, num: true }, [...u.reasons].join("; ") || "–"]), "No unavailable cases in this run.");
  }
  function refreshRunSelects() {
    const ch = runChoices();
    setOptions($("f-run"), ch, null, true);
    setOptions($("f-cmp"), ch, "None", true);
    refreshFilters();
  }
  function refreshFilters() {
    const run = runs.get($("f-run").value), ss = run ? run.samples : [];
    setOptions($("f-family"), uniq(ss.map(s => s.family)), "All", true);
    setOptions($("f-method"), uniq(ss.map(s => s.method)), "All", true);
    setOptions($("f-status"), uniq(ss.map(s => s.status)), "All", true);
    const ph = phasesOf(ss);
    setOptions($("f-phase"), ph, null, true);
    if (!$("f-phase").value && ph.includes("apply")) $("f-phase").value = "apply";
    render();
  }

  async function load() {
    let index;
    try {
      const r = await fetch("data/index.json", { cache: "no-cache" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      index = await r.json();
    } catch (e) { banner("Could not load data/index.json (" + e.message + "). No results can be shown."); return; }
    entries = Array.isArray(index.runs) ? index.runs : [];
    if (!entries.length) { banner("No runs have been recorded yet. Results appear here once a Renku job has written data/index.json."); return; }
    const res = await Promise.allSettled(entries.map(async e => {
      const r = await fetch("data/" + e.file, { cache: "no-cache" });
      if (!r.ok) throw new Error(e.run_id + ": HTTP " + r.status);
      const d = await r.json();
      if (!d || !Array.isArray(d.samples)) throw new Error(e.run_id + ": malformed run file");
      runs.set(e.run_id, d);
    }));
    res.filter(x => x.status === "rejected").forEach(x => banner("Could not load run file: " + x.reason.message));
    $("app").hidden = false;
    $("run-info").textContent = "";
    renderRuns();
    setOptions($("f-profile"), uniq(entries.map(e => e.profile)), "All", false);
    refreshRunSelects();
    if (index.updated_at) $("run-info").textContent = "Index updated " + index.updated_at + ".";
    render();
  }

  $("f-profile").addEventListener("change", refreshRunSelects);
  $("f-run").addEventListener("change", refreshFilters);
  for (const id of ["f-cmp", "f-family", "f-method", "f-status", "f-phase"]) $(id).addEventListener("change", render);
  load();
})();
