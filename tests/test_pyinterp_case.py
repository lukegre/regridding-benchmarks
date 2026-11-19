"""Exercise the independent periodic reference without optional pyinterp."""
import unittest

from regridding_benchmarks.pyinterp_case import _oracle


class OracleTests(unittest.TestCase):
    def test_bilinear_and_periodic_seam(self):
        try:
            import numpy as np
        except ImportError as exc:
            raise unittest.SkipTest(str(exc)) from exc
        lon = np.array([0., 90., 180., 270.])
        lat = np.array([-1., 1.])
        values = np.array([[0., 2.], [1., 3.], [2., 4.], [3., 5.]])
        x = np.array([45., 315., -45., 405.])
        y = np.array([0., 0., 0., 0.])
        np.testing.assert_allclose(_oracle(np, lon, lat, values, x, y), [1.5, 2.5, 2.5, 1.5])


if __name__ == '__main__':
    unittest.main()
