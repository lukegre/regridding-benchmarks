# Larger shared-grid regridding benchmarks

Recorded 426 repetitions across 142 successful grid/size/method profiles; 4 unsuccessful or incomplete profiles are retained in the raw JSON.

**[Interactive report](https://lukegre.github.io/regridding-benchmarks/#large-timings)** · [Per-repeat CSV](large_results/measurements.csv) · [Full results](large_results/combined.json)

## Protocol

- Fixed shared source/destination geometries and scalar values within each grid/size profile; canonical hashes are verified before aggregation. Lossless native-format, longitude and storage-order adaptations are allowed.
- Common 512 and 1024 scales across packages, plus a common 4096×4096 tier for all four CRS adapters. No per-package size tuning or padded execution time.
- Three serial repetitions, one thread, two-vCPU / 8-GiB execution quota. Imports, small warmup, fixture generation and accuracy checks are outside the timers.
- Setup and eager application are measured separately. Fused interfaces can build geometry/weights during application. CDO/Tempest/NCO native commands include process launch and native file I/O; Python file preparation/read costs are separately recorded.
- MIR repeats use fresh processes and fresh cache directories. Original cached-call observations remain in `large_results/cache_controls/`.
- Both WGS84 → Swiss LV95 and WGS84 → Web Mercator are included. Pure coordinate transforms are a separate comparison group from raster reprojection.
- Reported values are arithmetic means and observed min/max of three runs, not confidence intervals. Different numerical kernels are not interchangeable.

## xarray-regrid extension

xarray-regrid 0.4.2 adds linear, nearest and conservative profiles on the existing rectilinear/full Gaussian grids. The xarray_axes control uses 1-D target coordinates instead of the historical xarray 2-D query arrays, without changing physical grids or values. Its public accessor constructs machinery/weights inside application; conservative meridian/parallel cells differ from ESMF great-circle cells. See [extension details](XARRAY_REGRID_REPORT.md).

## Profile geometry

| Test | Scale | Source cells | Target cells |
| --- | ---: | ---: | ---: |
| crs_4326_to_2056 | 512 | 262,144 | 262,144 |
| crs_4326_to_2056__coordinates | 512 | 262,144 | 262,144 |
| crs_4326_to_2056 | 1024 | 1,048,576 | 1,048,576 |
| crs_4326_to_2056__coordinates | 1024 | 1,048,576 | 1,048,576 |
| crs_4326_to_2056 | 4096 | 16,777,216 | 16,777,216 |
| crs_4326_to_2056__coordinates | 4096 | 16,777,216 | 16,777,216 |
| crs_4326_to_3857 | 512 | 262,144 | 262,144 |
| crs_4326_to_3857__coordinates | 512 | 262,144 | 262,144 |
| crs_4326_to_3857 | 1024 | 1,048,576 | 1,048,576 |
| crs_4326_to_3857__coordinates | 1024 | 1,048,576 | 1,048,576 |
| crs_4326_to_3857 | 4096 | 16,777,216 | 16,777,216 |
| crs_4326_to_3857__coordinates | 4096 | 16,777,216 | 16,777,216 |
| gaussian | 512 | 524,288 | 465,920 |
| gaussian | 1024 | 2,097,152 | 1,865,728 |
| healpix | 512 | 786,432 | 465,920 |
| healpix | 1024 | 3,145,728 | 1,865,728 |
| icosahedral | 512 | 81,920 | 465,920 |
| icosahedral | 1024 | 327,680 | 1,865,728 |
| rectilinear | 512 | 262,144 | 262,144 |
| rectilinear | 1024 | 1,048,576 | 1,048,576 |
| roms | 512 | 262,144 | 262,144 |
| roms | 1024 | 1,048,576 | 1,048,576 |
| roms_mesh | 512 | 522,242 | 522,242 |
| roms_mesh | 1024 | 2,093,058 | 2,093,058 |
| satellite_swath | 512 | 524,288 | 524,288 |
| satellite_swath | 1024 | 2,097,152 | 2,097,152 |

## Timings

Times are seconds. `fused` means setup is API preparation and some weight/geometry work remains in application. NCO setup uses TempestRemap-generated weights.

| Test | Scale | Method | Mode | Setup mean | Apply mean | Total mean | Total range | RMSE | Finite |
| --- | ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: |
| crs_4326_to_2056 | 512 | odc_geo | fused | 0.0035 | 0.0420 | 0.0455 | 0.0420–0.0475 | 1.16e-05 | 95.21% |
| crs_4326_to_2056__coordinates | 512 | pyproj | fused | 0.0061 | 0.1444 | 0.1505 | 0.1418–0.1620 | 1.99e-08° round-trip | 100.00% |
| crs_4326_to_2056 | 512 | rasterio | fused | 0.0001 | 0.0273 | 0.0273 | 0.0261–0.0285 | 1.16e-05 | 95.21% |
| crs_4326_to_2056 | 512 | rioxarray | fused | 0.0041 | 0.0336 | 0.0377 | 0.0329–0.0414 | 1.16e-05 | 95.21% |
| crs_4326_to_2056 | 1024 | odc_geo | fused | 0.0087 | 0.1707 | 0.1794 | 0.1547–0.2004 | 1.37e-05 | 95.21% |
| crs_4326_to_2056__coordinates | 1024 | pyproj | fused | 0.0064 | 0.5287 | 0.5350 | 0.5145–0.5760 | 1.99e-08° round-trip | 100.00% |
| crs_4326_to_2056 | 1024 | rasterio | fused | 0.0002 | 0.0998 | 0.1000 | 0.0959–0.1028 | 1.37e-05 | 95.21% |
| crs_4326_to_2056 | 1024 | rioxarray | fused | 0.0099 | 0.1603 | 0.1702 | 0.1391–0.2273 | 1.37e-05 | 95.21% |
| crs_4326_to_2056 | 4096 | odc_geo | fused | 0.0894 | 3.5892 | 3.6786 | 3.5882–3.7249 | 1.46e-05 | 95.19% |
| crs_4326_to_2056__coordinates | 4096 | pyproj | fused | 0.0063 | 8.7457 | 8.7521 | 8.4600–9.2344 | 1.99e-08° round-trip | 100.00% |
| crs_4326_to_2056 | 4096 | rasterio | fused | 0.0002 | 2.1621 | 2.1622 | 2.0302–2.4156 | 1.46e-05 | 95.19% |
| crs_4326_to_2056 | 4096 | rioxarray | fused | 0.0964 | 1.9554 | 2.0518 | 2.0107–2.0849 | 1.46e-05 | 95.19% |
| crs_4326_to_3857 | 512 | odc_geo | fused | 0.0033 | 0.0321 | 0.0354 | 0.0304–0.0407 | 2.18e-06 | 100.00% |
| crs_4326_to_3857__coordinates | 512 | pyproj | fused | 0.0006 | 0.0279 | 0.0285 | 0.0264–0.0299 | 1.6e-14° round-trip | 100.00% |
| crs_4326_to_3857 | 512 | rasterio | fused | 0.0001 | 0.0174 | 0.0175 | 0.0165–0.0186 | 2.18e-06 | 100.00% |
| crs_4326_to_3857 | 512 | rioxarray | fused | 0.0029 | 0.0211 | 0.0240 | 0.0230–0.0249 | 2.18e-06 | 100.00% |
| crs_4326_to_3857 | 1024 | odc_geo | fused | 0.0085 | 0.1175 | 0.1260 | 0.1235–0.1286 | 3.23e-07 | 100.00% |
| crs_4326_to_3857__coordinates | 1024 | pyproj | fused | 0.0006 | 0.1185 | 0.1191 | 0.1112–0.1307 | 1.69e-14° round-trip | 100.00% |
| crs_4326_to_3857 | 1024 | rasterio | fused | 0.0001 | 0.0675 | 0.0676 | 0.0634–0.0719 | 3.23e-07 | 100.00% |
| crs_4326_to_3857 | 1024 | rioxarray | fused | 0.0053 | 0.0769 | 0.0822 | 0.0727–0.0872 | 3.23e-07 | 100.00% |
| crs_4326_to_3857 | 4096 | odc_geo | fused | 0.0871 | 1.7948 | 1.8819 | 1.8453–1.9135 | 4.23e-09 | 100.00% |
| crs_4326_to_3857__coordinates | 4096 | pyproj | fused | 0.0007 | 1.8752 | 1.8759 | 1.8081–1.9475 | 1.69e-14° round-trip | 100.00% |
| crs_4326_to_3857 | 4096 | rasterio | fused | 0.0001 | 1.2321 | 1.2322 | 1.1910–1.2694 | 4.23e-09 | 100.00% |
| crs_4326_to_3857 | 4096 | rioxarray | fused | 0.0889 | 1.2985 | 1.3873 | 1.3625–1.4217 | 4.23e-09 | 100.00% |
| gaussian | 512 | cdo_bilinear | split | 0.6176 | 0.1155 | 0.7331 | 0.6855–0.8197 | 4.08e-06 | 100.00% |
| gaussian | 512 | cdo_conservative | split | 6.1821 | 0.1752 | 6.3573 | 6.1899–6.4825 | 5.99e-06 | 100.00% |
| gaussian | 512 | cdo_nearest | split | 0.6721 | 0.1075 | 0.7797 | 0.6715–0.8875 | 0.0013 | 100.00% |
| gaussian | 512 | earthkit_mir | fused | 0.0052 | 3.5328 | 3.5380 | 3.4324–3.6161 | 4.08e-06 | 100.00% |
| gaussian | 512 | pyresample_gauss | split | 0.7434 | 0.0969 | 0.8403 | 0.7667–0.8826 | 0.00036 | 100.00% |
| gaussian | 512 | pyresample_nearest | split | 0.3779 | 0.0089 | 0.3867 | 0.3794–0.3962 | 0.0013 | 100.00% |
| gaussian | 512 | scipy | fused | 0.0026 | 0.0384 | 0.0410 | 0.0366–0.0481 | 4.08e-06 | 100.00% |
| gaussian | 512 | xarray | fused | 0.0016 | 0.0497 | 0.0513 | 0.0489–0.0556 | 4.08e-06 | 100.00% |
| gaussian | 512 | xarray_axes | fused | 0.0014 | 0.0159 | 0.0173 | 0.0162–0.0194 | 4.08e-06 | 100.00% |
| gaussian | 512 | xarray_regrid_conservative | fused | 0.0021 | 0.1479 | 0.1501 | 0.1341–0.1694 | 1.05e-05 | 100.00% |
| gaussian | 512 | xarray_regrid_linear | fused | 0.0022 | 0.0375 | 0.0397 | 0.0371–0.0448 | 4.08e-06 | 100.00% |
| gaussian | 512 | xarray_regrid_nearest | fused | 0.0016 | 0.0245 | 0.0261 | 0.0213–0.0305 | 0.0013 | 100.00% |
| gaussian | 512 | xesmf_bilinear | split | 17.6662 | 0.1751 | 17.8412 | 16.8060–18.6989 | 4.08e-06 | 100.00% |
| gaussian | 512 | xesmf_conservative | split | 24.3635 | 0.0955 | 24.4590 | 23.2142–26.3620 | 5.99e-06 | 100.00% |
| gaussian | 512 | xesmf_nearest_s2d | split | 3.9830 | 0.0493 | 4.0322 | 3.7343–4.2263 | 0.0013 | 100.00% |
| gaussian | 1024 | cdo_bilinear | split | 2.8170 | 0.4053 | 3.2223 | 3.0487–3.3486 | 1.02e-06 | 100.00% |
| gaussian | 1024 | cdo_conservative | split | 24.7359 | 0.3443 | 25.0801 | 24.7476–25.6700 | 1.51e-06 | 100.00% |
| gaussian | 1024 | cdo_nearest | split | 2.2449 | 0.1944 | 2.4392 | 2.3821–2.5114 | 0.000653 | 100.00% |
| gaussian | 1024 | earthkit_mir | fused | 0.0263 | 16.2208 | 16.2471 | 15.1203–17.2200 | 1.02e-06 | 100.00% |
| gaussian | 1024 | pyresample_gauss | split | 3.8097 | 0.4689 | 4.2786 | 3.2824–5.0532 | 0.0002 | 100.00% |
| gaussian | 1024 | pyresample_nearest | split | 1.5885 | 0.0333 | 1.6218 | 1.5764–1.6778 | 0.000653 | 100.00% |
| gaussian | 1024 | scipy | fused | 0.0160 | 0.1361 | 0.1521 | 0.1489–0.1584 | 1.02e-06 | 100.00% |
| gaussian | 1024 | xarray | fused | 0.0036 | 0.1809 | 0.1845 | 0.1771–0.1932 | 1.02e-06 | 100.00% |
| gaussian | 1024 | xarray_axes | fused | 0.0041 | 0.0620 | 0.0661 | 0.0626–0.0720 | 1.02e-06 | 100.00% |
| gaussian | 1024 | xarray_regrid_conservative | fused | 0.0021 | 0.4984 | 0.5005 | 0.4771–0.5203 | 2.65e-06 | 100.00% |
| gaussian | 1024 | xarray_regrid_linear | fused | 0.0016 | 0.0752 | 0.0768 | 0.0708–0.0861 | 1.02e-06 | 100.00% |
| gaussian | 1024 | xarray_regrid_nearest | fused | 0.0018 | 0.0466 | 0.0484 | 0.0449–0.0510 | 0.000653 | 100.00% |
| gaussian | 1024 | xesmf_bilinear | split | 83.5311 | 0.7507 | 84.2818 | 80.0440–91.0428 | 1.02e-06 | 100.00% |
| gaussian | 1024 | xesmf_conservative | split | 113.0621 | 0.5963 | 113.6585 | 101.5799–119.9830 | 1.51e-06 | 100.00% |
| gaussian | 1024 | xesmf_nearest_s2d | split | 20.9952 | 0.1807 | 21.1759 | 20.5351–22.1827 | 0.000653 | 100.00% |
| healpix | 512 | astropy_healpix | split | 0.3581 | 0.0117 | 0.3698 | 0.3570–0.3787 | 3.67e-06 | 100.00% |
| healpix | 512 | cdo_bilinear | split | 0.7820 | 0.1276 | 0.9096 | 0.7677–1.1001 | 3.67e-06 | 100.00% |
| healpix | 512 | cdo_nearest | split | 1.0329 | 0.1195 | 1.1524 | 0.9047–1.4566 | 0.000952 | 100.00% |
| healpix | 512 | earthkit_mir | fused | 0.0024 | 4.7162 | 4.7185 | 4.3133–5.4255 | 2.34e-06 | 100.00% |
| healpix | 512 | healpy | split | 0.0678 | 0.0093 | 0.0771 | 0.0755–0.0799 | 3.67e-06 | 100.00% |
| healpix | 512 | pyresample_gauss | split | 0.8398 | 0.1275 | 0.9673 | 0.8933–1.0689 | 0.000427 | 100.00% |
| healpix | 512 | pyresample_nearest | split | 0.4333 | 0.0085 | 0.4418 | 0.4150–0.4559 | 0.000952 | 100.00% |
| healpix | 1024 | astropy_healpix | split | 1.3577 | 0.0391 | 1.3967 | 1.3350–1.4336 | 9.28e-07 | 100.00% |
| healpix | 1024 | cdo_bilinear | split | 3.0112 | 0.3775 | 3.3887 | 3.1385–3.5465 | 9.28e-07 | 100.00% |
| healpix | 1024 | cdo_nearest | split | 3.2998 | 0.2009 | 3.5007 | 3.2918–3.6199 | 0.000489 | 100.00% |
| healpix | 1024 | earthkit_mir | fused | 0.0094 | 18.1449 | 18.1543 | 16.8605–19.8916 | 5.97e-07 | 100.00% |
| healpix | 1024 | healpy | split | 0.2258 | 0.0398 | 0.2656 | 0.2620–0.2679 | 9.28e-07 | 100.00% |
| healpix | 1024 | pyresample_gauss | split | 3.4285 | 0.4680 | 3.8965 | 3.8491–3.9290 | 0.000232 | 100.00% |
| healpix | 1024 | pyresample_nearest | split | 1.7509 | 0.0287 | 1.7796 | 1.7252–1.8873 | 0.00049 | 100.00% |
| icosahedral | 512 | cdo_conservative | split | 4.3778 | 0.1278 | 4.5056 | 4.4802–4.5445 | 0.00248 | 100.00% |
| icosahedral | 512 | cdo_nearest | split | 0.3340 | 0.0691 | 0.4032 | 0.3789–0.4510 | 0.00357 | 100.00% |
| icosahedral | 512 | esmpy | split | 15.7161 | 0.0052 | 15.7213 | 14.6864–16.8872 | 0.00248 | 100.00% |
| icosahedral | 512 | pyresample_gauss | split | 0.5930 | 0.1544 | 0.7474 | 0.6719–0.8845 | 0.000754 | 100.00% |
| icosahedral | 512 | pyresample_nearest | split | 0.2290 | 0.0057 | 0.2347 | 0.2156–0.2654 | 0.00357 | 100.00% |
| icosahedral | 512 | uxarray | fused | 0.2352 | 0.8767 | 1.1118 | 1.0776–1.1502 | 0.00357 | 100.00% |
| icosahedral | 1024 | cdo_conservative | split | 18.7103 | 0.2768 | 18.9870 | 18.6394–19.2372 | 0.00124 | 100.00% |
| icosahedral | 1024 | cdo_nearest | split | 1.5949 | 0.1712 | 1.7661 | 1.5933–1.9773 | 0.00178 | 100.00% |
| icosahedral | 1024 | esmpy | split | 77.8592 | 0.0463 | 77.9055 | 71.2952–83.1154 | 0.00124 | 100.00% |
| icosahedral | 1024 | pyresample_gauss | split | 2.3318 | 0.5958 | 2.9275 | 2.6628–3.3525 | 0.000728 | 100.00% |
| icosahedral | 1024 | pyresample_nearest | split | 0.8981 | 0.0201 | 0.9181 | 0.8935–0.9314 | 0.00178 | 100.00% |
| icosahedral | 1024 | uxarray | fused | 1.1032 | 3.9153 | 5.0186 | 4.4821–5.6647 | 0.00178 | 100.00% |
| rectilinear | 512 | cdo_bilinear | split | 0.4076 | 0.0956 | 0.5032 | 0.4580–0.5740 | 7.87e-07 | 100.00% |
| rectilinear | 512 | cdo_conservative | split | 3.1064 | 0.1145 | 3.2209 | 2.9606–3.3517 | 6.73e-05 | 100.00% |
| rectilinear | 512 | cdo_nearest | split | 0.3009 | 0.0706 | 0.3715 | 0.3325–0.4421 | 0.000323 | 100.00% |
| rectilinear | 512 | iris | split | 11.1536 | 0.0083 | 11.1619 | 10.1058–12.7523 | 6.73e-05 | 100.00% |
| rectilinear | 512 | pyresample_gauss | split | 0.3897 | 0.0550 | 0.4447 | 0.4179–0.4668 | 0.000141 | 100.00% |
| rectilinear | 512 | pyresample_nearest | split | 0.1631 | 0.0035 | 0.1666 | 0.1618–0.1705 | 0.000323 | 100.00% |
| rectilinear | 512 | scipy | fused | 0.0013 | 0.0257 | 0.0269 | 0.0212–0.0352 | 7.87e-07 | 100.00% |
| rectilinear | 512 | xarray | fused | 0.0008 | 0.0353 | 0.0361 | 0.0279–0.0467 | 7.87e-07 | 100.00% |
| rectilinear | 512 | xarray_axes | fused | 0.0009 | 0.0166 | 0.0174 | 0.0113–0.0230 | 7.87e-07 | 100.00% |
| rectilinear | 512 | xarray_regrid_conservative | fused | 0.0018 | 0.0671 | 0.0689 | 0.0599–0.0855 | 6.73e-05 | 100.00% |
| rectilinear | 512 | xarray_regrid_linear | fused | 0.0019 | 0.0206 | 0.0225 | 0.0202–0.0247 | 7.87e-07 | 100.00% |
| rectilinear | 512 | xarray_regrid_nearest | fused | 0.0019 | 0.0145 | 0.0164 | 0.0140–0.0196 | 0.000323 | 100.00% |
| rectilinear | 512 | xesmf_bilinear | split | 8.6324 | 0.1237 | 8.7561 | 7.8955–9.5604 | 7.8e-07 | 100.00% |
| rectilinear | 512 | xesmf_conservative | split | 11.6960 | 0.0960 | 11.7920 | 10.7258–13.3125 | 6.73e-05 | 100.00% |
| rectilinear | 512 | xesmf_nearest_s2d | split | 2.3757 | 0.0323 | 2.4081 | 2.1313–2.6564 | 0.000323 | 100.00% |
| rectilinear | 1024 | cdo_bilinear | split | 1.7467 | 0.2229 | 1.9696 | 1.8653–2.1094 | 1.96e-07 | 100.00% |
| rectilinear | 1024 | cdo_conservative | split | 12.6814 | 0.2671 | 12.9486 | 12.3973–13.4834 | 3.35e-05 | 100.00% |
| rectilinear | 1024 | cdo_nearest | split | 1.1010 | 0.2648 | 1.3659 | 1.3079–1.4116 | 0.000161 | 100.00% |
| rectilinear | 1024 | iris | split | 61.7230 | 0.0642 | 61.7872 | 52.6941–67.8800 | 3.35e-05 | 100.00% |
| rectilinear | 1024 | pyresample_gauss | split | 1.5726 | 0.2742 | 1.8468 | 1.7150–2.0451 | 7.12e-05 | 100.00% |
| rectilinear | 1024 | pyresample_nearest | split | 0.7321 | 0.0138 | 0.7459 | 0.7069–0.7682 | 0.000161 | 100.00% |
| rectilinear | 1024 | scipy | fused | 0.0047 | 0.0735 | 0.0782 | 0.0675–0.0929 | 1.96e-07 | 100.00% |
| rectilinear | 1024 | xarray | fused | 0.0008 | 0.0951 | 0.0958 | 0.0846–0.1095 | 1.96e-07 | 100.00% |
| rectilinear | 1024 | xarray_axes | fused | 0.0010 | 0.0317 | 0.0328 | 0.0275–0.0381 | 1.96e-07 | 100.00% |
| rectilinear | 1024 | xarray_regrid_conservative | fused | 0.0021 | 0.2085 | 0.2106 | 0.1691–0.2625 | 3.35e-05 | 100.00% |
| rectilinear | 1024 | xarray_regrid_linear | fused | 0.0016 | 0.0594 | 0.0610 | 0.0476–0.0823 | 1.96e-07 | 100.00% |
| rectilinear | 1024 | xarray_regrid_nearest | fused | 0.0016 | 0.0195 | 0.0211 | 0.0203–0.0224 | 0.000161 | 100.00% |
| rectilinear | 1024 | xesmf_bilinear | split | 37.9897 | 0.4474 | 38.4370 | 36.9055–41.0559 | 1.95e-07 | 100.00% |
| rectilinear | 1024 | xesmf_conservative | split | 54.8396 | 0.4253 | 55.2649 | 53.4222–57.8141 | 3.35e-05 | 100.00% |
| rectilinear | 1024 | xesmf_nearest_s2d | split | 11.9923 | 0.0993 | 12.0916 | 11.9844–12.1781 | 0.000161 | 100.00% |
| roms | 512 | cdo_bilinear | split | 0.3891 | 0.0900 | 0.4791 | 0.4494–0.5200 | 7.92e-07 | 100.00% |
| roms | 512 | cdo_conservative | split | 3.3937 | 0.1073 | 3.5010 | 3.3567–3.6425 | 6.48e-05 | 100.00% |
| roms | 512 | cdo_nearest | split | 0.3271 | 0.0719 | 0.3991 | 0.3350–0.4694 | 0.000321 | 100.00% |
| roms | 512 | pyresample_gauss | split | 0.3975 | 0.0739 | 0.4714 | 0.4435–0.4894 | 0.000122 | 100.00% |
| roms | 512 | pyresample_nearest | split | 0.1757 | 0.0041 | 0.1798 | 0.1759–0.1823 | 0.000321 | 100.00% |
| roms | 512 | xesmf_bilinear | split | 8.9574 | 0.1507 | 9.1081 | 7.9177–11.1943 | 7.85e-07 | 100.00% |
| roms | 512 | xesmf_conservative | split | 13.0165 | 0.1120 | 13.1285 | 12.6595–13.8408 | 6.48e-05 | 100.00% |
| roms | 512 | xesmf_nearest_s2d | split | 2.3767 | 0.0484 | 2.4250 | 2.2502–2.5456 | 0.000321 | 100.00% |
| roms | 1024 | cdo_bilinear | split | 1.7649 | 0.2508 | 2.0158 | 1.7696–2.2645 | 1.98e-07 | 100.00% |
| roms | 1024 | cdo_conservative | split | 13.4321 | 0.2784 | 13.7104 | 13.3885–14.0482 | 3.24e-05 | 100.00% |
| roms | 1024 | cdo_nearest | split | 1.1542 | 0.1494 | 1.3036 | 1.2333–1.3782 | 0.00016 | 100.00% |
| roms | 1024 | pyresample_gauss | split | 1.6549 | 0.2531 | 1.9080 | 1.8397–1.9676 | 6.19e-05 | 100.00% |
| roms | 1024 | pyresample_nearest | split | 0.7677 | 0.0183 | 0.7860 | 0.7134–0.8506 | 0.00016 | 100.00% |
| roms | 1024 | xesmf_bilinear | split | 35.4100 | 0.6028 | 36.0128 | 35.4332–37.0968 | 1.96e-07 | 100.00% |
| roms | 1024 | xesmf_conservative | split | 58.1114 | 0.5594 | 58.6707 | 57.2623–60.5718 | 3.24e-05 | 100.00% |
| roms | 1024 | xesmf_nearest_s2d | split | 12.5710 | 0.1647 | 12.7357 | 12.1892–13.5369 | 0.00016 | 100.00% |
| roms_mesh | 512 | xugrid | split | 8.2935 | 0.0203 | 8.3138 | 8.2591–8.3978 | 1.68e-09 | 100.00% |
| roms_mesh | 1024 | xugrid | split | 39.8800 | 0.0665 | 39.9466 | 38.0572–43.6905 | 3.01e-10 | 100.00% |
| satellite_swath | 512 | cdo_bilinear | split | 0.7292 | 0.1266 | 0.8558 | 0.8096–0.9413 | 4.49e-07 | 83.15% |
| satellite_swath | 512 | cdo_conservative | split | 6.5962 | 0.1582 | 6.7544 | 6.4045–6.9931 | 6.11e-05 | 83.33% |
| satellite_swath | 512 | cdo_nearest | split | 0.7082 | 0.1023 | 0.8105 | 0.7454–0.9233 | 0.00409 | 100.00% |
| satellite_swath | 512 | pyresample_gauss | split | 0.7158 | 0.1383 | 0.8541 | 0.7789–0.9610 | 0.00138 | 92.68% |
| satellite_swath | 512 | pyresample_nearest | split | 0.3652 | 0.0064 | 0.3716 | 0.3623–0.3827 | 0.00141 | 92.68% |
| satellite_swath | 512 | xesmf_bilinear | split | 15.0757 | 0.2164 | 15.2921 | 13.9905–17.6177 | 4.46e-07 | 83.15% |
| satellite_swath | 512 | xesmf_nearest_s2d | split | 5.2429 | 0.0627 | 5.3056 | 4.7568–5.5991 | 0.00409 | 100.00% |
| satellite_swath | 1024 | cdo_bilinear | split | 3.5098 | 0.3421 | 3.8520 | 3.5096–4.4746 | 1.12e-07 | 83.18% |
| satellite_swath | 1024 | cdo_conservative | split | 28.7992 | 0.6550 | 29.4542 | 27.6916–30.4520 | 3.04e-05 | 83.27% |
| satellite_swath | 1024 | cdo_nearest | split | 2.9709 | 0.2360 | 3.2069 | 2.8046–3.8950 | 0.00407 | 100.00% |
| satellite_swath | 1024 | pyresample_gauss | split | 3.1139 | 0.5427 | 3.6566 | 3.4707–3.9075 | 0.00137 | 92.70% |
| satellite_swath | 1024 | pyresample_nearest | split | 1.8776 | 0.0346 | 1.9123 | 1.8417–1.9707 | 0.00138 | 92.70% |
| satellite_swath | 1024 | xesmf_bilinear | split | 68.9153 | 0.9996 | 69.9149 | 67.3967–73.7889 | 1.11e-07 | 83.18% |
| satellite_swath | 1024 | xesmf_nearest_s2d | split | 39.2618 | 0.2542 | 39.5160 | 38.0919–41.1541 | 0.00407 | 100.00% |

## Limits

The synthetic swath has incomplete coverage of its rectangular destination. Nearest-neighbour methods may fill points outside the swath footprint; bilinear and conservative methods have different support and missing-value behavior. Accuracy and coverage must be assessed alongside timings. Conservative inputs are analytic centre samples, not exact cell averages. The Xugrid profile is a separate projected, face-centred triangular mesh workflow. These are CPU single-field benchmarks, not memory stress tests, MPI scaling tests, or complete ROMS vector/vertical remapping.

## Unsuccessful profiles

Four TempestRemap/NCO profiles exceeded the 300-second limit in GenerateOverlapMesh, before weight generation/application completed. NCO uses the same TempestRemap setup, so these are not independent interpolation failures. They characterize this SCRIP-converted regional-overlap workflow; they do not establish a universal package limit. No interpolation speed is claimed for these profiles.

- nco / icosahedral / 1024: error; GenerateOverlapMesh exceeded 300 seconds; no completed interpolation timing
- nco / icosahedral / 512: error; GenerateOverlapMesh exceeded 300 seconds; no completed interpolation timing
- tempest / icosahedral / 1024: error; GenerateOverlapMesh exceeded 300 seconds; no completed interpolation timing
- tempest / icosahedral / 512: error; GenerateOverlapMesh exceeded 300 seconds; no completed interpolation timing