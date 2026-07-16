#!/usr/bin/env python3
"""Pull VPS paper ledgers and publish a full trading report bundle."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INSTANCE_IDS = ("btc5", "btc15", "eth5", "sol5", "rotator")
STARTING_BANKROLL = 2000.0
FLEET_BANKROLL = STARTING_BANKROLL * 5
BACKTEST_BUNDLE = ROOT / "reports" / "full_backtest_vps_20260716_strict_real"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
        except json.JSONDecodeError:
            continue
    return rows


def settlements_for(paper_dir: Path, instance_id: str) -> list[dict[str, Any]]:
    rows = read_jsonl(paper_dir / instance_id / "trade_ledger.jsonl")
    return [r for r in rows if r.get("event") == "settlement" or r.get("won") is not None]


def fills_for(paper_dir: Path, instance_id: str) -> list[dict[str, Any]]:
    rows = read_jsonl(paper_dir / instance_id / "trade_ledger.jsonl")
    return [r for r in rows if r.get("event") == "fill"]


def pretrade_for(paper_dir: Path, instance_id: str) -> list[dict[str, Any]]:
    return read_jsonl(paper_dir / instance_id / "pretrade_decisions.jsonl")


def instance_summary(paper_dir: Path, instance_id: str) -> dict[str, Any]:
    settles = settlements_for(paper_dir, instance_id)
    fills = fills_for(paper_dir, instance_id)
    pts = pretrade_for(paper_dir, instance_id)
    wins = sum(1 for s in settles if s.get("won") or float(s.get("pnl_usd", 0) or 0) > 0)
    losses = len(settles) - wins
    pnls = [float(s.get("pnl_usd", 0) or 0) for s in settles]
    equity = STARTING_BANKROLL + sum(pnls)
    open_ids = {
        r.get("signal_id")
        for r in read_jsonl(paper_dir / instance_id / "trade_ledger.jsonl")
        if r.get("event") == "settlement" and r.get("signal_id")
    }
    open_n = sum(
        1
        for f in fills
        if f.get("signal_id") and f.get("signal_id") not in open_ids
    )
    skipped = sum(1 for p in pts if p.get("skip") is True)
    taken = sum(1 for p in pts if p.get("skip") is False)
    ledger_exists = (paper_dir / instance_id / "trade_ledger.jsonl").exists()

    return {
        "instance_id": instance_id,
        "bankroll_usd": STARTING_BANKROLL,
        "equity_usd": round(equity, 2),
        "pnl_usd": round(equity - STARTING_BANKROLL, 2),
        "n_settled": len(settles),
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / len(settles), 4) if settles else None,
        "open_positions": open_n,
        "n_fills": len(fills),
        "pretrade_decisions": len(pts),
        "pretrade_skipped": skipped,
        "pretrade_taken": taken,
        "has_ledger": ledger_exists,
        "status": "active" if (settles or open_n or taken) else ("watching" if pts else "idle"),
    }


def trade_rows(paper_dir: Path, instance_id: str) -> list[dict[str, Any]]:
    ledger = read_jsonl(paper_dir / instance_id / "trade_ledger.jsonl")
    fills = {f.get("signal_id"): f for f in ledger if f.get("event") == "fill"}
    rows: list[dict[str, Any]] = []
    for s in ledger:
        if s.get("event") != "settlement":
            continue
        sid = s.get("signal_id")
        f = fills.get(sid, {})
        meta = f.get("meta") or {}
        rows.append(
            {
                "instance_id": instance_id,
                "signal_id": sid,
                "slug": s.get("slug") or f.get("slug") or "",
                "direction": s.get("direction"),
                "size_usd": s.get("size_usd") or f.get("size_usd"),
                "entry_price": s.get("entry_price") or f.get("fill_price"),
                "pnl_usd": s.get("pnl_usd"),
                "won": s.get("won"),
                "settled_at": s.get("settled_at"),
                "entry_source": meta.get("entry_source") or "",
                "model_q_source": meta.get("model_q_source") or "",
                "enhanced_edge": meta.get("enhanced_edge"),
                "enhanced_conviction": meta.get("enhanced_conviction"),
                "bandit_arm": meta.get("bandit_arm"),
                "live_real_q": meta.get("live_real_q"),
                "timeframe": s.get("timeframe") or meta.get("timeframe"),
                "notes": s.get("notes") or "",
            }
        )
    rows.sort(key=lambda r: str(r.get("settled_at") or ""))
    return rows


def fleet_summary(instances: list[dict[str, Any]]) -> dict[str, Any]:
    total_settled = sum(i["n_settled"] for i in instances)
    total_wins = sum(i["wins"] for i in instances)
    total_losses = sum(i["losses"] for i in instances)
    fleet_equity = sum(i["equity_usd"] for i in instances)
    return {
        "fleet_bankroll_usd": FLEET_BANKROLL,
        "per_instance_bankroll_usd": STARTING_BANKROLL,
        "instance_count": len(instances),
        "fleet_equity_usd": round(fleet_equity, 2),
        "fleet_pnl_usd": round(fleet_equity - FLEET_BANKROLL, 2),
        "total_settled": total_settled,
        "wins": total_wins,
        "losses": total_losses,
        "win_rate": round(total_wins / total_settled, 4) if total_settled else None,
        "instances_with_activity": sum(
            1 for i in instances if i["n_settled"] or i["open_positions"] or i["pretrade_taken"]
        ),
        "instances": instances,
    }


def instance_summary_equity(inst: dict[str, Any]) -> float:
    return float(inst["equity_usd"])


def rsync_from_vps(dest: Path, host: str) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    cmd = [
        "rsync",
        "-avz",
        "-e",
        "ssh -i ~/.ssh/bot3_cloud_agent -o StrictHostKeyChecking=no",
        f"root@{host}:/opt/financial-freedom-bot/data/paper/",
        str(dest) + "/",
    ]
    subprocess.run(cmd, check=True)


def build_report(
    paper_dir: Path,
    out_dir: Path,
    *,
    vps_host: str,
    main_commit: str,
    pulled_at: str,
) -> dict[str, Any]:
    instances = [instance_summary(paper_dir, iid) for iid in INSTANCE_IDS]
    fleet = fleet_summary(instances)
    trades = []
    for iid in INSTANCE_IDS:
        trades.extend(trade_rows(paper_dir, iid))

    backtest_metrics: dict[str, Any] = {}
    backtest_report: dict[str, Any] = {}
    if (BACKTEST_BUNDLE / "metrics.json").exists():
        backtest_metrics = json.loads((BACKTEST_BUNDLE / "metrics.json").read_text())
    if (BACKTEST_BUNDLE / "report.json").exists():
        backtest_report = json.loads((BACKTEST_BUNDLE / "report.json").read_text())

    report = {
        "generated_at": pulled_at,
        "vps_host": vps_host,
        "main_commit": main_commit,
        "paper_dir": str(paper_dir.relative_to(ROOT)) if paper_dir.is_relative_to(ROOT) else str(paper_dir),
        "section_a_live_paper": fleet,
        "section_b_backtest": {
            "bundle": str(BACKTEST_BUNDLE.relative_to(ROOT)),
            "mode": "strict_real",
            "metrics": backtest_metrics,
            "verdict": backtest_report.get("verdict"),
            "target_met": backtest_metrics.get("target_met"),
        },
        "section_c_deploy": {
            "dashboard_title": "Bot 3",
            "paper_only": True,
            "frozen_gates": {
                "mode": "strict_real",
                "min_edge": 0.14,
                "min_conviction": 0.93,
                "kappa": 0.35,
                "max_single_market_pct": 0.08,
                "risk_budget": 0.18,
                "live_real_q": True,
            },
            "autonomy_stack": [
                "MCHB",
                "EHO",
                "CBPF",
                "RASP",
                "RGMC",
                "model_registry",
                "data_ingest",
                "continuous_loop",
            ],
        },
        "trades": trades,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "fleet_paper.json").write_text(json.dumps(fleet, indent=2) + "\n")
    (out_dir / "trades.json").write_text(json.dumps(trades, indent=2) + "\n")
    (out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (out_dir / "report.txt").write_text(render_text(report) + "\n")
    (out_dir / "README.md").write_text(render_readme(report) + "\n")

    if BACKTEST_BUNDLE.exists():
        for name in ("metrics.json", "parameters_used.yaml"):
            src = BACKTEST_BUNDLE / name
            if src.exists():
                shutil.copy2(src, out_dir / name)

    return report


def render_text(report: dict[str, Any]) -> str:
    fleet = report["section_a_live_paper"]
    bt = report["section_b_backtest"]
    m = bt.get("metrics") or {}
    lines = [
        "Bot 3 — Full Trading Report",
        f"Generated: {report['generated_at']}",
        f"VPS: {report['vps_host']} | main @ {report['main_commit']}",
        "",
        "=== A) Live VPS paper fleet ===",
        f"Fleet equity: ${fleet['fleet_equity_usd']:,.2f} / ${fleet['fleet_bankroll_usd']:,.2f} bankroll",
        f"Fleet PnL: ${fleet['fleet_pnl_usd']:,.2f}",
        f"Settled trades: {fleet['total_settled']} | WR: {fmt_pct(fleet.get('win_rate'))}",
        f"W/L: {fleet['wins']}/{fleet['losses']} | Instances active: {fleet['instances_with_activity']}/5",
        "",
    ]
    for inst in fleet["instances"]:
        wr = fmt_pct(inst.get("win_rate")) if inst["n_settled"] else "n/a"
        lines.append(
            f"  {inst['instance_id']:8}  settled={inst['n_settled']:3}  "
            f"open={inst['open_positions']}  pnl=${inst['pnl_usd']:+7.2f}  wr={wr}  "
            f"status={inst['status']}"
        )
    lines.extend(
        [
            "",
            "=== B) Synthetic backtest validation (strict_real) ===",
            bt.get("verdict") or "See metrics.json",
            f"Win rate: {fmt_pct(m.get('win_rate'))} | Trades: {m.get('n_trades')} | "
            f"Selectivity: {fmt_pct(m.get('selectivity'))}",
            f"Profit factor: {m.get('profit_factor', 0):.2f} | Max DD: {fmt_pct(m.get('max_drawdown_pct'))}",
            f"Brier: {m.get('brier', 0):.3f} | Target met: {m.get('target_met')}",
            "",
            "=== C) Deploy / freeze ===",
            "HERMES_PAPER_ONLY=1 | live_real_q=True | strict_real gates frozen",
            f"Autonomy: {', '.join(report['section_c_deploy']['autonomy_stack'])}",
            "",
            f"Trade log: {len(report.get('trades', []))} settled rows in trades.json",
        ]
    )
    return "\n".join(lines)


def render_readme(report: dict[str, Any]) -> str:
    fleet = report["section_a_live_paper"]
    bt = report["section_b_backtest"]
    m = bt.get("metrics") or {}
    return f"""# Full Trading Report — 2026-07-16

