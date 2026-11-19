from io import BytesIO
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from regridding_benchmarks import bundle, report, runner
from regridding_benchmarks.inputs import InputUnavailable, resolve
from regridding_benchmarks.io import read_json, sha256
from regridding_benchmarks.metrics import adapter_result
from regridding_benchmarks.registry import load, select


ROOT = Path(__file__).resolve().parents[1]


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.case = {
            "id": "fixture.case", "version": 1, "family": "test",
            "adapter": "regridding_benchmarks.worker:main", "fixture": "constant",
            "source_geometry": {"axes": [0, 1]}, "target_geometry": {"axes": [0.5]},
            "quantity": "intensive", "method": "linear", "mask": "finite",
            "phases": ["apply"], "required_phases": ["apply"],
            "gates": {"constant_error": {"max": 1e-12}, "coverage": {"equals": 1}},
            "resources": {"timeout_seconds": 5},
            "profiles": ["standard"], "expected": ["ok"],
        }

    @staticmethod
    def measure(case, repeat, repo, scratch, dataset_path, input_record, threads, log):
        log.write(f"repeat {repeat}\n".encode())
        return {"status": "ok", "timings": {"apply": repeat * 0.1},
                "metrics": {"constant_error": 0, "coverage": 1}}

    def execute(self, run_id="example", resume=False):
        return runner.run(self.root, self.root / "runs", run_id, "standard",
                          {"repeats": 3, "publishable": True}, [self.case], {},
                          self.root / "cache", self.root / "scratch", "integration",
                          resume=resume)

    def test_interruption_resume_and_corruption(self):
        def interrupted(*args):
            if args[1] == 2:
                raise KeyboardInterrupt()
            return self.measure(*args)

        with patch.object(runner, "measure", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.execute()
        output = self.root / "runs/example"
        self.assertEqual(read_json(output / "manifest.json")["state"], "incomplete")
        committed = output / "samples/fixture.case.0001.json"
        original = committed.read_bytes()
        (output / "logs/.pending-test").write_bytes(b"Interrupted atomic write")
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            bundle.validate(output)
        with patch.object(runner, "measure", side_effect=self.measure) as measure:
            self.execute(resume=True)
            self.assertEqual([call.args[1] for call in measure.call_args_list], [2, 3])
        self.assertEqual(committed.read_bytes(), original)
        self.assertEqual(len(bundle.validate(output)[1]), 3)
        with self.assertRaisesRegex(ValueError, "clean source"):
            bundle.validate(output, publication=True)
        with patch.object(runner, "measure") as measure:
            self.execute(resume=True)
            measure.assert_not_called()
        (output / "logs/fixture.case.0001.log").write_text("corruption")
        with self.assertRaisesRegex(ValueError, "Incompatible checkpoint"):
            bundle.validate(output)

    def test_changed_case_cannot_resume(self):
        with patch.object(runner, "measure", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.execute()
        self.case["target_geometry"]["axes"] = [0.25]
        with self.assertRaisesRegex(ValueError, "Resume rejected"):
            self.execute(resume=True)

    def test_report_aggregates_and_retains_editions(self):
        with patch.object(runner, "measure", side_effect=self.measure):
            first = self.execute()
            second = self.execute("later")
        site = self.root / "site"
        report.build(first, site, legacy=ROOT / "docs")
        report.build(second, site, legacy=ROOT / "docs")
        index = (site / "index.html").read_text()
        self.assertIn("editions/later.html", index)
        self.assertIn("editions/example.html", index)
        self.assertIn("legacy/index.html", index)
        page = (site / "editions/later.html").read_text()
        self.assertIn("<td>0.2</td><td>3</td>", page)
        self.assertTrue((site / "editions/later/samples/fixture.case.0003.json").is_file())
        self.assertTrue((site / "tool-guide.html").is_file())

    def test_gates_and_phase_validation(self):
        result = self.measure(self.case, 1, None, None, None, None, None,
                              log=BytesIO())
        result["metrics"]["coverage"] = 0
        self.assertEqual(adapter_result(self.case, result)["status"], "failed_validation")
        result["timings"]["apply"] = float("nan")
        with self.assertRaisesRegex(ValueError, "Invalid timing"):
            adapter_result(self.case, result)

    def test_kills_worker_on_timeout(self):
        self.case["resources"]["timeout_seconds"] = 0.001
        output = runner.run(self.root, self.root / "runs", "timeout", "standard",
                            {"repeats": 1, "publishable": True}, [self.case], {},
                            self.root / "cache", self.root / "scratch", "integration")
        result = bundle.validate(output)[1][0][2]
        self.assertEqual(result["status"], "timeout")

    def test_dataset_cache_rejects_corruption(self):
        cache = self.root / "cache"
        cache.mkdir()
        source = self.root / "source"
        source.write_bytes(b"expected input")
        digest = sha256(source)
        dataset = {"id": "pinned", "sha256": digest}
        with self.assertRaises(InputUnavailable):
            resolve(dataset, cache, self.root)
        path = cache / digest
        path.write_bytes(source.read_bytes())
        self.assertEqual(resolve(dataset, cache, self.root), path)
        path.write_bytes(b"corrupt input")
        with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
            resolve(dataset, cache, self.root)

    def test_registry_has_all_legacy_families(self):
        profiles, cases, _ = load(ROOT)
        self.assertTrue({"small", "shared-grid", "chunked", "storage", "native-control"}
                        <= {case["family"] for case in cases.values()})
        self.assertGreater(len(select(cases, profiles, "extended")), len(select(cases, profiles, "smoke")))
