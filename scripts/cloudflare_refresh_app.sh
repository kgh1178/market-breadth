#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="${1:-}"
DRY_RUN="${DRY_RUN:-0}"

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

if [[ -z "$APP_NAME" ]]; then
  usage
  exit 1
fi

cd "$ROOT_DIR"

case "$APP_NAME" in
  breadth)
    echo "[cloudflare-refresh] generating breadth payloads"
    run_cmd python3 scripts/generate_json.py
    ;;
  exchange)
    echo "[cloudflare-refresh] generating exchange payloads"
    run_cmd python3 scripts/generate_exchange_json.py
    ;;
  *)
    echo "Unknown app: $APP_NAME" >&2
    usage
    exit 1
    ;;
esac

echo "[cloudflare-refresh] rebuilding static outputs"
run_cmd python3 scripts/build_static_apps.py

echo "[cloudflare-refresh] syncing $APP_NAME api artifacts to R2"
if [[ "$DRY_RUN" == "1" ]]; then
  DRY_RUN=1 run_cmd scripts/cloudflare_sync_r2.sh --app "$APP_NAME"
else
  scripts/cloudflare_sync_r2.sh --app "$APP_NAME"
fi

echo "[cloudflare-refresh] complete"
