"""TV price-pattern learner — pre/post-trade loop for all lanes.

Learns Wilson win-rate by ``lane|asset|short_pattern|alignment`` from settled
fills, then soft-sizes pre-trade. Uses TV signal-history patterns (bar-close or
RSI-div price-path fallback) — never raw GB trade dumps.
"""

from __future__ import annotations

import math
import time
from typing import Optional


def _wilson_lower(wins: int, n: int, z: float = 1.64) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = p + z2 / (2.0 * n)
    spread = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * n)) / n)
    return max(0.0, (centre - spread) / denom)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))


def pattern_key(
    *,
    lane: str = "15m",
    asset: str = "btc",
    short_pattern: Optional[str] = None,
    alignment: Optional[str] = None,
) -> Optional[str]:
    pat = str(short_pattern or "").strip().lower() or None
    if not pat or pat in ("none", "unknown", "empty"):
        return None
    al = str(alignment or "none").strip().lower() or "none"
    return "%s|%s|%s|%s" % (
        str(lane or "15m").lower(),
        str(asset or "btc").lower(),
        pat,
        al,
    )


def pattern_key_from_research(research: Optional[dict], *, lane: str, asset: str) -> Optional[str]:
    rt = research or {}
    # Prefer explicit pattern tags from binary_intel / chart lean
    pat = (
        rt.get("tv_price_short_pattern")
        or rt.get("tv_15m_short_pattern")
        or rt.get("tv_1h_short_pattern")
    )
    al = (
        rt.get("tv_price_alignment")
        or rt.get("tv_15m_chart_alignment")
        or rt.get("tv_1h_chart_alignment")
        or "none"
    )
    return pattern_key(lane=lane, asset=asset, short_pattern=pat, alignment=al)


