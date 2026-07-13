#!/usr/bin/env python3
"""Compare paper A/B win-rate by research.ab_profile from btc_pulse ledger."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEDGER = ROOT / "vps_full_reports" / "latest" / "btc_pulse_ledger.json"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def compare_ab_profiles(
    ledger: dict,
    *,
    lookback_hours: float | None = None,
    now_ts: float | None = None,
) -> dict[str, Any]:
    """Aggregate settled WR/PnL by research.ab_profile."""
    now_ts = now_ts if now_ts is not None else datetime.now(timezone.utc).timestamp()
    cutoff = None
    if lookback_hours is not None and lookback_hours > 0:
        cutoff = now_ts - (lookback_hours * 3600.0)

    buckets: dict[str, dict[str, Any]] = {}

    def _b(name: str) -> dict[str, Any]:
        if name not in buckets:
            buckets[name] = {
                "n": 0, "wins": 0, "pnl_usd": 0.0, "open": 0,
                "avg_entry": [], "blocked_fade": 0,
            }
        return buckets[name]

    for pos in ledger.get("positions") or []:
        rt = pos.get("research") or {}
        prof = str(rt.get("ab_profile") or "legacy")
        st = (pos.get("status") or "").lower()
        b = _b(prof)
        if st == "open":
            b["open"] += 1
            continue
        if st != "settled":
            continue
        try:
            entry_ts = float(pos.get("entry_ts") or pos.get("open_ts") or 0)
            pnl = float(pos.get("pnl_usd") or 0)
            entry_price = float(pos.get("entry_price") or 0)
            won = bool(pos.get("won"))
        except (TypeError, ValueError):
            continue
        if cutoff is not None and entry_ts < cutoff:
            continue
        b["n"] += 1
        if won:
            b["wins"] += 1
        b["pnl_usd"] = round(float(b["pnl_usd"]) + pnl, 2)
        if entry_price > 0:
            b["avg_entry"].append(entry_price)
        fav = rt.get("favorites_gate") or {}
        if fav.get("reason") == "cell_phase2_fade":
            b["blocked_fade"] += 1

    out: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lookback_hours": lookback_hours,
        "by_profile": {},
    }
    for prof, b in sorted(buckets.items()):
        n = b["n"]
        entries = b.pop("avg_entry")
        out["by_profile"][prof] = {
            **b,
            "wr": round(b["wins"] / n, 4) if n else None,
            "avg_entry": round(sum(entries) / len(entries), 4) if entries else None,
        }
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="A/B WR compare by ab_profile")
    ap.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    ap.add_argument("--hours", type=float, default=48.0,
                    help="Lookback window (0 = all settled)")
    ap.add_argument("--json", action="store_true", help="Emit JSON only")
    args = ap.parse_args(argv)

    ledger = _load_json(args.ledger)
    if not ledger.get("positions"):
        print(f"No positions in {args.ledger}", file=sys.stderr)
        return 1

    lookback = None if args.hours <= 0 else args.hours
    report = compare_ab_profiles(ledger, lookback_hours=lookback)

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"A/B compare ({args.hours}h lookback)" if lookback else "A/B compare (all time)")
    for prof, s in report["by_profile"].items():
        wr = f"{100 * s['wr']:.1f}%" if s["wr"] is not None else "n/a"
        avg = f"{s['avg_entry']:.3f}" if s["avg_entry"] is not None else "n/a"
        print(
            f"  {prof:12s}  n={s['n']:3d}  wr={wr:>6s}  pnl=${s['pnl_usd']:+.2f}"
            f"  open={s['open']}  avg_entry={avg}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
