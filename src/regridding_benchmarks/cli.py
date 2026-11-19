"""Command line interface for reproduction and publication."""

import argparse
import json
import signal
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from subprocess import SubprocessError

from . import bundle, report, runner
from .inputs import InputUnavailable, default_cache, resolve
from .registry import load, select


def repo_path(path):
    return path.expanduser().resolve()


def default_output():
    return Path.home() / ".local" / "state" / "regridding-benchmarks" / "runs"


def parser():
    root = argparse.ArgumentParser(prog="regridding-benchmarks")
    root.add_argument("--repo", type=Path, default=Path.cwd(), help="benchmark checkout")
    commands = root.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list-cases", help="list versioned cases")
    listing.add_argument("--json", action="store_true")
    fetch = commands.add_parser("fetch", help="verify or fetch checksum-pinned inputs")
    execute = commands.add_parser("run", help="run or resume a profile")
    for command in (listing, fetch, execute):
        command.add_argument("--profile", default="smoke")
        command.add_argument("--case", action="append", default=[])
    for command in (fetch, execute):
        command.add_argument("--cache-dir", type=Path, default=default_cache())
    execute.add_argument("--output-dir", type=Path, default=default_output())
    execute.add_argument("--scratch-dir", type=Path, default=Path(tempfile.gettempdir()) / "regridding")
    execute.add_argument("--run-id")
    execute.add_argument("--series", default="local")
    execute.add_argument("--resume", action="store_true")
    validate = commands.add_parser("validate-bundle", help="verify a run bundle and its sample roster")
    validate.add_argument("bundle", type=Path)
    validate.add_argument("--publication", action="store_true")
    validate.add_argument("--check-roster", action="store_true",
                          help="compare against a clean checkout of the run revision")
    build = commands.add_parser("build-report", help="render a site from validated evidence")
    build.add_argument("bundle", type=Path)
    build.add_argument("--output-dir", type=Path, required=True)
    build.add_argument("--legacy-dir", type=Path)
    build.add_argument("--legacy-edition", type=Path, help="verified raw legacy edition")
    legacy = commands.add_parser("import-legacy", help="preserve the original evidence and tool guide")
    legacy.add_argument("--output-dir", type=Path, required=True)
    for command in (listing, fetch, execute, validate, build, legacy):
        command.add_argument("--repo", type=Path, default=argparse.SUPPRESS)
    return root


def dispatch(args):
    repo = repo_path(args.repo)
    if args.command == "validate-bundle":
        manifest, rows = bundle.validate(args.bundle, publication=args.publication)
        if args.check_roster:
            bundle.check_roster(repo, manifest)
        print(f"{manifest['run_id']} · verified {len(rows)} samples")
        return 0
    if args.command == "build-report":
        report.build(repo_path(args.bundle), repo_path(args.output_dir),
                     legacy=repo_path(args.legacy_dir) if args.legacy_dir else repo / "docs",
                     legacy_edition=repo_path(args.legacy_edition) if args.legacy_edition else None)
        return 0
    if args.command == "import-legacy":
        from .legacy import build_edition, validate_edition
        output = repo_path(args.output_dir)
        build_edition(repo, output)
        validate_edition(output)
        print(output)
        return 0
    profiles, cases, datasets = load(repo)
    profile = args.profile
    roster = select(cases, profiles, profile, args.case)
    if args.command == "list-cases":
        if args.json:
            print(json.dumps(roster, indent=2))
        else:
            for case in roster:
                print(f"{case['id']}\t{case['family']}\t{case['method']}")
        return 0
    cache = repo_path(args.cache_dir)
    if args.command == "fetch":
        for identifier in sorted({case["dataset"] for case in roster if case.get("dataset")}):
            try:
                path = resolve(datasets[identifier], cache, repo, fetch=True)
            except InputUnavailable as error:
                print(f"{identifier}\tunavailable\t{error}")
            else:
                print(f"{identifier}\tverified\t{path}")
        return 0
    if args.resume and not args.run_id:
        raise ValueError("--resume requires --run-id")
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = runner.run(repo, repo_path(args.output_dir), run_id, profile, profiles[profile],
                      roster, datasets, cache, repo_path(args.scratch_dir), args.series,
                      resume=args.resume, full_profile=not args.case)
    _, rows = bundle.validate(path)
    print(path)
    unexpected = [sample for case, sample, result in rows if result["status"] not in case["expected"]]
    if unexpected:
        print(f"{len(unexpected)} unexpected outcomes, starting with {unexpected[0]}", file=sys.stderr)
    return int(bool(unexpected))


def main(argv=None):
    try:
        return dispatch(parser().parse_args(argv))
    except (OSError, KeyError, TypeError, ValueError, SubprocessError) as error:
        print(f"regridding-benchmarks: {error}", file=sys.stderr)
        return 2


def terminate(signum, frame):
    raise KeyboardInterrupt


def entry_point():
    signal.signal(signal.SIGTERM, terminate)
    try:
        return main()
    except KeyboardInterrupt:
        print("Run interrupted. Completed checkpoints are available to resume.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(entry_point())
