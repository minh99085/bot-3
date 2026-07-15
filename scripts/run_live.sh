#!/usr/bin/env bash
# Live mode — HARD GATED. Hermes Paper deployments refuse this path.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${HERMES_PAPER_ONLY:-1}" == "1" ]]; then
  echo "Refusing live: HERMES_PAPER_ONLY=1 (this is a paper-only deployment)."
  exit 1
fi
if [[ "${HERMES_LIVE:-0}" != "1" ]]; then
  echo "Refusing live: set HERMES_LIVE=1 after paper WR>=80% evidence."
  exit 1
fi

export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -r requirements.txt
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

python -m hermes.hermes_loop "${1:-once}" --live "${@:2}"
