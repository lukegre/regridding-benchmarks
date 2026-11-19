"""Read the verified NOAA coastal SST export in native grid order."""


def coastal_field(path, np, pd):
    data = pd.read_csv(path, skiprows=[1])
    if list(data.columns) != ["time", "latitude", "longitude", "analysed_sst", "mask"]:
        raise ValueError("Unexpected MUR CSV columns")
    lat, lon = np.unique(data.latitude), np.unique(data.longitude)
    if (len(data) != 401 * 401 or len(lat) != 401 or len(lon) != 401
            or not (data.time == "2020-01-01T09:00:00Z").all()):
        raise ValueError("Unexpected MUR grid shape or timestamp")
    yy, xx = np.meshgrid(lat, lon, indexing="ij")
    np.testing.assert_array_equal(data.latitude.to_numpy(), yy.ravel())
    np.testing.assert_array_equal(data.longitude.to_numpy(), xx.ravel())
    values = data.analysed_sst.to_numpy().reshape(401, 401)
    flags = data["mask"].to_numpy().reshape(values.shape)
    wet = np.isfinite(values) & ((flags & 1) != 0) & ((flags & 26) == 0)
    return lat, lon, values, wet
