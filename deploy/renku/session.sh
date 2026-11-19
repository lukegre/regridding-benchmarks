#!/usr/bin/env bash
set -euo pipefail
: "${RENKU_BASE_URL_PATH:?Renku must supply the session base URL}"
export HOME="${BENCH_SCRATCH_DIR:-/work}"
mkdir -p "$HOME"
exec jupyter lab --ServerApp.ip=0.0.0.0 --ServerApp.port=8888 \
  --ServerApp.base_url="$RENKU_BASE_URL_PATH" --ServerApp.token='' \
  --ServerApp.password='' --ServerApp.allow_remote_access=true \
  --ServerApp.root_dir="${BENCH_REPO:-/work}"
