"""Compare migrated kernels with recorded numerical evidence when installed."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from regridding_benchmarks.legacy_adapter import run

ROOT = Path(__file__).resolve().parents[1]


class LegacyParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import numpy  # noqa: F401
            import scipy  # noqa: F401
            import xarray  # noqa: F401
        except ImportError as error:
            raise unittest.SkipTest(str(error)) from error
        cls.cases = json.loads((ROOT / 'benchmarks/legacy/cases.json').read_text())['cases']

    def test_small_numerics(self):
        history = json.loads((ROOT / 'all_results.json').read_text())
        for package, grid, scenario in [('scipy', 'rectilinear', 'smooth'),
                                        ('scipy', 'rectilinear', 'constant'),
                                        ('xarray', 'gaussian', 'smooth'),
                                        ('scipy', 'gaussian', 'nan_hole')]:
            with self.subTest(package=package, grid=grid, scenario=scenario), TemporaryDirectory() as tmp:
                matches = lambda row: all(row.get(k) == v for k, v in
                    [('package', package), ('grid', grid), ('scenario', scenario)])
                case = next(c for c in self.cases if c['family'] == 'small' and matches(c['options']))
                historical = next(row for row in history if matches(row))
                result = run(case, {'repo': ROOT, 'scratch': Path(tmp), 'repeat': 1, 'dataset_path': None})
                self.assertEqual(result['status'], 'ok')
                for metric in ('finite_fraction', 'rmse', 'max_error'):
                    self.assertAlmostEqual(result['metrics'][metric], historical[metric], delta=1e-12)

    def test_longitude_control(self):
        history = json.loads((ROOT / 'results/controls_python.json').read_text())
        for wrapped in ('False', 'True'):
            name = 'longitude_wrapped_' + wrapped
            case = next(c for c in self.cases if c['family'] == 'control'
                        and c['options']['package'] == 'SciPy' and c['options']['control'] == name)
            historical = next(row for row in history if row['package'] == 'SciPy' and row['case'] == name)
            with self.subTest(wrapped=wrapped), TemporaryDirectory() as tmp:
                result = run(case, {'repo': ROOT, 'scratch': Path(tmp), 'repeat': 1, 'dataset_path': None})
                self.assertEqual(result['status'], 'ok')
                for metric in ('finite_fraction', 'rmse'):
                    self.assertAlmostEqual(result['metrics'][metric], historical[metric], delta=1e-12)


if __name__ == '__main__':
    unittest.main()
