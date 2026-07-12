#!/usr/bin/env python3
"""Prepare .env for local Bot 3 paper training (Docker Desktop)."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "hermes-agent-main" / "plugins" / "hermes-trading-engine"
ENV_PATH = PLUGIN / ".env"
EXAMPLE = PLUGIN / ".env.example"
TV_SECRET_FILE = PLUGIN / "tradingview.secret"
TV_SECRET_EXAMPLE = PLUGIN / "tradingview.secret.example"

LOCAL_OVERRIDES = {
    "PULSE_DASHBOARD_BOT_LABEL": "Bot 3 - Local Training",
    "PULSE_DASHBOARD_PUBLISH": "127.0.0.1:8810",
    "TRADINGVIEW_WEBHOOK_PUBLISH": "127.0.0.1:18787",
    "PAPER_TRAINING_ENABLED": "1",
    "POLYMARKET_PAPER_TRAINING_ENABLED": "1",
    "BTC_PULSE_ENABLED": "1",
    "BTC_PULSE_PAPER_ONLY": "1",
    "LIVE_TRADING_ENABLED": "0",
    "POLYMARKET_LIVE_ENABLED": "0",
    "GROK_SIGNAL_ANALYST_ENABLED": "0",
    "GROK_SIGNAL_PREDICTOR_ENABLED": "0",
    "GROK_OVERLAY_ENABLED": "0",
    "PULSE_GROK_DECIDER_MODE": "shadow",
    "PULSE_RESEARCH_LOOP_ENABLED": "0",
    "PULSE_VERIFIER_ENABLED": "0",
}

# TradingView observe-only intake - wired for local; user only supplies tradingview.secret
TV_LOCAL_WIRING = {
    "TRADINGVIEW_WEBHOOK_HOST": "0.0.0.0",
    "TRADINGVIEW_WEBHOOK_PORT": "8787",
    "TRADINGVIEW_WEBHOOK_PATH": "/webhooks/tradingview",
    "TRADINGVIEW_WEBHOOK_UPSTREAM": "http://hermes-training:8787",
    "TRADINGVIEW_WEBHOOK_MIRROR_URL": "",
    "BOT_NAME": "hermes",
    "TRADINGVIEW_BOT_NAME": "hermes",
    "PULSE_TV_EVENT_ID_SUFFIX": "bot3",
    "PULSE_TV_FEATURE_SYMBOL": "BTCUSD",
    "TRADINGVIEW_ALLOWED_SYMBOLS": "BTCUSD,INDEX:BTCUSD,BTC/USD,BTC,XBTUSD",
    "TRADINGVIEW_MAX_AGE_S": "3600",
    "PULSE_TV_SIGNAL_MAX_FEATURE_AGE_S": "3600",
    "PULSE_TV_SIGNAL_HORIZON_S": "300",
    "PULSE_TV_MTF_TIMEFRAMES": "5,10,15,20,25,30,35,40,45,50,55,60",
    "PULSE_TV_2H_REVIEW_ENABLED": "1",
    "PULSE_TV_2H_LOOKBACK_S": "7200",
    "PULSE_TV_RSI_OVERLAY_ENABLED": "1",
    "PULSE_TRADINGVIEW_SIGNAL_GATE": "0",
    "PULSE_TV_PROMOTION_ALLOWED": "0",
}


def _parse_env(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _env_get(lines: list[str], key: str) -> str:
    for ln in lines:
        if ln.startswith(f"{key}="):
            raw = ln.split("=", 1)[1].strip()
            if raw.startswith('"') and raw.endswith('"'):
                return raw[1:-1].replace('\\"', '"')
            return raw
    return ""


def _format_env_value(val: str) -> str:
    if any(c in val for c in " \t#\"'") or not val:
        escaped = val.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return val


def _upsert(lines: list[str], updates: dict[str, str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for ln in lines:
        if "=" in ln and not ln.lstrip().startswith("#"):
            key = ln.split("=", 1)[0].strip()
            if key in updates:
                out.append(f"{key}={_format_env_value(updates[key])}")
                seen.add(key)
                continue
        if ln.strip() or out:
            out.append(ln)
    for key, val in updates.items():
        if key not in seen:
            out.append(f"{key}={_format_env_value(val)}")
    return out


def _load_tradingview_secret(lines: list[str]) -> str:
    if TV_SECRET_FILE.exists():
        for raw in TV_SECRET_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("TRADINGVIEW_WEBHOOK_SECRET="):
                return line.split("=", 1)[1].strip().strip('"')
            if line in ("PASTE_YOUR_SECRET_HERE", "CHANGE_ME", ""):
                continue
            return line
    return _env_get(lines, "TRADINGVIEW_WEBHOOK_SECRET")


def _ensure_secret_template() -> None:
    if TV_SECRET_FILE.exists() or not TV_SECRET_EXAMPLE.exists():
        return
    shutil.copy2(TV_SECRET_EXAMPLE, TV_SECRET_FILE)
    print(f"Created {TV_SECRET_FILE} - paste your TradingView secret on line 1")


def main() -> int:
    if not PLUGIN.is_dir():
        print(f"ERROR: plugin path missing: {PLUGIN}", file=sys.stderr)
        return 1

    _ensure_secret_template()

    if not ENV_PATH.exists():
        if not EXAMPLE.exists():
            print(f"ERROR: missing {EXAMPLE}", file=sys.stderr)
            return 1
        shutil.copy2(EXAMPLE, ENV_PATH)
        print(f"Created {ENV_PATH} from .env.example")

    apply = ROOT / "scripts" / "apply-loop-arch-env.py"
    if apply.exists():
        subprocess.run([sys.executable, str(apply)], check=True, cwd=ROOT)
    else:
        print(f"WARN: {apply} not found; using template .env only")

    lines = _parse_env(ENV_PATH)
    updates = {**LOCAL_OVERRIDES, **TV_LOCAL_WIRING}
    secret = _load_tradingview_secret(lines)
    if secret:
        updates["TRADINGVIEW_WEBHOOK_SECRET"] = secret
    lines = _upsert(lines, updates)
    if not any(ln.startswith("# LOCAL BOT 3") for ln in lines):
        lines.append("# LOCAL BOT 3 - laptop Docker training profile")
    if not any(ln.startswith("# TRADINGVIEW LOCAL") for ln in lines):
        lines.append("# TRADINGVIEW LOCAL - intake wired; secret from tradingview.secret")
    ENV_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote local training overrides to {ENV_PATH}")

    if secret:
        print("TradingView webhook: ENABLED (secret loaded from tradingview.secret)")
        print("  Local test URL : http://127.0.0.1:8810/webhooks/tradingview")
        print("  TV via ngrok     : https://<your-ngrok>/webhooks/tradingview  (ngrok http 8810)")
        print("  Pine secret input: same value as tradingview.secret")
    else:
        print("TradingView webhook: waiting for secret")
        print(f"  Edit {TV_SECRET_FILE} (paste one line), then re-run run-bot3-local-training.ps1")

    validate = ROOT / "scripts" / "pulse-babysit" / "validate-frozen-lock.py"
    if validate.exists():
        subprocess.run([sys.executable, str(validate)], check=False, cwd=ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
