"""A2 — latency-edge instrumentation (MEASURE only, never changes strategy).

The barrier thesis is a CEX/oracle-leads-Polymarket LATENCY edge. But a 4s
REST loop on a VPS may be the slowest participant: if Polymarket has already
repriced to reflect the oracle move before our decision, the edge we book in
paper is illusory. This records the four timestamps per candidate and a
``stale_edge`` verdict, so we can compute a fleet-wide stale_edge_rate BEFORE
trusting any lane.

It writes one JSONL row per evaluated candidate and never raises into the
trading path (callers wrap it).
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _to_epoch(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        f = float(v)
        return f / 1000.0 if f > 1e12 else f
    if isinstance(v, datetime):
        return v.timestamp()
    if isinstance(v, str):
        s = v.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(s).timestamp()
        except ValueError:
            try:
                return float(v)
            except ValueError:
                return None
    return None


@dataclass
class EdgeLatencyRecord:
    slug: str
    asset: str
    decision_ts: float
    oracle_ts: Optional[float]
    cex_ts: Optional[float]
    pm_updated_ts: Optional[float]
    oracle_spot: float
    cex_mid: float
    pm_implied_up: float
    model_q: float
    dislocation: float
    # verdicts
    pm_fresher_than_oracle: Optional[bool]  # PM updated at/after the oracle tick we traded
    pm_agrees_direction: bool               # PM already on our q's side of 0.5
    stale_edge: bool                        # edge likely already priced by PM


def classify(rec_kwargs: dict[str, Any]) -> EdgeLatencyRecord:
    """Pure classifier — decides whether an edge looks already-priced."""
    decision_ts = float(rec_kwargs.get("decision_ts") or 0.0)
    oracle_ts = _to_epoch(rec_kwargs.get("oracle_ts"))
    cex_ts = _to_epoch(rec_kwargs.get("cex_ts"))
    pm_ts = _to_epoch(rec_kwargs.get("pm_updated_ts"))
    p = float(rec_kwargs.get("pm_implied_up") or 0.5)
    q = float(rec_kwargs.get("model_q") or 0.5)

    # Reference tick = the freshest market data we reacted to.
    ref_ts = max([t for t in (oracle_ts, cex_ts) if t is not None], default=None)
    pm_fresher = None
    if pm_ts is not None and ref_ts is not None:
        pm_fresher = pm_ts >= ref_ts - 1.0  # PM had our info (±1s) already

    # PM already on the same side of 0.5 as our model → little to capture.
    pm_agrees = (q - 0.5) * (p - 0.5) > 0 and abs(p - 0.5) >= abs(q - 0.5) * 0.5

    # Stale edge: PM repriced at least as recently as our reference tick AND
    # already sits on our side → the "edge" is likely gone.
    stale = bool(pm_fresher) and pm_agrees
    return EdgeLatencyRecord(
        slug=str(rec_kwargs.get("slug") or ""),
        asset=str(rec_kwargs.get("asset") or ""),
        decision_ts=decision_ts,
        oracle_ts=oracle_ts,
        cex_ts=cex_ts,
        pm_updated_ts=pm_ts,
        oracle_spot=float(rec_kwargs.get("oracle_spot") or 0.0),
        cex_mid=float(rec_kwargs.get("cex_mid") or 0.0),
        pm_implied_up=p,
        model_q=q,
        dislocation=float(rec_kwargs.get("dislocation") or 0.0),
        pm_fresher_than_oracle=pm_fresher,
        pm_agrees_direction=pm_agrees,
        stale_edge=stale,
    )


def _probe_path() -> Path:
    from hermes.state_io import ledger_path

    return ledger_path(paper=True).parent / "latency_probe.jsonl"


def record_edge_latency(
    *,
    slug: str,
    asset: str,
    oracle_spot: float,
    oracle_ts: Any,
    cex_mid: float,
    cex_ts: Any,
    pm_implied_up: float,
    pm_updated_at: Any,
    model_q: float,
    dislocation: float,
) -> EdgeLatencyRecord:
    """Classify + append one candidate's latency record. Never raises upward."""
    rec = classify(
        {
            "slug": slug, "asset": asset,
            "decision_ts": datetime.now(timezone.utc).timestamp(),
            "oracle_ts": oracle_ts, "cex_ts": cex_ts, "pm_updated_ts": pm_updated_at,
            "oracle_spot": oracle_spot, "cex_mid": cex_mid,
            "pm_implied_up": pm_implied_up, "model_q": model_q,
            "dislocation": dislocation,
        }
    )
    try:
        from hermes.state_io import append_jsonl

        append_jsonl(_probe_path(), asdict(rec))
    except Exception as exc:  # noqa: BLE001
        logger.debug("latency probe write failed: %s", exc)
    return rec


def stale_edge_rate(rows: list[dict[str, Any]], *, min_dislocation: float = 0.0) -> dict[str, Any]:
    """Aggregate stale_edge_rate over probe rows (traded-signal candidates)."""
    considered = [
        r for r in rows if abs(float(r.get("dislocation") or 0.0)) >= min_dislocation
    ]
    n = len(considered)
    if n == 0:
        return {"n": 0, "stale_edge_rate": None, "pm_agrees_rate": None}
    stale = sum(1 for r in considered if r.get("stale_edge"))
    agrees = sum(1 for r in considered if r.get("pm_agrees_direction"))
    return {
        "n": n,
        "stale_edge_rate": stale / n,
        "pm_agrees_rate": agrees / n,
        "verdict": (
            "NO CAPTURABLE EDGE — PM already priced most signals"
            if stale / n >= 0.6
            else "edge plausibly capturable — proceed to A3"
        ),
    }
