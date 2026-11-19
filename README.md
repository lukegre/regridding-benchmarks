# Regridding benchmarks

Reproducible interoperability, numerical and performance benchmarks for geospatial remapping tools.

## Run a benchmark

Use the registry CLI from a checkout. The CLI also builds and validates reports in a Python
environment without the scientific engines. Install the pinned benchmark dependencies to
execute the numerical cases.

```sh
python -m pip install -e .
regridding-benchmarks list-cases --profile smoke
regridding-benchmarks fetch --profile smoke
regridding-benchmarks run --profile smoke --output-dir /tmp/regridding-runs --run-id smoke-local
regridding-benchmarks validate-bundle /tmp/regridding-runs/smoke-local
regridding-benchmarks build-report /tmp/regridding-runs/smoke-local --output-dir /tmp/regridding-site
```

See the [reproduction handbook](docs/reproduction.md), [deployment guide](docs/deployment.md),
and [published workload coverage](docs/workload-coverage.md).

## Legacy edition

The [legacy archive](benchmarks/legacy/README.md) holds the original runners, raw results,
and reports. Use `regridding-benchmarks import-legacy` to verify and export the recorded edition.

- [Large and chunked results](https://lukegre.github.io/regridding-benchmarks/)
- [Small-grid survey](https://lukegre.github.io/regridding-benchmarks/small-data.html)
- [Tool guide](https://lukegre.github.io/regridding-benchmarks/tool-guide.html)
- [External benchmark comparison](https://lukegre.github.io/regridding-benchmarks/comparison.html)
- [Tool-selection skill](skills/regridding-tool-selection/SKILL.md)

The current GitHub Pages edition is served from `docs/`. The deployment guide describes
how to cut over to the bundle-based publication workflow.
