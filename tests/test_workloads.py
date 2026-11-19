import importlib.util
import os
import hashlib
import tempfile
import unittest
from pathlib import Path
from regridding_benchmarks.workloads import run


class WorkloadTests(unittest.TestCase):
    def invoke(self, operation):
        with tempfile.TemporaryDirectory() as directory:
            return run({'options': {'operation': operation}}, {'scratch': Path(directory), 'dataset_path': None})

    def test_icon_does_not_claim_unpinned_input(self):
        result = self.invoke('icon')
        self.assertEqual(result['status'], 'unavailable')
        self.assertIn('checksum', result['reason'])

    @unittest.skipUnless(importlib.util.find_spec('healpy'), 'healpy not installed')
    def test_ring_nested_and_centres(self):
        self.assertTrue(self.invoke('indexing')['metrics']['permutation_identity'])

    @unittest.skipUnless(importlib.util.find_spec('xhealpixify'), 'xhealpixify not installed')
    def test_xhealpixify_masked_analytic(self):
        result = self.invoke('xhealpixify')
        self.assertEqual(result['status'], 'ok')
        self.assertGreater(result['metrics']['partially_masked_target_cells'], 0)
        self.assertGreater(result['metrics']['empty_target_cells'], 0)

    @unittest.skipUnless(os.environ.get('MUR_TEST_CSV') and importlib.util.find_spec('xhealpixify'), 'verified MUR CSV or xhealpixify not available')
    def test_xhealpixify_mur_coast(self):
        path = Path(os.environ['MUR_TEST_CSV'])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), '6fc27fc35967cfc87cbbfddcddaafd640d8d571ae7cad932b4b7deb9b1a588c6')
        result = run({'options': {'operation': 'xhealpixify_mur'}}, {'dataset_path': path})
        self.assertEqual(result['status'], 'ok')
        self.assertGreater(result['metrics']['partially_masked_target_cells'], 0)
        self.assertGreater(result['metrics']['empty_target_cells'], 0)

    @unittest.skipUnless(all(importlib.util.find_spec(x) for x in ('healpy', 'xdggs')), 'healpy/xdggs not installed')
    def test_xdggs_healpy_index_agreement(self):
        self.assertTrue(self.invoke('xdggs_indexing')['metrics']['healpy_index_agreement'])

    @unittest.skipUnless(all(importlib.util.find_spec(x) for x in ('healpy', 'healpix_geo')), 'healpy/healpix-geo not installed')
    def test_wgs84_against_authalic_sphere(self):
        metrics = self.invoke('wgs84')['metrics']
        self.assertLess(metrics['max_authalic_latitude_error_degrees'], 1e-9)

    @unittest.skipUnless(importlib.util.find_spec('xdggs'), 'xdggs not installed')
    def test_compressed_range_coverage(self):
        metrics = self.invoke('range_memory')['metrics']
        self.assertEqual(metrics['covered_cells'], 2 * 4 ** 8)
        self.assertLess(metrics['index_nbytes'], metrics['dense_uint64_equivalent_bytes'])

    @unittest.skipUnless(all(importlib.util.find_spec(x) for x in ('xarray', 'xdggs')), 'xdggs not installed')
    def test_cf_roundtrip(self):
        self.assertTrue(self.invoke('cf')['metrics']['values_and_mask_preserved'])

    @unittest.skipUnless(all(importlib.util.find_spec(x) for x in ('xarray', 'xdggs', 'zarr')), 'xdggs/zarr not installed')
    def test_zarr_roundtrip(self):
        self.assertTrue(self.invoke('zarr')['metrics']['grid_metadata_preserved'])


if __name__ == '__main__':
    unittest.main()
