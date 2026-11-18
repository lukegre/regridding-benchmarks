# xarray-regrid 0.4.2 benchmark extension

Added 48 large-tier repetitions across 16 profiles, including a separate xarray_axes query-layout control. Added 27 chunked measurements across 9 profiles, plus 162 small adversarial probes and 5 targeted usability/numerical controls.

## Protocol

The source/target coordinates and values are unchanged from the common 512/1024 rectilinear and full Gaussian fixtures. Canonical hashes are checked alongside all existing tools. Each large profile has three serial one-thread runs after a small warmup; imports and fixture preparation are excluded. Existing measured records are retained. The three chunk layouts use the same 4 × 512 × 512 cube and missing patch, synchronous Dask and three repeats.

The public xarray-regrid accessor does not expose reusable construction separately. Setup is array/API preparation; formatting, boundary handling and weight/interpolation work occur inside application on every call. These profiles are fused, not a claim that conservative weight construction is free. The new xarray_axes control uses 1-D target axes; the historical xarray adapter uses 2-D target query arrays. Both describe identical physical grids. xarray-regrid linear/nearest use xarray interpolation internally.

Conservative uses latitude_coord="lat", skipna=True and nan_threshold=1.0, with native output chunk defaults. Its cells follow meridians/parallels and inferred bounds; ESMF uses great-circle edges. Smooth-field centre-sample RMSE is not an integral-conservation verdict. No general curvilinear/swath/spherical-mesh or CRS fallback is implied.

## Large shared grids

| Family | Scale | Adapter | Setup mean s | Apply mean s | Total mean s | RMSE | Finite |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| gaussian | 512 | xarray_axes | 0.00142 | 0.01592 | 0.01735 | 4.08e-06 | 100.00% |
| gaussian | 512 | xarray_regrid_conservative | 0.00213 | 0.14793 | 0.15006 | 1.05e-05 | 100.00% |
| gaussian | 512 | xarray_regrid_linear | 0.00223 | 0.03746 | 0.03968 | 4.08e-06 | 100.00% |
| gaussian | 512 | xarray_regrid_nearest | 0.00159 | 0.02453 | 0.02611 | 0.0013 | 100.00% |
| gaussian | 1024 | xarray_axes | 0.00408 | 0.06199 | 0.06607 | 1.02e-06 | 100.00% |
| gaussian | 1024 | xarray_regrid_conservative | 0.00211 | 0.49842 | 0.50053 | 2.65e-06 | 100.00% |
| gaussian | 1024 | xarray_regrid_linear | 0.00159 | 0.07518 | 0.07677 | 1.02e-06 | 100.00% |
| gaussian | 1024 | xarray_regrid_nearest | 0.00179 | 0.04658 | 0.04837 | 0.000653 | 100.00% |
| rectilinear | 512 | xarray_axes | 0.00088 | 0.01656 | 0.01744 | 7.87e-07 | 100.00% |
| rectilinear | 512 | xarray_regrid_conservative | 0.00179 | 0.06712 | 0.06891 | 6.73e-05 | 100.00% |
| rectilinear | 512 | xarray_regrid_linear | 0.00189 | 0.02064 | 0.02252 | 7.87e-07 | 100.00% |
| rectilinear | 512 | xarray_regrid_nearest | 0.00189 | 0.01449 | 0.01638 | 0.000323 | 100.00% |
| rectilinear | 1024 | xarray_axes | 0.00101 | 0.03175 | 0.03275 | 1.96e-07 | 100.00% |
| rectilinear | 1024 | xarray_regrid_conservative | 0.00214 | 0.20849 | 0.21063 | 3.35e-05 | 100.00% |
| rectilinear | 1024 | xarray_regrid_linear | 0.00164 | 0.05938 | 0.06103 | 1.96e-07 | 100.00% |
| rectilinear | 1024 | xarray_regrid_nearest | 0.00160 | 0.01946 | 0.02106 | 0.000161 | 100.00% |

## Chunked arrays

All added chunked outputs matched their own eager references exactly, including finite masks, across all three repetitions. This does not establish equivalence between different algorithms. Conservative retained spatial output chunks; linear and nearest rechunked. Runtime warnings for invalid divide were observed during conservative computation around missing cells; completed output/mask comparisons still matched the reference. Raw output chunks and task layers are retained.

| Method | Input layout | Graph median s | Compute median s | Tasks | Max finite difference | Mask mismatches |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| xarray_regrid_conservative | 1×128×128 | 0.0388 | 0.3354 | 993 | 0.0 | 0 |
| xarray_regrid_conservative | 1×256×256 | 0.0369 | 0.1073 | 249 | 0.0 | 0 |
| xarray_regrid_conservative | 4×512×512 | 0.0372 | 0.0609 | 19 | 0.0 | 0 |
| xarray_regrid_linear | 1×128×128 | 0.0212 | 0.3249 | 2248 | 0.0 | 0 |
| xarray_regrid_linear | 1×256×256 | 0.0132 | 0.0833 | 408 | 0.0 | 0 |
| xarray_regrid_linear | 4×512×512 | 0.0126 | 0.0305 | 21 | 0.0 | 0 |
| xarray_regrid_nearest | 1×128×128 | 0.0214 | 0.2940 | 2248 | 0.0 | 0 |
| xarray_regrid_nearest | 1×256×256 | 0.0143 | 0.0718 | 408 | 0.0 | 0 |
| xarray_regrid_nearest | 4×512×512 | 0.0137 | 0.0133 | 21 | 0.0 | 0 |