Published from VPS paper fleet pull + bundled `strict_real` backtest validation.

## Reproduce

```bash
# Pull latest ledgers from VPS
python scripts/generate_trading_report.py --pull

# Or use existing local pull
python scripts/generate_trading_report.py --paper-dir data/paper_pull
```

## A) Live VPS paper fleet

| Metric | Value |
|--------|-------|
| Fleet bankroll | ${fleet['fleet_bankroll_usd']:,.0f} (5 × $2k) |
| Fleet equity | ${fleet['fleet_equity_usd']:,.2f} |
| Fleet PnL | ${fleet['fleet_pnl_usd']:,.2f} |
| Settled trades | {fleet['total_settled']} |
| Win rate | {fmt_pct(fleet.get('win_rate'))} |
| Active instances | {fleet['instances_with_activity']}/5 |

Per-instance breakdown in `fleet_paper.json` and `trades.json`.

**Note:** Early post-reset sample — live crypto up/down lanes only (btc5, btc15, rotator). eth5/sol5 watching, no fills yet.

## B) Synthetic backtest (`strict_real`)

Source bundle: `{bt.get('bundle')}`

| Metric | Value |
|--------|-------|
| Win rate | {fmt_pct(m.get('win_rate'))} |
| Trades | {m.get('n_trades')} / {m.get('n_decisions')} decisions |
| Selectivity | {fmt_pct(m.get('selectivity'))} |
| Profit factor | {m.get('profit_factor', 0):.2f} |
| Max drawdown | {fmt_pct(m.get('max_drawdown_pct'))} |
| Brier | {m.get('brier', 0):.3f} |
| Target met | {m.get('target_met')} |

