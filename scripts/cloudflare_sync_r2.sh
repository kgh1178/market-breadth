#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUCKET_NAME="${CLOUDFLARE_R2_BUCKET:-jstockinsight-app-data}"
APP_NAME="${CLOUDFLARE_APP_NAME:-breadth}"
API_DIR="${CLOUDFLARE_API_DIR:-}"
DRY_RUN="${DRY_RUN:-0}"
REMOTE="${REMOTE:-1}"

usage() {
  cat <<'EOF'
Usage: scripts/cloudflare_sync_r2.sh [--dry-run] [--local] [--bucket NAME] [--app NAME] [--api-dir PATH]

Uploads app JSON artifacts to Cloudflare R2 using wrangler.

Examples:
  scripts/cloudflare_sync_r2.sh --dry-run
  scripts/cloudflare_sync_r2.sh --bucket jstockinsight-app-data --app breadth
  scripts/cloudflare_sync_r2.sh --local
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --local)
      REMOTE=0
      shift
      ;;
    --bucket)
      BUCKET_NAME="$2"
      shift 2
      ;;
    --app)
      APP_NAME="$2"
      shift 2
      ;;
    --api-dir)
      API_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$API_DIR" ]]; then
  API_DIR="$ROOT_DIR/docs/$APP_NAME/api"
fi

if [[ ! -d "$API_DIR" ]]; then
  echo "API directory not found: $API_DIR" >&2
  exit 1
fi

files=("$API_DIR"/*.json(N))
if [[ ${#files[@]} -eq 0 ]]; then
  echo "No JSON files found in $API_DIR" >&2
  exit 1
fi

echo "[cloudflare-r2-sync] app=$APP_NAME bucket=$BUCKET_NAME api_dir=$API_DIR"

for file in "${files[@]}"; do
  key="$APP_NAME/$(basename "$file")"
  cmd=(npx wrangler r2 object put "$BUCKET_NAME/$key" --file "$file")
  if [[ "$REMOTE" == "1" ]]; then
    cmd+=(--remote)
  fi
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[dry-run] '
    printf '%q ' "${cmd[@]}"
    printf '\n'
  else
    "${cmd[@]}"
  fi
done

echo "[cloudflare-r2-sync] complete"
