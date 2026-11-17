# Regridding benchmarks

Synthetic interoperability and numerical-suitability tests for geospatial remapping tools.

**[Large and chunked results](https://lukegre.github.io/regridding-benchmarks/)** · [Small-grid survey](https://lukegre.github.io/regridding-benchmarks/small-data.html) · [Tool selection and input specifications](https://lukegre.github.io/regridding-benchmarks/tool-guide.html)

The home page presents larger shared-grid timings and chunked-array experiments. Setup, lazy graph construction and completed interpolation are reported separately where applicable. Interactive filters and per-repeat inspection expose the recorded evidence.

The separate small-grid survey covers satellite swaths, rectilinear grids, ROMS-style curvilinear grids, icosahedral meshes, HEALPix and Gaussian grids. It includes 519 attempted operations (484 returned outputs and 35 errors) and 405 combinations outside the tested adapter scope. An output is not a correctness verdict; errors include deliberately malformed inputs. Its diagnostic timings include startup and other overheads and are not a controlled performance ranking.

The [tool guide](TOOL_GUIDE.md) describes data requirements, geometry and missing-value contracts, chunking constraints and interpolation choices for categories, packed integers, counts, booleans, flags and timestamps. [Machine-readable contracts](tool_contracts.json) support future agents; these advisory contracts require version-specific validation.

## Larger shared-grid timing tier

The larger tier is separate from the original small adversarial survey. Every adapter in a family/size profile uses identical source and destination coordinates and scalar values. Geometry/value hashes are checked by the aggregator. The 512 and 1024 scales are common across packages, not calibrated per package; all four CRS adapters also run a shared 4096×4096 tier. MIR repetitions use isolated processes and fresh cache directories. Each profile runs three times serially with one thread. Setup and eager application are measured separately; imports, warmup and fixture creation are outside the timers. Fused APIs and native CLI I/O are identified explicitly.

```sh
.venv/bin/python run_large.py --scales 512 1024 --repeats 3
.venv/bin/python run_large.py --scales 4096 --repeats 3 --only rasterio rioxarray odc_geo pyproj
.venv/bin/python summarize_large.py
.venv/bin/python build_pages.py
```

If environments are stored elsewhere, set `BENCH_ENV_ROOT` to the directory containing `.venv/` and `compiled/`. The runner resumes completed profiles. See the [larger-run report](LARGE_REPORT.md) and [large-tier methodology](large_results/README.md). This tier includes WGS84 → Swiss LV95 and WGS84 → Web Mercator, separately comparing coordinate transformation and raster value reprojection.

## Chunked-array tier

[Chunked methodology and results](CHUNKED_REPORT.md) cover a common 4 × 512 × 512 cube, three chunk layouts and three repeats per profile: 45 in-memory measurements across xESMF, xarray and odc-geo, plus three warm-cache NetCDF4 read measurements. Rectilinear, ROMS and two CRS reprojections are included. The larger unchunked tier remains the primary performance comparison. Chunked tests use a common smaller spatial size after expensive 1024-grid pilots; those incomplete pilots are reported separately, not as completed timings.

Weights are constructed once per profile and reused across layouts. Complete compute is timed separately from graph construction. xESMF explicitly uses full-horizontal output chunks, so this is not a demonstration of distributed spatial output. One odc-geo LV95 layout has four finite-mask differences against the eager reference; inspect the accuracy column before assuming equivalence.

After installing the environments below, follow the serial commands in [CHUNKED_REPORT.md](CHUNKED_REPORT.md), then rebuild Pages. Raw measurements and geometry/value hashes are in `chunked_results/`.

## Reproduce the original small suite

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

Optional report UI verification (requires Playwright and Chromium): `python qa/verify_report.py`. This checks all three pages, size and chunk filters, separate timings, CRS comparison groups, per-repeat inspection, data contracts and responsive layout.
