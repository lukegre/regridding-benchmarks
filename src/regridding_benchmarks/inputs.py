"""Find or download inputs by their manifest SHA-256."""

import hashlib
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from .io import atomic_file, sha256


class InputUnavailable(Exception):
    pass


def resolve(dataset, cache, repo, *, fetch=False):
    digest = dataset.get("sha256")
    if not digest:
        raise InputUnavailable(dataset.get("reason") or "No input checksum is pinned")
    if dataset.get("path"):
        path = (repo / dataset["path"]).resolve()
        if not path.is_relative_to(repo) or not path.is_file() or sha256(path) != digest:
            raise ValueError(f"Missing or invalid pinned repository input {dataset['id']}")
        return path
    path = cache / digest
    if path.is_file():
        if sha256(path) != digest:
            raise ValueError(f"Checksum mismatch in cache for {dataset['id']}")
        return path
    if not fetch or not dataset.get("url"):
        raise InputUnavailable(dataset.get("reason") or "Pinned input is absent from the cache")
    url = dataset["url"]
    if not url.startswith("https://"):
        raise ValueError(f"Dataset URL must use HTTPS: {dataset['id']}")
    observed = hashlib.sha256()
    try:
        with urlopen(url, timeout=60) as response, atomic_file(path) as stream:
            for chunk in iter(lambda: response.read(1 << 20), b""):
                observed.update(chunk)
                stream.write(chunk)
            if observed.hexdigest() != digest:
                raise ValueError(f"Downloaded checksum mismatch for {dataset['id']}")
    except (URLError, TimeoutError, ConnectionError) as error:
        raise InputUnavailable(f"Download failed: {getattr(error, 'reason', error)}") from error
    return path


def default_cache():
    return Path.home() / ".cache" / "regridding-benchmarks" / "inputs"
