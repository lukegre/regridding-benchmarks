#!/usr/bin/env python3
"""Safely extract a trusted, checksum-verified site snapshot and merge editions."""
import argparse
import shutil
import tarfile
from pathlib import Path, PurePosixPath


def extract(archive, destination):
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        for member in members:
            name = PurePosixPath(member.name)
            if (name.is_absolute() or '..' in name.parts or not (member.isdir() or member.isfile())):
                raise ValueError(f'Unsafe snapshot member: {member.name}')
        tar.extractall(destination, members=members, filter='data')


def merge(previous, site):
    old = previous / 'editions'
    if not old.is_dir():
        raise ValueError('Prior site has no editions directory')
    target = site / 'editions'
    target.mkdir(parents=True, exist_ok=True)
    for item in old.iterdir():
        if item.is_symlink() or (target / item.name).exists():
            raise ValueError(f'Conflicting or unsafe edition: {item.name}')
        if item.is_dir():
            shutil.copytree(item, target / item.name, symlinks=False)
        elif item.is_file():
            shutil.copy2(item, target / item.name)
        else:
            raise ValueError(f'Unsafe edition: {item.name}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('archive', type=Path)
    parser.add_argument('previous', type=Path)
    parser.add_argument('site', type=Path)
    args = parser.parse_args()
    extract(args.archive, args.previous)
    merge(args.previous, args.site)