class TvPricePatternLearner:
    """Aggregated pattern cells — ~KB state, all lanes."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        min_samples: int = 8,
        target_wr: float = 0.58,
        kill_wr: float = 0.45,
        boost_mult: float = 1.12,
        haircut_mult: float = 0.55,
        max_cells: int = 80,
    ):
        self.enabled = bool(enabled)
        self.min_samples = int(min_samples)
        self.target_wr = float(target_wr)
        self.kill_wr = float(kill_wr)
        self.boost_mult = float(boost_mult)
        self.haircut_mult = float(haircut_mult)
        self.max_cells = int(max_cells)
        self._cells: dict[str, dict] = {}
        self._last_action: Optional[str] = None
        self._last_ts: Optional[float] = None

    def record_settled(
        self,
        *,
        won: bool,
        pnl_usd: float = 0.0,
        key: Optional[str] = None,
        lane: str = "15m",
        asset: str = "btc",
        short_pattern: Optional[str] = None,
        alignment: Optional[str] = None,
        now: Optional[float] = None,
    ) -> Optional[dict]:
        if not self.enabled:
            return None
        k = key or pattern_key(
            lane=lane, asset=asset, short_pattern=short_pattern, alignment=alignment)
        if not k:
            return None
        cell = self._cells.setdefault(k, {"n": 0, "wins": 0, "pnl_usd": 0.0})
        cell["n"] = int(cell.get("n") or 0) + 1
        if won:
            cell["wins"] = int(cell.get("wins") or 0) + 1
        cell["pnl_usd"] = round(float(cell.get("pnl_usd") or 0.0) + float(pnl_usd or 0.0), 4)
        cell["last_ts"] = float(now if now is not None else time.time())
        self._trim()
        self._last_ts = cell["last_ts"]
        return {"key": k, **cell}

    def size_mult(self, key: Optional[str]) -> float:
        """Soft size from learned pattern WR. 1.0 until min_samples."""
        if not self.enabled or not key:
            return 1.0
        cell = self._cells.get(key)
        if not cell:
            return 1.0
        n = int(cell.get("n") or 0)
        if n < self.min_samples:
            return 1.0
        wins = int(cell.get("wins") or 0)
        wr = wins / n
        wlb = _wilson_lower(wins, n)
        if wlb >= self.target_wr or wr >= self.target_wr + 0.05:
            return self.boost_mult
        if wlb < self.kill_wr or wr < self.kill_wr:
            return self.haircut_mult
        if wr >= self.target_wr:
            return _clamp(1.0 + 0.5 * (self.boost_mult - 1.0), 1.0, self.boost_mult)
        return 1.0

    def heuristic_size_mult(
        self,
        *,
        side: Optional[str],
        trade_lean: Optional[str],
        alignment: Optional[str],
    ) -> float:
        """Cold-start soft bias from live pattern lean (before cells mature)."""
        if not self.enabled:
            return 1.0
        side_l = str(side or "").lower()
        lean = str(trade_lean or "").lower()
        if side_l not in ("up", "down") or lean not in ("up", "down"):
            return 1.0
        al = str(alignment or "").lower()
        agrees = side_l == lean
        if agrees and al == "aligned":
            return 1.10
        if agrees and al in ("short_only", "divergent"):
            return 1.0 if al == "short_only" else 0.85
        if not agrees and al == "aligned":
            return 0.50
        if not agrees:
            return 0.65
        return 1.0

    def effective_size_mult(
        self,
        *,
        key: Optional[str],
        side: Optional[str] = None,
        trade_lean: Optional[str] = None,
        alignment: Optional[str] = None,
    ) -> float:
        learned = self.size_mult(key)
        if key and key in self._cells and int(self._cells[key].get("n") or 0) >= self.min_samples:
            return learned
        return self.heuristic_size_mult(
            side=side, trade_lean=trade_lean, alignment=alignment)

    def lessons_for_book(self) -> list:
        out = []
        for key, cell in self._cells.items():
            n = int(cell.get("n") or 0)
            if n < self.min_samples:
                continue
            wins = int(cell.get("wins") or 0)
            wr = wins / n
            wlb = _wilson_lower(wins, n)
            if wlb >= self.target_wr:
                out.append((
                    "exploit",
                    "tv_pattern:%s" % key,
                    "TV price pattern %s → WR %.0f%% (n=%d, wlb=%.2f); size up when aligned."
                    % (key, 100 * wr, n, wlb),
                ))
            elif wr < self.kill_wr:
                out.append((
                    "avoid",
                    "tv_pattern:%s" % key,
                    "TV price pattern %s → WR %.0f%% (n=%d); haircut / skip."
                    % (key, 100 * wr, n),
                ))
        return out[:12]

    def report(self) -> dict:
        cells_out = {}
        for k, c in list(self._cells.items())[:40]:
            n = int(c.get("n") or 0)
            wins = int(c.get("wins") or 0)
            cells_out[k] = {
                "n": n,
                "wins": wins,
                "wr": round(wins / n, 4) if n else None,
                "wilson_lb": round(_wilson_lower(wins, n), 4) if n else None,
                "pnl_usd": c.get("pnl_usd"),
                "size_mult": self.size_mult(k),
            }
        return {
            "enabled": self.enabled,
            "min_samples": self.min_samples,
            "n_cells": len(self._cells),
            "cells": cells_out,
            "last_action": self._last_action,
            "last_ts": self._last_ts,
        }

    def _trim(self) -> None:
        if len(self._cells) <= self.max_cells:
            return
        # Drop lowest-n oldest cells
        ranked = sorted(
            self._cells.items(),
            key=lambda kv: (int(kv[1].get("n") or 0), float(kv[1].get("last_ts") or 0.0)),
        )
        for k, _ in ranked[: max(0, len(self._cells) - self.max_cells)]:
            self._cells.pop(k, None)

    def to_state(self) -> dict:
        return {
            "enabled": self.enabled,
            "min_samples": self.min_samples,
            "cells": dict(self._cells),
            "last_action": self._last_action,
            "last_ts": self._last_ts,
        }

    def load_state(self, data: dict) -> None:
        if not data:
            return
        self._cells = {
            str(k): dict(v) for k, v in (data.get("cells") or {}).items()
            if isinstance(v, dict)
        }
        self._last_action = data.get("last_action")
        self._last_ts = data.get("last_ts")
        if data.get("min_samples") is not None:
            try:
                self.min_samples = int(data["min_samples"])
            except (TypeError, ValueError):
                pass
        self._trim()

    def merge_cells(self, offline: dict) -> int:
        """Richer-wins merge from offline priors (lessons export)."""
        n_merged = 0
        for k, stats in (offline or {}).items():
            if not isinstance(stats, dict):
                continue
            off_n = int(stats.get("n") or stats.get("trades") or 0)
            if off_n <= 0:
                continue
            cur = self._cells.get(str(k))
            cur_n = int((cur or {}).get("n") or 0)
            if cur is None or cur_n < off_n:
                self._cells[str(k)] = {
                    "n": off_n,
                    "wins": int(stats.get("wins") or 0),
                    "pnl_usd": round(float(stats.get("pnl_usd") or 0.0), 4),
                    "last_ts": float(stats.get("last_ts") or time.time()),
                }
                n_merged += 1
        self._trim()
        if n_merged:
            self._last_action = "merge_offline"
            self._last_ts = time.time()
        return n_merged
