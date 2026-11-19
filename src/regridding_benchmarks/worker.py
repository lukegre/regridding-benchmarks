"""Adapter process entry point."""

import importlib
import resource
import sys
from pathlib import Path

from .io import read_json, write_json


def main():
    request, response = map(Path, sys.argv[1:])
    payload = read_json(request)
    case = payload["case"]
    context = payload["context"]
    for field in ("repo", "scratch", "dataset_path"):
        if context[field] is not None:
            context[field] = Path(context[field])
    module, name = case["adapter"].split(":")
    adapter = getattr(importlib.import_module(module), name)
    result = adapter(case, context)
    if isinstance(result, dict):
        # Linux reports KiB and macOS reports bytes.
        unit = 1 if sys.platform == "darwin" else 1024
        result["resources"] = {
            "worker_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * unit,
            "child_peak_rss_bytes": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * unit,
        }
    write_json(response, result)


if __name__ == "__main__":
    main()
