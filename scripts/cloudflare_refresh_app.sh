#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="${1:-}"
DRY_RUN="${DRY_RUN:-0}"
PYTHON_BIN="${PYTHON_BIN:-}"

usage() {
  cat <<'EOF'
Usage: scripts/cloudflare_refresh_app.sh [breadth|exchange]

Generates app JSON artifacts, rebuilds static outputs, and syncs the app API
payloads to Cloudflare R2.

Examples:
  scripts/cloudflare_refresh_app.sh breadth
  scripts/cloudflare_refresh_app.sh exchange
  DRY_RUN=1 scripts/cloudflare_refresh_app.sh exchange
EOF
}

run_cmd() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[dry-run] '
    printf '%q ' "$@"
    printf '\n'
  else
    "$@"
  fi
}

pick_python() {
  if [[ -n "$PYTHON_BIN" ]]; then
    echo "$PYTHON_BIN"
    return 0
  fi

  local candidates=(
    "$(command -v python3 2>/dev/null || true)"
    "/usr/local/bin/python3"
    "/opt/homebrew/bin/python3"
    "/usr/bin/python3"
  )
  local candidate

  for candidate in "${candidates[@]}"; do
    [[ -z "$candidate" ]] && continue
    [[ ! -x "$candidate" ]] && continue
    if "$candidate" -c "import numpy, pandas, yfinance" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done

  echo "Unable to find a python3 interpreter with numpy/pandas/yfinance installed." >&2
  exit 1
}

if [[ -z "$APP_NAME" ]]; then
  usage
  exit 1
fi

cd "$ROOT_DIR"
PYTHON_BIN="$(pick_python)"
echo "[cloudflare-refresh] using python: $PYTHON_BIN"

case "$APP_NAME" in
  breadth)
    echo "[cloudflare-refresh] generating breadth payloads"
    run_cmd "$PYTHON_BIN" scripts/generate_json.py
    ;;
  exchange)
    echo "[cloudflare-refresh] generating exchange payloads"
    run_cmd "$PYTHON_BIN" scripts/generate_exchange_json.py
    ;;
  *)
    echo "Unknown app: $APP_NAME" >&2
    usage
    exit 1
    ;;
esac

echo "[cloudflare-refresh] rebuilding static outputs"
run_cmd "$PYTHON_BIN" scripts/build_static_apps.py

echo "[cloudflare-refresh] syncing $APP_NAME api artifacts to R2"
if [[ "$DRY_RUN" == "1" ]]; then
  DRY_RUN=1 run_cmd scripts/cloudflare_sync_r2.sh --app "$APP_NAME"
else
  scripts/cloudflare_sync_r2.sh --app "$APP_NAME"
fi

echo "[cloudflare-refresh] complete"
