"""Load and validate the versioned case and dataset registry."""

import re

from .io import read_json

ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
OUTCOMES = frozenset({
    "ok", "expected_rejection", "unsupported", "unavailable",
    "timeout", "crash", "failed_validation",
})


def items(directory, key, exclude=()):
    for path in sorted(directory.rglob("*.json")):
        if path.name in exclude:
            continue
        value = read_json(path)
        yield from (value[key] if isinstance(value, dict) else value)


def index(rows, kind):
    result = {}
    for row in rows:
        identifier = row.get("id")
        if not isinstance(identifier, str) or not ID.fullmatch(identifier) or identifier in result:
            raise ValueError(f"Invalid or duplicate {kind} ID {identifier!r}")
        result[identifier] = row
    return result


def validate_case(case, datasets, profiles):
    def require(condition, detail):
        if not condition:
            raise ValueError(f"{case['id']} {detail}")

    require(type(case.get("version")) is int and case["version"] > 0, "needs a positive version")
    for field in ("family", "adapter", "quantity", "method", "mask"):
        require(bool(case.get(field)), f"needs {field}")
    adapter = case["adapter"]
    require(isinstance(adapter, str) and adapter.count(":") == 1, "needs a module:function adapter")
    require(bool(case.get("fixture")) != bool(case.get("dataset")), "needs exactly one input")
    if case.get("dataset"):
        require(case["dataset"] in datasets, "references an unknown dataset")
    for key in ("source_geometry", "target_geometry", "resources"):
        require(isinstance(case.get(key), dict) and case[key], f"needs a {key} object")
    timeout = case["resources"].get("timeout_seconds")
    require(type(timeout) in (int, float) and 0 < timeout <= 86400, "needs a bounded timeout")
    for key, allowed in (("profiles", profiles), ("expected", OUTCOMES), ("phases", None)):
        values = case.get(key)
        require(isinstance(values, list) and all(isinstance(value, str) and value for value in values),
                f"needs a {key} list")
        require(len(values) == len(set(values)) and (key == "phases" or values),
                f"has empty or duplicate {key}")
        require(allowed is None or set(values) <= set(allowed), f"has unknown {key}")
    optional_phases = case.get("required_phases", [])
    require(isinstance(optional_phases, list) and set(optional_phases) <= set(case["phases"]),
            "has required phases outside its timing phases")
    require(isinstance(case.get("options", {}), dict), "needs an options object")
    gates = case.get("gates", {})
    require(isinstance(gates, dict), "needs a gates object")
    for metric, gate in gates.items():
        require(isinstance(gate, dict) and gate and
                (set(gate) == {"equals"} or set(gate) <= {"min", "max"}),
                f"has an invalid gate for {metric}")
        if "equals" not in gate:
            require(all(type(value) in (int, float) for value in gate.values()) and
                    gate.get("min", float("-inf")) <= gate.get("max", float("inf")),
                    f"has invalid gate bounds for {metric}")


def load(repo):
    profiles = read_json(repo / "benchmarks" / "profiles.json")
    for name, settings in profiles.items():
        if (not ID.fullmatch(name) or type(settings.get("repeats")) is not int
                or settings["repeats"] < 1 or type(settings.get("publishable")) is not bool):
            raise ValueError(f"Invalid profile {name}")
    datasets = index(items(repo / "datasets", "datasets"), "dataset")
    for identifier, dataset in datasets.items():
        if dataset.get("sha256") is not None and not DIGEST.fullmatch(dataset["sha256"]):
            raise ValueError(f"Invalid checksum for {identifier}")
    cases = index(items(repo / "benchmarks", "cases", ("profiles.json",)), "case")
    for case in cases.values():
        validate_case(case, datasets, profiles)
    return profiles, cases, datasets


def select(cases, profiles, profile, identifiers=()):
    if profile not in profiles:
        raise ValueError(f"Unknown profile {profile!r}")
    eligible = {key: case for key, case in cases.items() if profile in case["profiles"]}
    missing = set(identifiers) - eligible.keys()
    if missing:
        raise ValueError(f"Cases outside {profile} profile: {', '.join(sorted(missing))}")
    roster = [case for key, case in sorted(eligible.items()) if not identifiers or key in identifiers]
    if not roster:
        raise ValueError(f"No cases in {profile} profile")
    return roster
