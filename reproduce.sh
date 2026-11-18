#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1
export NUMBA_CACHE_DIR=/tmp/geobench-numba MPLCONFIGDIR=/tmp/geobench-mpl
# First recreate .venv from requirements-python.lock and compiled from the
# conda explicit requirements-compiled.lock. Add healpy and trimesh to compiled.
.venv/bin/python run_all.py
.venv/bin/python run_compiled.py
.venv/bin/python run_cdo.py
.venv/bin/python native.py python
compiled/bin/python native.py compiled
.venv/bin/python extra.py python
compiled/bin/python extra.py compiled
.venv/bin/python controls.py python
compiled/bin/python controls.py compiled
compiled/bin/python cli_probes.py
.venv/bin/python reproduce_astropy.py > results/astropy_minimal.log 2>&1
.venv/bin/python xarray_regrid_controls.py
.venv/bin/python report.py
