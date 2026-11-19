# Legacy edition

[`archive/`](archive) contains the original runners, recorded results, and reports. The
registry adapters reuse its benchmark kernels. The original results manifest and edition
source manifest use paths relative to `archive/`. The exported edition retains those paths.

The GitHub Pages files remain in [`docs/`](../../docs) for the current URLs. To run the
original reproduction or report-generation scripts, use a separate checkout of
`e4a4d263877433859d14dd6c6d91924127dbd54c`. Those scripts can rewrite recorded outputs.
Use the registry CLI for new measurements and checkout-local legacy exports.

The source manifest pins the original checkout revision and SHA-256 hashes for the historical small, shared-grid, chunked and storage results, their logs and supporting artifacts, and the tool guide. `results-manifest.json` is the original checksum manifest; all 1,184 entries were verified against the checkout. `sources.manifest` also pins the other edition files. The current registry is an inventory of observed cases; it does not turn historical errors into expected rejections or establish numerical parity.

`regridding_benchmarks.legacy.build_edition(repo, output)` verifies both manifests and copies the original bytes to an empty output directory. `validate_edition(output)` verifies the copies and index references. `manifest.json` names the guide and index. Each record in `index.json` links to its original JSON file by relative `source` and RFC 6901 `pointer` (empty means the whole document). Summary files are retained but excluded from the index where they duplicate individual chunked records. Diagnostic and interrupted pilots are retained without treating them as completed timings. The output can be served as a static edition without benchmark libraries.

The edition preserves the historical platform and configuration files where recorded. Image digest, complete effective resource limits and complete engine versions are unknown; small-fixture hashes were not recorded. Timings are a separate historical series and must not be pooled with fresh runs. Old URLs and deployment redirects require a publication cutover.

The adapter calls the original small and shared-grid kernels, and executes the original chunked/storage experiments in scratch. Bounded smoke cases use a 32×32 chunked grid or 128×128 storage grid with one repeat; these are adaptations, not comparable performance measurements. Chunked and storage records describe an entire multi-layout or multi-repeat experiment, not a single fresh repeat. The small CDO and xESMF cases call the original kernels from an isolated worker. CDO writes only in the worker scratch and reports the command, file preparation and output read as one timing. xESMF records weight construction separately. Some historical native or diagnostic cases remain outside the executable adapters. The default-output xESMF diagnostic is preserved but is not a runnable case. Original runners have not been modified; their package-specific semantics and limitations remain applicable. No fixture-hash or numerical parity claim is made for the new runner until independently compared.

Migration checks with the Python 3.12 environment compared SciPy rectilinear smooth and constant, SciPy Gaussian with a missing-value hole, and xarray Gaussian smooth against the historical finite fractions and errors to an absolute tolerance of 1e-12. SciPy longitude controls with and without wrapping also match. Shared-grid 512 SciPy and xarray geometry hashes match and their numerical errors agree within 1e-12; generated value hashes differ on the current platform, so byte-identical fixture values are not claimed. Full xarray chunked and NetCDF storage protocols completed, and their finite-mask and value comparisons are gated; the bounded versions also pass. The standard profile includes selected 512-scale cases across rectilinear, Gaussian, swath, curvilinear and projected grids, plus full xarray chunked and storage protocols. Compiled and optional engines require their corresponding environments. The full chunked and storage protocols retain their internal three repetitions per runner sample.

In the local amd64 compatibility pilot, all eight selected shared-grid cases reproduced historical finite coverage and RMSE within the comparison tolerance. The recorded geometry hashes matched for CDO and SciPy rectilinear, pyresample swath, and xarray-regrid rectilinear. Some geometry and value hashes differed on the emulated runtime. The raw repeats retain both hashes and remain a separate series.

The small rectilinear CDO nearest and xESMF bilinear cases each ran three times in the amd64 image. Finite coverage, RMSE and maximum error matched the recorded historical values exactly for the compared samples.

Python longitude and xarray-regrid controls reuse only the numerical function bodies from the historical scripts, avoiding their top-level file writes. The unnamed xarray-regrid categorical control previously errored; this is an observed failure, not an expected rejection. Conservation, categorical mode and compact integer-code controls have method-specific gates.
