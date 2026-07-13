#!/usr/bin/env bash
# Rotate VPS paper A/B profile between throughput (A) and favorites (B).
# Usage: ./scripts/rotate-ab-profile.sh [throughput|favorites|toggle]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROFILE="${1:-toggle}"
VPS_REPO="${BOT3_VPS_REPO:-/opt/Bot-3}"

case "$PROFILE" in
  throughput|a|profile_a)
    SETUP="scripts/setup-vps-training-env.py"
    LABEL="throughput"
    ;;
  favorites|b|profile_b)
    SETUP="scripts/setup-vps-favorites-ab-env.py"
    LABEL="favorites"
    ;;
  toggle)
    ENV_FILE="$VPS_REPO/hermes-agent-main/plugins/hermes-trading-engine/.env"
    if [[ -f "$ENV_FILE" ]] && grep -q '^PULSE_AB_PROFILE=favorites' "$ENV_FILE" 2>/dev/null; then
      SETUP="scripts/setup-vps-training-env.py"
      LABEL="throughput"
    else
      SETUP="scripts/setup-vps-favorites-ab-env.py"
      LABEL="favorites"
    fi
    ;;
  *)
    echo "Usage: $0 [throughput|favorites|toggle]" >&2
    exit 1
    ;;
esac

echo "Rotating A/B profile -> $LABEL via $SETUP"
cd "$ROOT"
python3 "$ROOT/$SETUP"
export BOT3_VPS_SETUP_SCRIPT="$SETUP"
bash "$ROOT/scripts/sync-vps-bot3.sh"
