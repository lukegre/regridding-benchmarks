"""Render validated evidence as a static, dependency-free site."""

from collections import defaultdict
from html import escape
from statistics import median
import shutil

from .bundle import validate
from .io import read_json, write_json

LEGACY_FILES = (
    "index.html", "small-data.html", "tool-guide.html", "comparison.html",
    "results.csv", "results.json", "large-measurements.csv", "large-results.json",
    "chunked-results.json", "external-comparisons.json", "tool_contracts.json",
    "tool_recommendations.json", "tool-selection-skill.md", "xarray-regrid-report.md",
    "benchmark-source-and-results.tar.gz",
)


def page(title, body):
    return f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
body {{font: 1rem/1.5 system-ui, sans-serif; max-width: 76rem; margin: 2rem auto; padding: 0 1rem; color: #162527}}
a {{color: #075f6d; overflow-wrap: anywhere}}
table {{border-collapse: collapse; width: 100%; text-align: left}}
th, td {{padding: .6rem; border-bottom: 1px solid #c9dddd; vertical-align: top}}
th {{background: #eef5f3}}
.table {{overflow-x: auto}}
code {{overflow-wrap: anywhere}}
</style>
<main><h1>{escape(title)}</h1>{body}</main></html>
"""


def display(value):
    return escape(str(value))


def link(href, label):
    return f'<a href="{escape(href, quote=True)}">{display(label)}</a>'


def method_details(case):
    method = display(case["method"])
    protocol = case.get("protocol", "")
    if isinstance(protocol, str) and protocol.startswith("https://"):
        method += f"<br>{link(protocol, 'Upstream protocol')}"
    if case.get("deviations"):
        items = "".join(f"<li>{display(item)}</li>" for item in case["deviations"])
        method += f"<details><summary>Protocol adaptations</summary><ul>{items}</ul></details>"
    return method


def measurements(case, result):
    for phase, seconds in result["timings"].items():
        yield "", phase, seconds
    # The original chunked protocols keep all inner repeats inside a worker
    # sample. Report each layout and phase separately.
    metrics = result["metrics"]
    if case["family"] == "chunked":
        repeats = metrics.get("records", [])
    elif case["family"] == "storage":
        repeats = metrics.get("repeats", [])
    else:
        return
    for repeat in repeats:
        layout = " × ".join(map(str, repeat.get("layout", metrics.get("layout", []))))
        for column, phase in (("graph_seconds", "graph construction"), ("compute_seconds", "compute"),
                              ("compute_read_seconds", "compute with storage read"),
                              ("eager_application_seconds", "eager application")):
            seconds = repeat.get(column)
            if seconds is not None:
                yield layout, phase, seconds


def edition_page(manifest, rows):
    run_id = manifest["run_id"]
    timings = defaultdict(list)
    for case, _, result in rows:
        if manifest["publishable_profile"] and result["status"] == "ok":
            for layout, phase, seconds in measurements(case, result):
                timings[case["id"], layout, phase].append(seconds)
    summary = "".join(f"<tr><td>{display(case)}</td><td>{display(layout)}</td><td>{display(phase)}</td>"
                      f"<td>{median(values):.6g}</td><td>{len(values)}</td></tr>"
                      for (case, layout, phase), values in sorted(timings.items()))
    table = "".join(
        f"<tr><td>{display(case['id'])}</td><td>{method_details(case)}</td>"
        f"<td>{display(case.get('dataset') or case.get('fixture'))}</td>"
        f"<td>{display(value['status'])}</td><td>{display(value.get('reason', ''))}</td>"
        f"<td>{link(f'{run_id}/samples/{sample}.json', sample)} · "
        f"{link(f'{run_id}/logs/{sample}.log', 'log')}</td></tr>"
        for case, sample, value in rows
    )
    datasets = {record["dataset"]["id"]: record
                for record in manifest["inputs"].values() if "dataset" in record}
    items = []
    for identifier, record in sorted(datasets.items()):
        protocol = record["dataset"].get("protocol", "")
        upstream = (f" · {link(protocol, 'Upstream protocol')}"
                    if isinstance(protocol, str) and protocol.startswith("https://") else "")
        outcome = f"SHA-256 {record['sha256']}" if record["verified"] else record["reason"]
        items.append(f"<li>{display(identifier)}{upstream} · {display(outcome)}</li>")
    related = "".join(items)
    return page(f"Edition {run_id}", f"""
<p>{link('../index.html', 'All editions')} · {link(f'{run_id}/manifest.json', 'Run manifest')}
 · {link(f'{run_id}/checksums.json', 'Checksums')}</p>
<dl><dt>Series</dt><dd>{display(manifest['series'])}</dd>
<dt>Profile</dt><dd>{display(manifest['profile'])}</dd>
<dt>Revision</dt><dd>{display(manifest['source']['commit'] or 'Unknown')}</dd>
<dt>Image digest</dt><dd>{display(manifest['environment']['image_digest'] or 'Unknown')}</dd>
<dt>Completed</dt><dd>{display(manifest['finished_at'])}</dd></dl>
{f'<h2>Datasets and protocols</h2><ul>{related}</ul>' if related else ''}
<h2>Sample outcomes</h2>
<div class="table"><table><thead><tr><th>Case</th><th>Method</th><th>Input</th><th>Outcome</th>
<th>Reason</th><th>Evidence</th></tr></thead><tbody>{table}</tbody></table></div>
{f'<h2>Median phase times</h2><div class="table"><table><thead><tr><th>Case</th><th>Layout</th><th>Phase</th><th>Seconds</th><th>Repeats</th></tr></thead><tbody>{summary}</tbody></table></div>' if summary else ''}
""")


def copy_legacy(legacy, output):
    if not legacy or not (legacy / "index.html").is_file():
        return ""
    edition = output / "legacy"
    edition.mkdir(exist_ok=True)
    for name in LEGACY_FILES:
        source = legacy / name
        if source.is_file():
            shutil.copy2(source, edition / name)
            if name != "index.html":
                shutil.copy2(source, output / name)
    return f"<p>{link('legacy/index.html', 'Legacy benchmark reports and tool guide')}</p>"


def link_guidance(output, historical):
    index = read_json(historical / "index.json")
    evidence = {
        "source_revision": index["source_revision"],
        "manifest": "legacy/evidence/manifest.json",
        "case_index": "legacy/evidence/index.json",
    }
    for name in ("tool_contracts.json", "tool_recommendations.json"):
        path = output / name
        if not path.is_file():
            continue
        guidance = read_json(path)
        guidance["benchmark_evidence"] = evidence
        for rule in guidance.get("recommendations", []):
            files = [f"large_results/{package}__{rule['grid']}__{rule['scale']}.json"
                     for package in rule.get("packages", [])]
            rule["case_records"] = [f"legacy/evidence/{name}" for name in files
                                    if (historical / name).is_file()]
        write_json(path, guidance)
    path = output / "tool-guide.html"
    if path.is_file():
        note = (
            f"<section><h2>Benchmark evidence</h2><p>These recommendations cite the "
            f"{link(evidence['case_index'], 'historical case records')} and "
            f"{link(evidence['manifest'], 'edition manifest')}. Each record identifies its raw "
            "result and pointer within that result.</p></section>"
        )
        path.write_text(path.read_text().replace("<main>", f"<main>{note}", 1))
    path = output / "tool-selection-skill.md"
    if path.is_file():
        with path.open("a") as stream:
            stream.write("\n## Cite benchmark evidence\n\n"
                         "Cite the edition revision and exact case record when applying a measured "
                         "claim. The case index provides the original result path and JSON Pointer. "
                         "[Historical case index](legacy/evidence/index.json) · "
                         "[Edition manifest](legacy/evidence/manifest.json)\n")


def build(bundle, output, *, legacy=None, legacy_edition=None):
    manifest, rows = validate(bundle)
    target = output / "editions" / manifest["run_id"]
    if target.exists():
        if (target / "checksums.json").read_bytes() != (bundle / "checksums.json").read_bytes():
            raise ValueError(f"Edition {manifest['run_id']} already has different evidence")
        validate(target)
    else:
        shutil.copytree(bundle, target)
    target.parent.joinpath(target.name + ".html").write_text(edition_page(manifest, rows))
    history = []
    for candidate in sorted(target.parent.iterdir()):
        if candidate.is_dir() and candidate != target:
            prior, prior_rows = validate(candidate)
            if prior["run_id"] != candidate.name:
                raise ValueError(f"Invalid edition directory {candidate}")
            prior_page = candidate.parent / f"{candidate.name}.html"
            if not prior_page.is_file():
                prior_page.write_text(edition_page(prior, prior_rows))
            history.append(prior["run_id"])
    history_links = "".join(f"<li>{link(f'editions/{prior}.html', prior)}</li>" for prior in history)
    legacy_link = copy_legacy(legacy, output)
    if legacy_edition:
        from .legacy import validate_edition

        validate_edition(legacy_edition)
        historical = output / "legacy" / "evidence"
        if historical.exists():
            validate_edition(historical)
            if (historical / "manifest.json").read_bytes() != (legacy_edition / "manifest.json").read_bytes():
                raise ValueError("Historical evidence differs from the archived edition")
        else:
            shutil.copytree(legacy_edition, historical)
        link_guidance(output, historical)
        legacy_link += (
            f"<p>{link('legacy/evidence/index.json', 'Historical case evidence index')} · "
            f"{link('legacy/evidence/manifest.json', 'Historical revision and checksums')}</p>"
        )
    legacy_redirect = (
        "<script>if (location.hash) location.replace('legacy/index.html' + location.hash)</script>"
        if legacy else ""
    )
    (output / "index.html").write_text(page("Geospatial regridding benchmarks", f"""
<h2>Current edition</h2><p>{link(f'editions/{target.name}.html', target.name)}</p>
{f'<h2>Previous editions</h2><ul>{history_links}</ul>' if history_links else ''}
{legacy_link}
{legacy_redirect}
"""))
    (output / ".nojekyll").touch()
