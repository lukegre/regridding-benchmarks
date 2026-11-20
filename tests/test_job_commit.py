"""Run deploy/renku/job_commit.sh against local bare remotes (offline)."""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy" / "renku" / "job_commit.sh"
CASE = "masked-rectilinear-common-support"
# Stand-in CLI: real run/validate-bundle for one small case; fetch and build-report are skipped.
STUB = """#!/bin/sh
sub=$1; shift
case "$sub" in
  fetch|build-report) exit 0;;
  run) exec "{py}" -m regridding_benchmarks run --case {case} "$@";;
  *) exec "{py}" -m regridding_benchmarks "$sub" "$@";;
esac
"""


def git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class JobCommitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.main_remote = self.tmp / "main.git"
        self.results_remote = self.tmp / "results.git"
        for remote in (self.main_remote, self.results_remote):
            git("init", "--bare", "--initial-branch=main", str(remote))
        seed = self.tmp / "seed"
        git("clone", str(self.main_remote), str(seed))
        (seed / "README").write_text("seed\n")
        git("add", "README", cwd=seed)
        git("-c", "user.name=t", "-c", "user.email=t@example.org", "commit", "-m", "seed", cwd=seed)
        git("push", "origin", "HEAD:main", cwd=seed)
        self.seed = seed
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        stub = self.bin / "regridding-benchmarks"
        stub.write_text(STUB.format(py=sys.executable, case=CASE))
        stub.chmod(stub.stat().st_mode | stat.S_IXUSR)

    def run_job(self, run_id):
        src = str(ROOT / "src")
        env = {
            **os.environ,
            "PATH": f"{self.bin}{os.pathsep}{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}",
            "PYTHONPATH": src,
            "BENCH_ENV_ROOT": str(self.tmp),
            "BENCH_REPO": str(ROOT),
            "BENCH_RESULTS_REMOTE": str(self.results_remote),
            "BENCH_MAIN_REMOTE": str(self.main_remote),
            "BENCH_SCRATCH_DIR": str(self.tmp / "scratch"),
            "BENCH_DONE_MARKER": str(self.tmp / f"done-{run_id}"),
            "BENCH_RUN_ID": run_id,
            "BENCH_PROFILE": "smoke",
        }
        return subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=300)

    def main_file(self, path):
        git("pull", "--quiet", "origin", "main", cwd=self.seed)
        return json.loads((self.seed / path).read_text())

    def test_pushes_summary_to_main_and_keeps_earlier_runs(self):
        first = self.run_job("run-one")
        self.assertEqual(first.returncode, 0, first.stderr)
        run = self.main_file("docs/data/runs/run-one.json")
        self.assertEqual(run["run_id"], "run-one")
        self.assertEqual([r["run_id"] for r in self.main_file("docs/data/index.json")["runs"]], ["run-one"])

        # A push landing on main in the meantime must not break the next job.
        (self.seed / "other.txt").write_text("x\n")
        git("add", "other.txt", cwd=self.seed)
        git("-c", "user.name=t", "-c", "user.email=t@example.org", "commit", "-m", "other", cwd=self.seed)
        git("push", "origin", "HEAD:main", cwd=self.seed)

        second = self.run_job("run-two")
        self.assertEqual(second.returncode, 0, second.stderr)
        ids = [r["run_id"] for r in self.main_file("docs/data/index.json")["runs"]]
        self.assertCountEqual(ids, ["run-one", "run-two"])
        self.assertTrue((self.seed / "other.txt").exists())
        self.assertTrue((self.seed / "docs/data/runs/run-one.json").exists())

        # The full bundle still goes to the results branch.
        out = subprocess.run(["git", "--git-dir", str(self.results_remote), "ls-tree", "-r", "--name-only", "results"],
                             capture_output=True, text=True, check=True).stdout
        self.assertIn("results/run-one/manifest.json", out)
        self.assertIn("results/run-two/manifest.json", out)


if __name__ == "__main__":
    unittest.main()
