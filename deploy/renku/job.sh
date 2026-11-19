#!/usr/bin/env bash
set -euo pipefail
: "${BENCH_SOURCE_REV:?Set BENCH_SOURCE_REV to the full commit SHA}"
: "${BENCH_OUTPUT_ROOT:?Set BENCH_OUTPUT_ROOT to a durable writable connector mount}"
: "${BENCH_CACHE_DIR:?Set BENCH_CACHE_DIR to a separate writable cache}"
: "${BENCH_SCRATCH_DIR:?Set BENCH_SCRATCH_DIR to separate writable scratch}"
: "${BENCH_RUN_ID:?Set a unique run ID}"
[[ "$BENCH_SOURCE_REV" =~ ^[0-9a-f]{40}$ ]] || { echo 'Expected full lowercase commit SHA' >&2; exit 2; }
: "${BENCH_REPO:?Set BENCH_REPO to a checkout pinned to BENCH_SOURCE_REV}"
repo=$BENCH_REPO
export GIT_OPTIONAL_LOCKS=0
actual=$(git -C "$repo" rev-parse HEAD)
[[ "${BENCH_IMAGE_SOURCE_REV:-}" == "$BENCH_SOURCE_REV" ]] || { echo "Image source revision mismatch" >&2; exit 2; }
[[ "$actual" == "$BENCH_SOURCE_REV" ]] || { echo "Source revision mismatch: $actual" >&2; exit 2; }
[[ -z "$(git -C "$repo" status --porcelain)" ]] || { echo 'Source checkout is dirty' >&2; exit 2; }
mkdir -p "$BENCH_OUTPUT_ROOT" "$BENCH_CACHE_DIR" "$BENCH_SCRATCH_DIR"
export TMPDIR="$BENCH_SCRATCH_DIR" NUMBA_CACHE_DIR="$BENCH_SCRATCH_DIR/numba" MPLCONFIGDIR="$BENCH_SCRATCH_DIR/matplotlib"
profile=${BENCH_PROFILE:-smoke}
bundle="$BENCH_OUTPUT_ROOT/$BENCH_RUN_ID"
regridding-benchmarks fetch --profile "$profile" --cache-dir "$BENCH_CACHE_DIR" --repo "$repo"
regridding-benchmarks run --profile "$profile" --output-dir "$BENCH_OUTPUT_ROOT" --run-id "$BENCH_RUN_ID" --cache-dir "$BENCH_CACHE_DIR" --scratch-dir "$BENCH_SCRATCH_DIR" --series "${BENCH_SERIES:-renkulab}" --repo "$repo"
regridding-benchmarks validate-bundle "$bundle"
