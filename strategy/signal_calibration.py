"""Self-improving fusion weights for the advanced ensemble.

Upstream: hermes/lessons_engine.py (call after settlements),
strategy/advanced_signals.py (consumes overrides).

After every N resolved paper trades, re-estimate swarm/market blend and
per-component reliability via rolling Brier / win-rate. Weak signals are
down-weighted automatically. Never touches STRICT_REAL_FREEZE gates.
"""

from __future__ import annotations

import json
import logging
import math
import os
import threading
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
DEFAULT_PATH = Path(
    os.environ.get("HERMES_ADVANCED_WEIGHTS_PATH", "data/paper/advanced_weights.json")
)
RECALIBRATE_EVERY = int(os.environ.get("HERMES_ADVANCED_RECALIB_N", "25"))


def _default_state() -> dict[str, Any]:
    return {
        "n_resolved": 0,
        "swarm_weight": 0.70,
        "market_blend": 0.30,
        "component_brier": {},
        "component_wr": {},
        "model_brier": {"n": 0, "sum_sq": 0.0},
        "last_recalibrated_at_n": 0,
        "component_reliability": {},
    }


def _load(path: Path = DEFAULT_PATH) -> dict[str, Any]:
    if not path.is_file():
        return _default_state()
    try:
        with path.open() as f:
            raw = json.load(f) or {}
        base = _default_state()
        base.update(raw)
        return base
    except Exception as exc:  # noqa: BLE001
        logger.warning("signal_calibration load failed: %s", exc)
        return _default_state()


def _save(state: dict[str, Any], path: Path = DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    tmp.replace(path)


def load_fusion_overrides(path: Path = DEFAULT_PATH) -> dict[str, float]:
    """Return {swarm_weight, market_blend} if calibrated; else empty."""
    with _LOCK:
        st = _load(path)
    if int(st.get("n_resolved", 0)) < RECALIBRATE_EVERY:
        return {}
    return {
        "swarm_weight": float(st.get("swarm_weight", 0.70)),
        "market_blend": float(st.get("market_blend", 0.30)),
    }


def record_resolved_trade(
    *,
    p_up: float,
    resolved_yes: bool,
    components: Optional[dict[str, float]] = None,
    path: Path = DEFAULT_PATH,
) -> dict[str, Any]:
    """Update rolling Brier / WR; maybe re-fit fusion blend.

    ``p_up`` is model P(UP) at entry; ``components`` are sub-signal P(UP).
    """
    y = 1.0 if resolved_yes else 0.0
    with _LOCK:
        st = _load(path)
        st["n_resolved"] = int(st.get("n_resolved", 0)) + 1
        gb = st.setdefault("model_brier", {"n": 0, "sum_sq": 0.0})
        gb["n"] = int(gb["n"]) + 1
        gb["sum_sq"] = float(gb["sum_sq"]) + (float(p_up) - y) ** 2

        for name, p in (components or {}).items():
            cb = st.setdefault("component_brier", {}).setdefault(
                name, {"n": 0, "sum_sq": 0.0}
            )
            cb["n"] = int(cb["n"]) + 1
            cb["sum_sq"] = float(cb["sum_sq"]) + (float(p) - y) ** 2
            cw = st.setdefault("component_wr", {}).setdefault(name, {"n": 0, "wins": 0})
            cw["n"] = int(cw["n"]) + 1
            if (float(p) >= 0.5) == resolved_yes:
                cw["wins"] = int(cw["wins"]) + 1

        n = int(st["n_resolved"])
        if n - int(st.get("last_recalibrated_at_n", 0)) >= RECALIBRATE_EVERY:
            st = _recalibrate(st)
            st["last_recalibrated_at_n"] = n
            logger.info(
                "signal_calibration: recalibrated at n=%d swarm=%.2f market=%.2f",
                n,
                st["swarm_weight"],
                st["market_blend"],
            )
        _save(st, path)
        return st


def _recalibrate(st: dict[str, Any]) -> dict[str, Any]:
    """Walk-forward: higher model Brier → lean more on market blend."""
    gb = st.get("model_brier") or {}
    n = int(gb.get("n") or 0)
    if n < 10:
        return st
    brier = float(gb.get("sum_sq", 0.0)) / n
    # Brier ~0.25 random; ≤0.15 good → swarm ∈ [0.55, 0.80]
    swarm = 0.80 - 1.0 * max(0.0, min(0.25, brier - 0.10))
    swarm = float(max(0.55, min(0.80, swarm)))
    st["swarm_weight"] = swarm
    st["market_blend"] = round(1.0 - swarm, 4)

    reliability: dict[str, float] = {}
    for name, cb in (st.get("component_brier") or {}).items():
        cn = int(cb.get("n") or 0)
        if cn < 5:
            continue
        cbrier = float(cb.get("sum_sq", 0.0)) / cn
        reliability[name] = float(math.exp(-4.0 * cbrier))
    st["component_reliability"] = reliability
    return st


def maybe_recalibrate_from_settlements(
    settlements: list[Any],
    path: Path = DEFAULT_PATH,
) -> int:
    """Hook for lessons_engine_tick — ingest resolved trades with model_q meta."""
    n = 0
    for stl in settlements or []:
        try:
            meta = getattr(stl, "meta", None) or {}
            if not isinstance(meta, dict):
                meta = {}
            # Prefer explicit P(UP)
            p_up = meta.get("model_q")
            if p_up is None:
                p_up = meta.get("cex_implied_up")
            if p_up is None:
                continue
            if "resolved_yes" in meta:
                resolved_yes = bool(meta["resolved_yes"])
            else:
                won = getattr(stl, "won", None)
                if won is None:
                    continue
                side = str(meta.get("enhanced_side") or meta.get("side") or "UP").upper()
                # won is relative to traded side
                if side in ("DOWN", "NO"):
                    resolved_yes = not bool(won)
                else:
                    resolved_yes = bool(won)
            comps = meta.get("advanced_components")
            if not isinstance(comps, dict):
                comps = None
            record_resolved_trade(
                p_up=float(p_up),
                resolved_yes=resolved_yes,
                components=comps,
                path=path,
            )
            n += 1
        except Exception as exc:  # noqa: BLE001
            logger.debug("calibration skip settlement: %s", exc)
    return n
