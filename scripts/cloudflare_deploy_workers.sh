#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLOUDFLARE_DIR="$ROOT_DIR/cloudflare"
TARGET="${1:-all}"
DRY_RUN="${DRY_RUN:-0}"

run_deploy() {
  local workdir="$1"
  local label="$2"
  local cmd=(npx wrangler deploy)

  echo "[cloudflare-deploy] ${label} -> ${workdir}"
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[dry-run] (cd %q && ' "$workdir"
    printf '%q ' "${cmd[@]}"
    printf ')\n'
  else
    (
      cd "$workdir"
      "${cmd[@]}"
    )
  fi
}

case "$TARGET" in
  api)
    run_deploy "$CLOUDFLARE_DIR/api-worker" "api-worker"
    ;;
  breadth)
    run_deploy "$CLOUDFLARE_DIR/producers/breadth" "breadth-producer"
    ;;
  fear-greed)
    run_deploy "$CLOUDFLARE_DIR/producers/fear-greed" "fear-greed-producer"
    ;;
  exchange)
    run_deploy "$CLOUDFLARE_DIR/producers/exchange" "exchange-producer"
    ;;
  all)
    run_deploy "$CLOUDFLARE_DIR/api-worker" "api-worker"
    run_deploy "$CLOUDFLARE_DIR/producers/breadth" "breadth-producer"
    run_deploy "$CLOUDFLARE_DIR/producers/fear-greed" "fear-greed-producer"
    run_deploy "$CLOUDFLARE_DIR/producers/exchange" "exchange-producer"
    ;;
  *)
    echo "Unknown deploy target: $TARGET" >&2
    echo "Usage: scripts/cloudflare_deploy_workers.sh [api|breadth|fear-greed|exchange|all]" >&2
    exit 1
    ;;
esac

echo "[cloudflare-deploy] complete"
