"""Summarise a run bundle as compact JSON for the results web page.

    python -m regridding_benchmarks.summary <bundle> <data-dir>

writes <data-dir>/runs/<run-id>.json and adds the run to <data-dir>/index.json.
"""

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = 1
ENGINE_PACKAGES = ("numpy", "scipy", "xarray", "dask", "xesmf", "esmpy", "xarray-regrid",
                   "pyresample", "pyinterp", "healpy", "xdggs")
MAX_STRING = 80


def _read(path):
    return json.loads(Path(path).read_text())


def _norm(name):
    return name.lower().replace("_", "-")


def scalar_metrics(metrics):
    kept = {}
    for key, value in (metrics or {}).items():
        if isinstance(value, (bool, int, float)) or (isinstance(value, str) and len(value) <= MAX_STRING):
            kept[key] = value
    return kept


def engines(environment):
    found = {}
    for name, info in (environment.get("executables") or {}).items():
        if info.get("version"):
            found[name] = info["version"]
    wanted = set(ENGINE_PACKAGES)
    for interp in (environment.get("interpreters") or {}).values():
        for name, version in (interp.get("packages") or {}).items():
            if _norm(name) in wanted:
                found.setdefault(_norm(name), version)
    return found


def summarize_bundle(bundle):
    """Return the runs/<run-id>.json structure for a bundle directory."""
    bundle = Path(bundle)
    manifest = _read(bundle / "manifest.json")
    cases = {case["id"]: case for case in manifest["cases"]}
    samples = []
    for path in sorted((bundle / "samples").glob("*.json")):
        sample = _read(path)
        case = cases.get(sample["case_id"], {})
        result = sample["result"]
        resources = result.get("resources") or {}
        samples.append({
            "case_id": sample["case_id"],
            "family": case.get("family"),
            "method": case.get("method"),
            "quantity": case.get("quantity"),
            "repeat": sample["repeat"],
            "status": result["status"],
            "expected": result["status"] in case.get("expected", []),
            "reason": result.get("reason"),
            "timings": result.get("timings") or {},
            "metrics": scalar_metrics(result.get("metrics")),
            "resources": {key: value for key, value in resources.items()
                          if isinstance(value, (int, float))},
        })
    return {
        "schema": SCHEMA,
        "run_id": manifest["run_id"],
        "profile": manifest["profile"],
        "series": manifest.get("series"),
        "started_at": manifest.get("started_at"),
        "finished_at": manifest.get("finished_at"),
        "repeats": manifest.get("repeats"),
        "publishable": False,
        "source_commit": (manifest.get("source") or {}).get("commit"),
        "engines": engines(manifest.get("environment") or {}),
        "samples": samples,
    }


def update_index(index_path, summary):
    """Add or replace the entry for summary's run in index.json, newest first."""
    index_path = Path(index_path)
    index = _read(index_path) if index_path.exists() else {"runs": []}
    entry = {
        "run_id": summary["run_id"],
        "profile": summary["profile"],
        "series": summary["series"],
        "started_at": summary["started_at"],
        "n_samples": len(summary["samples"]),
        "status_counts": dict(Counter(sample["status"] for sample in summary["samples"])),
        "file": f"runs/{summary['run_id']}.json",
    }
    runs = [run for run in index["runs"] if run["run_id"] != entry["run_id"]] + [entry]
    runs.sort(key=lambda run: run.get("started_at") or "", reverse=True)
    index = {"updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "runs": runs}
    index_path.write_text(json.dumps(index, indent=2) + "\n")
    return index


def write(bundle, data_dir):
    data_dir = Path(data_dir)
    summary = summarize_bundle(bundle)
    run_path = data_dir / "runs" / f"{summary['run_id']}.json"
    run_path.parent.mkdir(parents=True, exist_ok=True)
    run_path.write_text(json.dumps(summary, separators=(",", ":")) + "\n")
    update_index(data_dir / "index.json", summary)
    return run_path


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        sys.exit("usage: python -m regridding_benchmarks.summary <bundle> <data-dir>")
    print(write(*argv))


if __name__ == "__main__":
    main()
