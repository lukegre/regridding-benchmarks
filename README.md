# Regridding benchmarks

Synthetic interoperability and numerical-suitability tests for geospatial remapping tools.

**[Interactive results on GitHub Pages](https://lukegre.github.io/regridding-benchmarks/)** · [Detailed report](REPORT.md) · [CSV metrics](all_results.csv) · [JSON results](all_results.json)

The recorded run covers satellite swaths, rectilinear grids, ROMS-style curvilinear grids, icosahedral meshes, HEALPix, and full Gaussian grids. It includes 519 attempted operations (484 returned outputs and 35 errors) and 405 combinations outside the tested adapter scope. An output is not a correctness verdict; errors include deliberately malformed inputs.

The report's heatmaps support scenario selection, exact values, keyboard focus, and selecting a cell to inspect its evidence. Its timing tables show diagnostic wall time and separately recorded xESMF weight-construction time. These single-run measurements include variable startup, import, JIT and I/O costs and are not a controlled performance ranking.

## Reproduce the suite

Linux x86_64, Python 3.12, `uv` and `micromamba` are required. Exact versions/builds from the recorded environment are included in the lock files.

```sh
uv venv .venv --python 3.12
UV_CACHE_DIR=/tmp/geobench-uv uv pip install --python .venv/bin/python -r requirements-python.lock
MAMBA_ROOT_PREFIX="$PWD/mamba-root" micromamba create -y -p "$PWD/compiled" -f requirements-compiled.lock
UV_CACHE_DIR=/tmp/geobench-uv uv pip install --python compiled/bin/python -r requirements-compiled-extras.lock
bash reproduce.sh
.venv/bin/python plot.py
```

Fixture generation is deterministic. There are no real satellite downloads and no memory-exhaustion tests. Conservative workflows need correct cell geometry; coordinate conventions, masks, pixel ordering and variable semantics are part of the tested interfaces. The report documents the adapters and their limits.

## Files

- `suite.py`: common grid/scenario probes and package adapters.
- `native.py`, `extra.py`, `controls.py`: native meshes, conservative ROMS, CRS, ordering, longitude and cached-weight controls.
- `cli_probes.py`: TempestRemap/NCO mesh, weights and application workflow.
- `results/`: original per-adapter metrics, warnings, traces, CLI logs and NetCDF inputs/outputs. Absolute paths in historical logs refer to the original run workspace.
- `report.py`, `plot.py`, `build_artifact.py`, `interactive-figures.*`, `update_figures.py`: report generation.
- `build_pages.py`: regenerate the report, interactive figures and downloadable results archive in `docs/`.
- `docs/`: GitHub Pages publication, including downloadable CSV/JSON and source/results archive.

To rebuild Pages from existing recorded results:

```sh
.venv/bin/python build_pages.py
```

GitHub Pages serves `main` → `/docs`. The benchmark environments and site credentials are excluded from Git.
