"""Compare file reads and controlled HTTP range reads for MUR Web Mercator tiles."""

import re
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from math import pi
from threading import Lock, Thread
from time import perf_counter

from .comparison import arrays_digest
from .io import sha256
from .mur import coastal_field


@contextmanager
def range_server(path):
    counters = {"range_requests": 0, "body_bytes": 0}
    counter_lock = Lock()
    size = path.stat().st_size

    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self):
            self.serve(body=False)

        def do_GET(self):
            self.serve(body=True)

        def log_message(self, format, *args):
            pass

        def serve(self, *, body):
            if self.path != "/sst.tif":
                self.send_error(404)
                return
            header = self.headers.get("Range")
            match = re.fullmatch(r"bytes=(\d+)-(\d*)", header or "")
            if header and not match:
                self.send_error(416)
                return
            start, end = (int(match[1]), min(int(match[2] or size), size - 1)) if match else (0, size - 1)
            if not 0 <= start <= end:
                self.send_error(416)
                return
            self.send_response(206 if match else 200)
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Accept-Ranges", "bytes")
            if match:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            if body:
                with path.open("rb") as stream:
                    stream.seek(start)
                    self.wfile.write(stream.read(end - start + 1))
                with counter_lock:
                    counters["range_requests"] += int(bool(match))
                    counters["body_bytes"] += end - start + 1

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        try:
            yield f"/vsicurl/http://127.0.0.1:{server.server_port}/sst.tif", counters
        finally:
            server.shutdown()
            thread.join()


def run(case, context):
    start = perf_counter()
    try:
        import numpy as np
        import pandas as pd
        import rasterio
        from rasterio.shutil import copy
        from rasterio.transform import from_bounds, from_origin
        from rasterio.warp import Resampling, reproject, transform_bounds
        from rasterio.windows import Window, from_bounds as source_window
    except ImportError as error:
        return {"status": "unavailable", "reason": str(error)}
    timings = {"imports": perf_counter() - start}

    start = perf_counter()
    lat, lon, values, wet = coastal_field(context["dataset_path"], np, pd)
    source = np.where(wet, values, np.nan).astype("float32")[::-1]
    affine = from_origin(lon[0] - 0.005, lat[-1] + 0.005, 0.01, 0.01)
    raw = context["scratch"] / "sst-raw.tif"
    cog = context["scratch"] / "sst.tif"
    with rasterio.open(raw, "w", driver="GTiff", height=source.shape[0], width=source.shape[1],
                       count=1, dtype=source.dtype, crs="EPSG:4326", transform=affine,
                       nodata=np.nan) as dataset:
        dataset.write(source, 1)
    copy(raw, cog, driver="COG", blocksize=128, compress="DEFLATE", overviews="NONE")
    timings["fixture"] = perf_counter() - start

    # XYZ tiles in EPSG:3857 use a square with half-width pi * WGS84 a.
    zoom, x, y = case["options"]["tile"]
    half = pi * 6378137
    width = 2 * half / (2 ** zoom)
    left, top = -half + x * width, half - y * width
    bounds = (left, top - width, left + width, top)
    target = from_bounds(*bounds, 256, 256)
    window = source_window(*transform_bounds("EPSG:3857", "EPSG:4326", *bounds), transform=affine)
    column, row = np.floor([window.col_off, window.row_off]).astype(int)
    last_column, last_row = np.ceil([window.col_off + window.width,
                                    window.row_off + window.height]).astype(int)
    padded = Window(column - 1, row - 1, last_column - column + 2, last_row - row + 2)
    region = padded.intersection(Window(0, 0, source.shape[1], source.shape[0]))
    region_affine = rasterio.windows.transform(region, affine)
    outputs = {}
    with range_server(cog) as (url, transfer):
        for mode, path in (("file", str(cog)), ("http", url)):
            start = perf_counter()
            with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", VSI_CACHE="FALSE",
                              CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
                with rasterio.open(path) as dataset:
                    field = dataset.read(1, window=region)
                read_finished = perf_counter()
                result = np.full((256, 256), np.nan, dtype="float32")
                reproject(field, result, src_transform=region_affine, src_crs="EPSG:4326",
                          src_nodata=np.nan, dst_transform=target, dst_crs="EPSG:3857",
                          dst_nodata=np.nan, resampling=Resampling.bilinear, num_threads=1)
            end = perf_counter()
            outputs[mode] = result
            timings[f"{mode}_read"] = read_finished - start
            timings[f"{mode}_warp"] = end - read_finished
            timings[f"{mode}_total"] = end - start

    file_values, http_values = outputs["file"], outputs["http"]
    valid = np.isfinite(file_values) & np.isfinite(http_values)
    return {
        "status": "ok", "timings": timings,
        "geometry": {"source_sha256": arrays_digest(np, lat, lon),
                     "target_sha256": arrays_digest(np, tuple(target), [256, 256])},
        "metrics": {
            "coverage": float(valid.mean()),
            "finite_mask_mismatches": int(np.count_nonzero(np.isfinite(file_values) ^ np.isfinite(http_values))),
            "max_common_difference": float(np.max(np.abs(file_values[valid] - http_values[valid]))) if valid.any() else None,
            "cog_sha256": sha256(cog), "cog_bytes": cog.stat().st_size, **transfer,
        },
    }