{bt.get('verdict') or ''}

## C) Deploy context

- **Commit:** `{report['main_commit']}`
- **VPS:** `{report['vps_host']}`
- **Mode:** `strict_real`, `HERMES_PAPER_ONLY=1`, `live_real_q=True`
- **Dashboard:** Bot 3
- **Autonomy stack:** MCHB, EHO, CBPF, RASP, RGMC, registry, ingest, continuous loop

Frozen gates: `min_edge=0.14`, `min_conviction=0.93`, κ=0.35, `max_single=0.08`, `risk_budget=0.18`.

## Files

| File | Purpose |
|------|---------|
| `report.txt` | Human-readable summary |
| `report.json` | Full structured report |
| `fleet_paper.json` | Per-instance fleet stats |
| `trades.json` | All settled trades with meta |
| `metrics.json` | Backtest metrics snapshot |
| `parameters_used.yaml` | strict_real config snapshot |
"""


def fmt_pct(v: Any) -> str:
    if v is None:
        return "n/a"
    try:
        return f"{float(v) * 100:.1f}%"
    except (TypeError, ValueError):
        return str(v)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate full trading report bundle")
    parser.add_argument(
        "--paper-dir",
        type=Path,
        default=ROOT / "data" / "paper_pull",
        help="Local paper fleet directory (instance subfolders)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "reports" / "full_trading_report_20260716",
    )
    parser.add_argument("--pull", action="store_true", help="rsync paper data from VPS first")
    parser.add_argument("--vps-host", default="207.246.96.45")
    args = parser.parse_args()

    if args.pull:
        rsync_from_vps(args.paper_dir, args.vps_host)

    commit = "unknown"
    try:
        commit = (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT)
            .decode()
            .strip()
        )
    except subprocess.CalledProcessError:
        pass

    pulled_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report = build_report(
        args.paper_dir,
        args.out_dir,
        vps_host=args.vps_host,
        main_commit=commit,
        pulled_at=pulled_at,
    )
    print(render_text(report))
    print(f"\nWrote bundle → {args.out_dir}")


if __name__ == "__main__":
    main()
