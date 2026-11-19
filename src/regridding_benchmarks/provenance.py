"""Source, dependency, and resource metadata for a benchmark series."""

import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from .io import fingerprint, sha256

THREADS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
           "NUMBA_NUM_THREADS", "GDAL_NUM_THREADS")


def packages():
    return {entry.metadata["Name"]: entry.version for entry in importlib.metadata.distributions()
            if entry.metadata.get("Name")}


def read(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def cpu_model():
    cpuinfo = read("/proc/cpuinfo") or ""
    for line in cpuinfo.splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    if sys.platform == "darwin":
        result = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                                text=True, capture_output=True)
        if result.returncode == 0:
            return result.stdout.strip()
    return platform.processor() or None


def resources():
    cgroup = "/sys/fs/cgroup/"
    cpu_limit = read(cgroup + "cpu.max")
    memory_limit = read(cgroup + "memory.max")
    affinity = sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None
    return {
        "platform": platform.platform(),
        "cpu_model": cpu_model(),
        "affinity": affinity,
        "logical_cpus": os.cpu_count(),
        "cpu_quota": cpu_limit or read(cgroup + "cpu/cpu.cfs_quota_us"),
        "cpu_period_v1": read(cgroup + "cpu/cpu.cfs_period_us") if not cpu_limit else None,
        "memory_limit": memory_limit or read(cgroup + "memory/memory.limit_in_bytes"),
        "host_memory": next((line.split(":", 1)[1].strip()
                             for line in (read("/proc/meminfo") or "").splitlines()
                             if line.startswith("MemTotal:")), None),
        "resource_class": os.environ.get("BENCH_RESOURCE_CLASS"),
    }


def source(repo):
    def git(*args):
        return subprocess.run(["git", "--no-optional-locks", "-C", str(repo), *args],
                              capture_output=True, check=True).stdout

    try:
        commit = git("rev-parse", "HEAD").decode().strip()
        changes = git("status", "--porcelain", "--untracked-files=all", "-z")
        paths = git("ls-files", "-z", "--cached", "--others", "--exclude-standard")
    except subprocess.CalledProcessError:
        return {"commit": None, "dirty": None, "working_tree_sha256": None}
    inputs = {}
    if changes:
        for name in os.fsdecode(paths).split("\0"):
            path = repo / name
            if name and path.is_file():
                inputs[name] = sha256(path)
    return {"commit": commit, "dirty": bool(changes),
            "working_tree_sha256": fingerprint(inputs) if changes else None}


def interpreter(case):
    variables = {"python": "BENCH_PYTHON", "compiled": "BENCH_COMPILED_PYTHON",
                 "xhealpixify": "BENCH_XHEALPIXIFY_PYTHON"}
    variable = variables.get(case.get("python_env"))
    return os.environ.get(variable, sys.executable) if variable else sys.executable


def python_environment():
    # Both pinned interpreters load the runner from this installation, even
    # when only the launcher interpreter has the package installed.
    installed = str(Path(__file__).resolve().parents[1])
    paths = os.environ.get("PYTHONPATH", "").split(os.pathsep)
    return {**os.environ, "PYTHONPATH": os.pathsep.join([installed, *filter(None, paths)])}


def environment(repo, cases):
    interpreters = {}
    for python in sorted({interpreter(case) for case in cases}):
        probe = subprocess.run(
            [python, "-c", "import json, platform; from regridding_benchmarks.provenance "
             "import packages; print(json.dumps({'python':platform.python_version(),"
             "'packages':packages()}))"],
            capture_output=True, text=True, check=True, env=python_environment(),
        )
        interpreters[python] = json.loads(probe.stdout)
    cdo = shutil.which("cdo")
    cdo_version = None
    if cdo:
        try:
            probe = subprocess.run([cdo, "-V"], capture_output=True, text=True, timeout=5)
        except subprocess.TimeoutExpired:
            cdo_version = "version probe timed out"
        else:
            cdo_version = next(iter((probe.stdout + probe.stderr).splitlines()), None)
    return {
        "image_digest": os.environ.get("BENCH_IMAGE_DIGEST"),
        "lock_sha256": lock_digests(repo),
        "interpreters": interpreters,
        "executables": {"cdo": {"path": cdo, "version": cdo_version}},
        "resources": resources(),
        "threads": {key: os.environ.get(key, "1") for key in THREADS},
        "cache_policy": {
            "inputs": "SHA-256 verified files",
            "worker": "fresh process and scratch per sample",
            "os_page_cache": os.environ.get("BENCH_PAGE_CACHE", "uncontrolled"),
        },
    }


def lock_digests(repo):
    locks = {*repo.glob("requirements*.lock"), *(repo / "environments").rglob("*.lock")}
    return {path.relative_to(repo).as_posix(): sha256(path) for path in sorted(locks)}
