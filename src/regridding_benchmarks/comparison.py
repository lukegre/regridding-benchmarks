"""Common-support comparison on the legacy masked rectilinear fixture."""

from hashlib import sha256
from time import perf_counter


def arrays_digest(np, *arrays):
    digest = sha256()
    for array in arrays:
        canonical = np.asarray(array, dtype="<f8", order="C")
        digest.update(str(canonical.shape).encode("ascii"))
        digest.update(canonical.tobytes())
    return digest.hexdigest()


def run(case, context):
    import sys

    from .legacy import ARCHIVE_DIR

    sys.path.insert(0, str(context["repo"] / ARCHIVE_DIR))
    try:
        start = perf_counter()
        import numpy as np
        import suite
        import scipy.interpolate  # preload SciPy for both adapters
    except ImportError as error:
        return {"status": "unavailable", "reason": str(error)}
    finally:
        sys.path.pop(0)
    imports = perf_counter() - start
    if case.get("options", {}).get("duplicate_axis"):
        return duplicate_axis(suite, imports)
    start = perf_counter()
    lon, lat, field, mask, target_lon, target_lat, truth = suite.sample("rectilinear", "mask_hole")
    fixture = perf_counter() - start
    args = (lon, lat, field, mask, target_lon, target_lat)
    outputs = {}
    timings = {"imports": imports, "fixture": fixture}
    for package in ("scipy", "xarray"):
        start = perf_counter()
        outputs[package] = suite.apply(package, "rectilinear", "mask_hole", *args)
        timings[f"{package}_application"] = perf_counter() - start

    left, right = outputs.values()
    finite = {package: np.isfinite(values) for package, values in outputs.items()}
    common = finite["scipy"] & finite["xarray"]
    metrics = {
        "common_coverage": float(common.mean()),
        "finite_mask_mismatches": int(np.count_nonzero(finite["scipy"] ^ finite["xarray"])),
        "common_max_difference": float(np.max(np.abs(left[common] - right[common]))) if common.any() else None,
    }
    for package, values in outputs.items():
        support = finite[package]
        metrics[f"{package}_coverage"] = float(support.mean())
        metrics[f"{package}_rmse"] = (
            float(np.sqrt(np.mean((values[support] - truth[support]) ** 2))) if support.any() else None
        )
        metrics[f"{package}_common_rmse"] = (
            float(np.sqrt(np.mean((values[common] - truth[common]) ** 2))) if common.any() else None
        )
    return {
        "status": "ok", "timings": timings, "metrics": metrics,
        "geometry": {
            "source_sha256": arrays_digest(np, lon, lat),
            "target_sha256": arrays_digest(np, target_lon, target_lat),
            "input_sha256": arrays_digest(np, field, mask),
        },
    }


def duplicate_axis(suite, imports):
    start = perf_counter()
    fixture = suite.sample("rectilinear", "duplicate")
    timings = {"imports": imports, "fixture": perf_counter() - start}
    start = perf_counter()
    try:
        suite.apply("scipy", "rectilinear", "duplicate", *fixture[:-1])
    except ValueError as error:
        if "strictly ascending or descending" not in str(error):
            raise
        return {"status": "expected_rejection", "reason": str(error),
                "timings": {**timings, "application": perf_counter() - start}}
    return {"status": "failed_validation", "reason": "SciPy accepted a duplicate source axis",
            "timings": {**timings, "application": perf_counter() - start}}
