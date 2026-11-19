"""Validate adapter records and apply declared numerical criteria."""

import math

from .registry import OUTCOMES


def is_number(value):
    return type(value) in (float, int) and math.isfinite(value)


def adapter_result(case, value):
    if not isinstance(value, dict) or value.get("status") not in OUTCOMES:
        raise ValueError("Adapter returned an unknown outcome")
    status = value["status"]
    if status != "ok" and not value.get("reason"):
        raise ValueError("Non-success outcome needs a reason")
    timings = value.get("timings", {})
    metrics = value.get("metrics", {})
    if not isinstance(timings, dict) or not isinstance(metrics, dict):
        raise ValueError("Timings and metrics must be objects")
    for phase, seconds in timings.items():
        if phase not in case["phases"] or not is_number(seconds) or seconds < 0:
            raise ValueError(f"Invalid timing for {phase!r}")
    for phase in case.get("required_phases", []):
        if status == "ok" and phase not in timings:
            raise ValueError(f"Missing required timing for {phase!r}")
    violations = []
    if status == "ok":
        for metric, gate in case.get("gates", {}).items():
            observed = metrics.get(metric)
            if "equals" in gate:
                passed = observed == gate["equals"] and observed is not None
            else:
                passed = (is_number(observed)
                          and gate.get("min", -math.inf) <= observed <= gate.get("max", math.inf))
            if not passed:
                violations.append(f"{metric}={observed!r} outside {gate}")
    result = {**value, "timings": timings, "metrics": metrics}
    if violations:
        result.update(status="failed_validation", reason="; ".join(violations))
    return result
