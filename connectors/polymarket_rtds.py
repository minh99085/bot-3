"""Polymarket Real-Time Data Streams (RTDS) — cross-check on the settle price.

wss://ws-live-data.polymarket.com carries the crypto price stream Polymarket
uses for its own UI/resolution context (symbol 'btc/usd', 'eth/usd'). We use
it ONLY as an independent cross-check that the Chainlink strike/close we
settle on matches what the market itself is showing — never as the settlement
authority (that stays Chainlink Data Streams per A1).

The frame parser and cross-check are pure/injectable so they unit-test
offline; the live WS connect runs on the VPS.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)

RTDS_WSS = "wss://ws-live-data.polymarket.com"
SYMBOLS = {"BTC": "btc/usd", "ETH": "eth/usd"}


@dataclass
class RtdsTick:
    symbol: str
    price: float
    ts: Optional[float] = None


def subscribe_message(asset: str) -> str:
    """Subscription frame for an asset's price symbol."""
    sym = SYMBOLS.get(asset.upper(), asset.lower())
    return json.dumps({"action": "subscribe", "subscriptions": [{"topic": "prices", "symbol": sym}]})


def parse_frame(raw: Any) -> Optional[RtdsTick]:
    """Parse one RTDS text frame → RtdsTick (None if not a price tick)."""
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", "ignore")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None
    if not isinstance(raw, dict):
        return None
    payload = raw.get("payload") or raw.get("data") or raw
    sym = str(payload.get("symbol") or raw.get("symbol") or "").lower()
    price = None
    for k in ("price", "value", "mid", "p"):
        if payload.get(k) is not None:
            try:
                price = float(payload[k])
            except (TypeError, ValueError):
                price = None
            break
    if price is None or price <= 0:
        return None
    ts = None
    for k in ("timestamp", "ts", "time"):
        if payload.get(k) is not None:
            try:
                t = float(payload[k])
                ts = t / 1000.0 if t > 1e12 else t
            except (TypeError, ValueError):
                ts = None
            break
    return RtdsTick(symbol=sym, price=price, ts=ts)


def cross_check(oracle_price: float, rtds_price: float, *, tol_bps: float = 15.0) -> dict[str, Any]:
    """Compare a Chainlink strike/close vs the RTDS price at the same instant."""
    if oracle_price <= 0 or rtds_price <= 0:
        return {"ok": False, "reason": "missing_price", "diff_bps": None}
    diff_bps = abs(oracle_price - rtds_price) / oracle_price * 10_000.0
    ok = diff_bps <= tol_bps
    if not ok:
        logger.warning(
            "RTDS cross-check MISMATCH: oracle=%.2f rtds=%.2f diff=%.1fbps > %.1f",
            oracle_price, rtds_price, diff_bps, tol_bps,
        )
    return {"ok": ok, "diff_bps": diff_bps, "oracle": oracle_price, "rtds": rtds_price}
