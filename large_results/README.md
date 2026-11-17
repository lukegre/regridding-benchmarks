# Large timing tier

The original small adversarial records remain in `results/` and `all_results.*`.

Production timing profiles use shared 512 and 1024 scales (plus 4096 for all CRS adapters), three repetitions, one thread, and serial execution. `scale` controls each family's deterministic source/destination geometry; it is not a per-package calibration. Rectilinear and ROMS source/target shapes are n×n. Gaussian sources are n×2n; HEALPix NSIDE=n/2; icosahedral sources use subdivision log2(n)-3. Global destination coordinates use exactly the same aligned latitude/longitude raster across all packages, including MIR. CRS profiles use identical WGS84 source rasters and identical LV95/Web-Mercator destination rasters.

Within each family/scale, source geometry, destination geometry and scalar values have SHA-256 fingerprints. The fingerprints describe canonical inputs before lossless longitude wrapping, storage reordering and native mesh-format conversion. Match fingerprints and operation semantics before comparing times. Xugrid has a separate projected triangular-mesh profile, since its face-centred destination differs from a raster target.

`setup_seconds` and `apply_seconds` are recorded separately, with `total_seconds` their sum. Package imports, a small warmup and deterministic fixture generation are outside those timers. Each recorded repetition rebuilds the adapter. Fused APIs can do geometry and weights inside apply; `timing_mode` and `setup_note` make this explicit. Pure coordinate conversion is distinct from resampling values. CDO/Tempest/NCO command timings include native process launch and file I/O; Python input/output I/O is recorded separately and subtracted where possible. MIR uses a fresh process and fresh MIR_CACHE_PATH per production repeat after controls revealed global cache reuse. Cached controls remain in cache_controls/.

The roughly 10-second goal is a workload-size guide, not a padded timer or per-package fixed duration. Faster methods remain faster on the same input. There are no artificial repetitions inside a measured operation.

Files ending `__64.json` and smoke logs are development checks, not production performance observations. The runner supports resuming complete profile records and rerunning failures.
