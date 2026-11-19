"""Serial, resumable benchmark runs in isolated worker processes."""

import fcntl
import os
import signal
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .inputs import InputUnavailable, resolve
from .io import atomic_file, fingerprint, read_json, sha256, write_json
from .metrics import adapter_result
from .provenance import environment, interpreter, python_environment, source
from .registry import ID

SCHEMA = 1


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def sample_id(case_id, repeat):
    return f"{case_id}.{repeat:04d}"


def planned_samples(manifest):
    for case in manifest["cases"]:
        for repeat in range(1, manifest["repeats"] + 1):
            yield sample_id(case["id"], repeat), case, repeat


def paths_for(bundle, key):
    return bundle / "samples" / f"{key}.json", bundle / "logs" / f"{key}.log"


def case_input(case, datasets, cache, repo):
    identifier = case.get("dataset")
    if not identifier:
        return {"fixture": case["fixture"]}, None
    dataset = datasets[identifier]
    try:
        path = resolve(dataset, cache, repo)
    except InputUnavailable as error:
        return {"dataset": dataset, "verified": False, "reason": str(error)}, None
    return {"dataset": dataset, "verified": True, "sha256": dataset["sha256"]}, path


def failure(status, reason):
    return {"status": status, "reason": reason, "timings": {}, "metrics": {}}


def measure(case, repeat, repo, scratch, dataset_path, input_record, threads, log):
    if "reason" in input_record:
        log.write((input_record["reason"] + "\n").encode())
        return failure("unavailable", input_record["reason"])
    request, response = scratch / "request.json", scratch / "response.json"
    write_json(request, {"case": case, "context": {
        "repo": str(repo), "scratch": str(scratch), "repeat": repeat,
        "dataset_path": str(dataset_path) if dataset_path else None,
    }})
    env = {**python_environment(), **threads, "TMPDIR": str(scratch),
           "PYTHONFAULTHANDLER": "1",
           "NUMBA_CACHE_DIR": str(scratch / "numba"),
           "XDG_CACHE_HOME": str(scratch / "xdg-cache"),
           "MPLCONFIGDIR": str(scratch / "matplotlib")}
    worker = subprocess.Popen(
        [interpreter(case), "-m", "regridding_benchmarks.worker", str(request), str(response)],
        cwd=scratch, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    try:
        worker.wait(timeout=case["resources"]["timeout_seconds"])
    except subprocess.TimeoutExpired:
        return failure("timeout", "Worker exceeded its case time limit")
    finally:
        # Also stop descendants that survive their worker on cancellation or timeout.
        try:
            os.killpg(worker.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        worker.wait()
    if worker.returncode:
        return failure("crash", f"Worker exited with status {worker.returncode}")
    try:
        return adapter_result(case, read_json(response))
    except (KeyError, OSError, TypeError, ValueError) as error:
        return failure("failed_validation", f"Invalid adapter result: {error}")


def compatible_sample(path, log, key, case, repeat, signature):
    if not path.is_file():
        return False
    result = read_json(path)
    if (result["run_fingerprint"] != signature or result["sample_id"] != key
            or result["case_id"] != case["id"] or result["repeat"] != repeat
            or not log.is_file() or sha256(log) != result["log_sha256"]):
        raise ValueError(f"Incompatible checkpoint {path}")
    if adapter_result(case, result["result"]) != result["result"]:
        raise ValueError(f"Invalid checkpoint {path}")
    return True


def run(repo, output, run_id, profile, profile_settings, roster, datasets, cache,
        scratch_root, series, *, resume=False, full_profile=True):
    if not ID.fullmatch(run_id) or not ID.fullmatch(series):
        raise ValueError("Invalid run ID or series")
    output.mkdir(parents=True, exist_ok=True)
    with (output / f".{run_id}.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError(f"Run {run_id} is already active") from error
        return run_locked(repo, output / run_id, profile, profile_settings, roster,
                          datasets, cache, scratch_root, series, resume, full_profile)


def run_locked(repo, bundle, profile, settings, roster, datasets, cache,
               scratch_root, series, resume, full_profile):
    manifest_path = bundle / "manifest.json"
    if bundle.exists() and not resume:
        raise ValueError(f"Run already exists: {bundle}; use --resume")
    if resume and not manifest_path.is_file():
        raise ValueError(f"No run manifest to resume in {bundle}")
    inputs = {case["id"]: case_input(case, datasets, cache, repo) for case in roster}
    identity = {
        "schema_version": SCHEMA, "run_id": bundle.name, "profile": profile,
        "repeats": settings["repeats"], "publishable_profile": settings["publishable"],
        "full_profile": full_profile, "series": series, "source": source(repo),
        "environment": environment(repo, roster), "cases": roster,
        "inputs": {key: record for key, (record, _) in inputs.items()},
    }
    signature = fingerprint(identity)
    if resume:
        manifest = read_json(manifest_path)
        if manifest["run_fingerprint"] != signature:
            raise ValueError("Resume rejected because run inputs, source, or environment changed")
        if manifest["state"] == "complete":
            from .bundle import validate
            validate(bundle)
            return bundle
        # An abrupt process exit can leave an uncommitted temporary file.
        for directory in (bundle, bundle / "samples", bundle / "logs"):
            for temporary in directory.glob(".pending-*"):
                temporary.unlink()
    else:
        manifest = {**identity, "run_fingerprint": signature, "state": "incomplete",
                    "started_at": timestamp()}
        write_json(manifest_path, manifest)
    scratch_root.mkdir(parents=True, exist_ok=True)
    files = {}
    for key, case, repeat in planned_samples(manifest):
        path, log_path = paths_for(bundle, key)
        if not compatible_sample(path, log_path, key, case, repeat, signature):
            record, dataset_path = inputs[case["id"]]
            started = timestamp()
            with tempfile.TemporaryDirectory(prefix="sample-", dir=scratch_root) as temporary:
                with atomic_file(log_path) as log:
                    result = measure(case, repeat, repo, Path(temporary), dataset_path, record,
                                     identity["environment"]["threads"], log)
            default_geometry = {
                side: {"specification_sha256": fingerprint(case[f"{side}_geometry"])}
                for side in ("source", "target")
            }
            sample = {
                "sample_id": key, "case_id": case["id"], "repeat": repeat,
                "run_fingerprint": signature, "started_at": started, "finished_at": timestamp(),
                "log_sha256": sha256(log_path), "geometry": result.get("geometry", default_geometry),
                "result": result,
            }
            write_json(path, sample)
        for file in (path, log_path):
            files[file.relative_to(bundle).as_posix()] = sha256(file)
    if source(repo) != identity["source"]:
        raise ValueError("Source changed during the benchmark; the run remains incomplete")
    manifest.update(state="complete", finished_at=timestamp())
    # Write the inventory first so a visible complete manifest has a corresponding inventory.
    files["manifest.json"] = fingerprint(manifest)
    write_json(bundle / "checksums.json", files)
    write_json(manifest_path, manifest)
    return bundle
