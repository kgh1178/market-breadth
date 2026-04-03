#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$ROOT_DIR"

echo "[cloudflare-preflight] running breadth pipeline"
python3 scripts/generate_json.py

echo "[cloudflare-preflight] building static app outputs"
python3 scripts/build_static_apps.py

echo "[cloudflare-preflight] running test suite"
python3 -m pytest -q

echo "[cloudflare-preflight] breadth api artifacts"
find docs/breadth/api -maxdepth 1 -type f | sort

echo "[cloudflare-preflight] complete"
