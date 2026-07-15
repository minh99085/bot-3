"""Hard market scope — Hermes Paper trades ONLY BTC 5m/15m Up/Down.

Preferred seed slugs (user-specified):
  - btc-updown-15m-1784113200
  - btc-updown-5m-1784113500

Windows rotate every 5m/15m. Discovery follows the *currently active*
window of each series and never touches any other Polymarket event.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

# Canonical series IDs (substrategy / lessons / dashboard)
SERIES_5M = "btc_updown_5m"
SERIES_15M = "btc_updown_15m"
ALLOWED_SERIES = frozenset({SERIES_5M, SERIES_15M})

# User-specified preferred windows (used when still active)
PREFERRED_SLUGS = (
    "btc-updown-15m-1784113200",
    "btc-updown-5m-1784113500",
)

SLUG_RE = re.compile(r"^btc-updown-(5m|15m)-(\d+)$")

# Fast-market sizing defaults (paper, $2000 bankroll)
COLD_START_SIZE_PCT = 0.005  # 0.5% of bankroll (~$10)
MAX_SIZE_PCT_FAST = 0.02  # 2% cap until lessons prove edge
MIN_SIZE_PCT_FAST = 0.005
MIN_LIVE_EV_FAST = 0.04  # slightly lower than slow markets (fees dominate)
MIN_ORACLE_ALIGN = 0.55


@dataclass(frozen=True)
class ScopedMarket:
    series: str  # btc_updown_5m | btc_updown_15m
    timeframe: str  # 5m | 15m
    slug: str
    window_ts: int


def scope_enabled() -> bool:
    return os.environ.get("HERMES_SCOPE_BTC_UPDOWN_ONLY", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def preferred_slugs() -> tuple[str, ...]:
    raw = os.environ.get("HERMES_BTC_UPDOWN_SLUGS", "").strip()
    if raw:
        return tuple(s.strip() for s in raw.split(",") if s.strip())
    return PREFERRED_SLUGS


def parse_slug(slug: str) -> Optional[ScopedMarket]:
    m = SLUG_RE.match((slug or "").strip().lower())
    if not m:
        return None
    tf = m.group(1)
    ts = int(m.group(2))
    series = SERIES_5M if tf == "5m" else SERIES_15M
    return ScopedMarket(series=series, timeframe=tf, slug=slug.strip().lower(), window_ts=ts)


def is_allowed_slug(slug: str) -> bool:
    return parse_slug(slug) is not None


def is_allowed_series(series: str) -> bool:
    return series in ALLOWED_SERIES


def series_from_record(record: dict) -> Optional[str]:
    """Resolve btc_updown_5m vs btc_updown_15m without substring false positives.

    ``btc_updown_5m`` must NOT match ``btc_updown_15m`` records.
    """
    meta = record.get("meta") or {}
    if not isinstance(meta, dict):
        meta = {}

    ms = str(record.get("market_series") or meta.get("market_series") or "").strip()
    if ms in ALLOWED_SERIES:
        return ms

    slug = str(
        record.get("slug")
        or record.get("market_slug")
        or meta.get("slug")
        or ""
    ).strip().lower()
    if slug:
        sm = parse_slug(slug)
        if sm:
            return sm.series

    sid = str(record.get("substrategy_id") or meta.get("substrategy_id") or "").strip()
    if sid:
        head = sid.split("|", 1)[0].strip()
        if head in ALLOWED_SERIES:
            return head

    tf = str(record.get("timeframe") or meta.get("timeframe") or "").strip().lower()
    if tf == "5m":
        return SERIES_5M
    if tf == "15m":
        return SERIES_15M

    return None


def record_belongs_to_series(record: dict, series: str) -> bool:
    """True when a ledger / pretrade row belongs to one scoped lane."""
    resolved = series_from_record(record)
    return resolved == series if resolved else False


def series_from_slug(slug: str) -> Optional[str]:
    sm = parse_slug(slug)
    return sm.series if sm else None


def window_step_seconds(timeframe: str) -> int:
    return 300 if timeframe == "5m" else 900


def current_window_ts(timeframe: str, *, now: Optional[float] = None) -> int:
    """Floor UTC epoch to the current open window start."""
    step = window_step_seconds(timeframe)
    t = int(now if now is not None else datetime.now(timezone.utc).timestamp())
    return (t // step) * step


def candidate_slugs_for_series(timeframe: str, *, now: Optional[float] = None) -> list[str]:
    """Preferred slug (if matching series) + nearby rolling windows for 24/7."""
    step = window_step_seconds(timeframe)
    base = current_window_ts(timeframe, now=now)
    out: list[str] = []
    # Prefer user seeds first when they match this timeframe
    for pref in preferred_slugs():
        sm = parse_slug(pref)
        if sm and sm.timeframe == timeframe:
            out.append(sm.slug)
    # Current + next few windows (fast markets expire quickly)
    for off in (-1, 0, 1, 2, 3):
        slug = f"btc-updown-{timeframe}-{base + off * step}"
        if slug not in out:
            out.append(slug)
    return out


def all_discovery_slugs(*, now: Optional[float] = None) -> list[str]:
    """Ordered slug candidates for both allowed series only."""
    seen: set[str] = set()
    ordered: list[str] = []
    for tf in ("15m", "5m"):
        for slug in candidate_slugs_for_series(tf, now=now):
            if slug not in seen:
                seen.add(slug)
                ordered.append(slug)
    return ordered
