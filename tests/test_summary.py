import json
import tempfile
import unittest
from pathlib import Path

from regridding_benchmarks import summary


def make_bundle(root, run_id="run-a", started_at="2026-01-01T00:00:00Z"):
    bundle = Path(root) / run_id
    (bundle / "samples").mkdir(parents=True)
    manifest = {
        "run_id": run_id, "profile": "standard", "repeats": 1, "series": "renkulab",
        "started_at": started_at, "finished_at": started_at, "source": {"commit": "abc"},
        "environment": {
            "executables": {"cdo": {"path": "/bin/cdo", "version": "2.6.5"}},
            "interpreters": {"py": {"python": "3.11", "packages": {"numpy": "2.0", "other": "1"}}},
        },
        "cases": [
            {"id": "c1", "family": "f", "method": "m", "quantity": "q", "expected": ["ok"]},
            {"id": "c2", "family": "f", "method": "m", "quantity": "q", "expected": ["unavailable"]},
            {"id": "c3", "family": "f", "method": "m", "quantity": "q", "expected": ["ok"]},
        ],
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    results = [
        ("c1", {"status": "ok", "reason": None, "timings": {"apply": 0.5},
                "metrics": {"coverage": 1.0, "flag": True, "name": "x", "nested": {"a": 1},
                            "arr": [1, 2], "long": "y" * 500},
                "resources": {"worker_peak_rss_bytes": 10}}),
        ("c2", {"status": "unavailable", "reason": "no data", "timings": {}, "metrics": {}}),
        ("c3", {"status": "crash", "reason": "boom", "timings": {}, "metrics": {}}),
    ]
    for case_id, result in results:
        sample = {"case_id": case_id, "repeat": 1, "result": result}
        (bundle / "samples" / f"{case_id}.0001.json").write_text(json.dumps(sample))
    return bundle


class SummaryTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_summary_fields_and_counts(self):
        run = summary.summarize_bundle(make_bundle(self.root))
        self.assertEqual(run["schema"], 1)
        self.assertFalse(run["publishable"])
        self.assertEqual(run["source_commit"], "abc")
        self.assertEqual(run["engines"], {"cdo": "2.6.5", "numpy": "2.0"})
        self.assertEqual(len(run["samples"]), 3)
        index = summary.update_index(self.root / "index.json", run)
        self.assertEqual(index["runs"][0]["status_counts"], {"ok": 1, "unavailable": 1, "crash": 1})
        self.assertEqual(index["runs"][0]["n_samples"], 3)

    def test_metrics_scalar_only(self):
        run = summary.summarize_bundle(make_bundle(self.root))
        first = next(s for s in run["samples"] if s["case_id"] == "c1")
        self.assertEqual(first["metrics"], {"coverage": 1.0, "flag": True, "name": "x"})
        self.assertEqual(first["resources"], {"worker_peak_rss_bytes": 10})

    def test_expected_flag(self):
        run = summary.summarize_bundle(make_bundle(self.root))
        expected = {s["case_id"]: s["expected"] for s in run["samples"]}
        self.assertEqual(expected, {"c1": True, "c2": True, "c3": False})

    def test_index_replaces_and_orders_newest_first(self):
        data = self.root / "data"
        for run_id, started in [("old", "2026-01-01T00:00:00Z"), ("new", "2026-03-01T00:00:00Z"),
                                ("mid", "2026-02-01T00:00:00Z")]:
            summary.write(make_bundle(self.root, run_id, started), data)
        index = json.loads((data / "index.json").read_text())
        self.assertEqual([r["run_id"] for r in index["runs"]], ["new", "mid", "old"])
        self.assertTrue((data / "runs" / "new.json").exists())
        summary.write(make_bundle(self.root / "again", "mid", "2026-02-01T00:00:00Z"), data)
        index = json.loads((data / "index.json").read_text())
        self.assertEqual([r["run_id"] for r in index["runs"]], ["new", "mid", "old"])


if __name__ == "__main__":
    unittest.main()