## Targeted controls and usability

### closed_global_integral

Status: completed. A returned output is not a correctness verdict.

```json
{
  "grid": "rectilinear",
  "engine_version": "0.4.2",
  "source_shape": [
    36,
    72
  ],
  "target_shape": [
    18,
    36
  ],
  "finite_fraction": 1.0,
  "relative_integral_error": 0.0,
  "source_integral": 25.132741228718345,
  "target_integral": 25.132741228718345,
  "flags": [],
  "note": "Closed global meridian/parallel cells, sphere radius one, complete coverage. Values are treated as cell means; this validates this geometry, not ESMF great-circle equivalence."
}
```

### categorical_coarsening_unnamed_input

Status: error. A returned output is not a correctness verdict.

```json
{
  "grid": "rectilinear",
  "engine_version": "0.4.2",
  "error": "ValueError('Cannot group by unnamed DataArrays.')",
  "traceback": "Traceback (most recent call last):\n  File \"/workspace/regridding-benchmarks/xarray_regrid_controls.py\", line 15, in record\n    try:row.update(func(),status='completed')\n                   ^^^^^^\n  File \"/workspace/regridding-benchmarks/xarray_regrid_controls.py\", line 40, in <lambda>\n    record('xarray_regrid_most_common','categorical_coarsening_unnamed_input',lambda:mode(False))\n                                                                                     ^^^^^^^^^^^\n  File \"/workspace/regridding-benchmarks/xarray_regrid_controls.py\", line 30, in mode\n    out=a.regrid.most_common(dst,values=np.array([0,1]),fill_value=-1)\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/workspace/geospatial-benchmarks/.venv/lib/python3.12/site-packages/xarray_regrid/regrid.py\", line 176, in most_common\n    return flox_reduce.compute_mode(\n           ^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/workspace/geospatial-benchmarks/.venv/lib/python3.12/site-packages/xarray_regrid/methods/flox_reduce.py\", line 174, in compute_mode\n    result: xr.DataArray = flox.xarray.xarray_reduce(\n                           ^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/workspace/geospatial-benchmarks/.venv/lib/python3.12/site-packages/flox/xarray.py\", line 226, in xarray_reduce\n    raise ValueError(\"Cannot group by unnamed DataArrays.\")\nValueError: Cannot group by unnamed DataArrays.\n"
}
```

### categorical_coarsening_no_ties

Status: completed. A returned output is not a correctness verdict.

```json
{
  "grid": "rectilinear",
  "engine_version": "0.4.2",
  "source_shape": [
    4,
    4
  ],
  "target_shape": [
    2,
    2
  ],
  "output": [
    [
      1,
      1
    ],
    [
      1,
      1
    ]
  ],
  "finite_fraction": 1.0,
  "max_error": 0.0,
  "flags": [],
  "note": "Count-based mode on equally spaced 2\u00d72 source blocks with no ties. Does not test area-weighted mode; version 0.4.2 documents nondeterministic ties."
}
```

### large_integer_ids_native

Status: completed. A returned output is not a correctness verdict.

```json
{
  "grid": "rectilinear",
  "engine_version": "0.4.2",
  "input_dtype": "int64",
  "output_dtype": "float64",
  "input_ids": [
    9007199254740993,
    9007199254740995
  ],
  "decoded_ids": [
    [
      9007199254740992,
      9007199254740996
    ],
    [
      9007199254740992,
      9007199254740996
    ]
  ],
  "integer_id_mismatches": 4,
  "flags": [
    "integer_precision_loss"
  ],
  "note": "Probe native nearest preservation of IDs above 2^53; a returned output is not a correctness verdict."
}
```

### large_integer_ids_compact_codes

Status: completed. A returned output is not a correctness verdict.

```json
{
  "grid": "rectilinear",
  "engine_version": "0.4.2",
  "input_dtype": "int64",
  "output_dtype": "float64",
  "input_ids": [
    9007199254740993,
    9007199254740995
  ],
  "decoded_ids": [
    [
      9007199254740993,
      9007199254740995
    ],
    [
      9007199254740993,
      9007199254740995
    ]
  ],
  "integer_id_mismatches": 0,
  "flags": [],
  "note": "Compact-code output is decoded through the original int64 lookup."
}
```

The malformed nonseparable bad-latitude small probes are rejected by our adapter before conversion to 1-D coordinates; those errors do not measure library validation. Linear/conservative categorical probes produce fractional labels as expected for inappropriate class methods. Nearest preserves binary class membership but does not guarantee exact class-boundary accuracy or large integer precision. The mode control tests count-based coarsening with no ties; 0.4.2 documents nondeterministic ties, so no deterministic-tie support is claimed.

## Reproduce only this extension

Install requirements-python.lock into the documented .venv; acceleration dependencies are pinned without upgrading the previous environment.

```sh
.venv/bin/python run_large.py --scales 512 1024 --repeats 3 --only xarray_regrid_linear xarray_regrid_nearest xarray_regrid_conservative xarray_axes
for method in linear nearest conservative; do
  .venv/bin/python chunked_bench.py xarray_regrid_${method} rectilinear
  .venv/bin/python suite.py xarray_regrid_${method}
done
.venv/bin/python xarray_regrid_controls.py
.venv/bin/python chunked_combine.py
.venv/bin/python summarize_large.py
.venv/bin/python build_pages.py
```

Run profiles serially. Set BENCH_ENV_ROOT when the environments are outside the checkout. See the lock files, raw per-profile JSON, shared-grid report, chunked report, guide and external comparison for scope and evidence.
