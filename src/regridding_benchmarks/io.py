"""Deterministic JSON and atomic file updates."""

import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def fingerprint(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


@contextmanager
def atomic_file(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".pending-", delete=False) as stream:
        temp = Path(stream.name)
        try:
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
            temp.replace(path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temp.unlink(missing_ok=True)


def write_json(path, value):
    with atomic_file(path) as stream:
        stream.write(json_bytes(value))
