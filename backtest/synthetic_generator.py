"""SyntheticDataGenerator — path-based crypto up/down universe (non-circular).

PLUMBING SANITY CHECK ONLY. Synthetic results say nothing about real edge;
the go/no-go metric is real out-of-sample performance after costs.

Honest structure (vs the old ``q = true_q + noise`` circularity):

  1. Simulate a CEX price path per market (GBM ticks, optional drift regime,
     block-correlated via a shared factor).
  2. The OUTCOME is the path itself: resolved_yes = close > strike.
  3. The MARKET price p is the no-drift-knowledge fair probability given the
     current path state, plus crowd noise. It never sees the future.
  4. The MODEL q is produced by running the SAME live pipeline
     (``strategy.advanced_signals.ensemble_cex_implied_up``) on the simulated
     path history — momentum computed exactly like
     ``connectors.cex_realtime`` does. q is NOT a function of true_q; the
     model is free to be wrong or worse than the market.
  5. ``null_edge=True`` feeds the ensemble a statistically identical DECOY
     path that is independent of the outcome path. q then carries zero
     information — the null-edge guardrail test asserts WR collapses to
     ~coinflip after costs.

``true_q`` on each DecisionPoint is the true conditional P(up) given the
path state AND the hidden drift — a diagnostic only, never shown to the
strategy and never used to build p or q.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np
from scipy.stats import norm

from models.config import EnhancedMispriceConfig, load_enhanced_config
from models.market import DecisionPoint, MarketSnapshot
from strategy.advanced_signals import ensemble_cex_implied_up

logger = logging.getLogger(__name__)

SEC_PER_YEAR = 31_536_000.0  # crypto trades 24/7
TICK_SEC = 1.0
PRE_TICKS = 240  # live feed keeps ~240 points (cex_realtime max_points=240)
WINDOW_CHOICES = (300.0, 900.0)  # 5m / 15m up-down windows
WINDOW_WEIGHTS = (0.7, 0.3)
ASSETS = ("btc", "eth", "sol", "xrp")
ASSET_REF_PRICE = {"btc": 60_000.0, "eth": 3_000.0, "sol": 150.0, "xrp": 0.60}
TREND_PROB = 0.35  # fraction of windows with real drift
# Cumulative drift over a window, in sigmas (Sharpe). Detectable, never dominant.
TREND_SHARPE_LO, TREND_SHARPE_HI = 0.2, 1.0
# The crowd watches the same chart: the market prices this fraction of the
# drift (drawn per market). The residual is the only structural edge left.
DRIFT_AWARENESS_LO, DRIFT_AWARENESS_HI = 0.6, 1.0
MOMENTUM_SCALE = 0.0015  # same normalization as connectors.cex_realtime


@dataclass
class SyntheticUniverse:
    """Full generated universe + flat decision stream."""

    markets_meta: list[dict]
    decisions: list[DecisionPoint]
    seed: int
    n_markets: int
    block_corr: float

    def chronological(self) -> list[DecisionPoint]:
        return sorted(self.decisions, key=lambda d: (d.decision_time, d.decision_id))


def _live_momentum(path: np.ndarray, idx: int) -> float:
    """Replicate connectors.cex_realtime momentum: blended 30/60/180s returns."""

    def ret_over(sec: int) -> float:
        j = idx - int(sec / TICK_SEC)
        if j < 0 or path[j] <= 0:
            return 0.0
        return float(path[idx] / path[j] - 1.0)

    raw = 0.5 * ret_over(30) + 0.3 * ret_over(60) + 0.2 * ret_over(180)
    return float(max(-1.0, min(1.0, raw / MOMENTUM_SCALE)))


def _fair_prob(spot: float, strike: float, sigma_1s: float, ticks_left: float, mu_1s: float = 0.0) -> float:
    """P(S_T > K) for the remaining window under GBM with per-tick mu/sigma."""
    if spot <= 0 or strike <= 0 or ticks_left <= 0:
        return 0.5
    sig = max(1e-9, sigma_1s) * math.sqrt(ticks_left)
    d = (math.log(spot / strike) + mu_1s * ticks_left) / sig
    return float(np.clip(norm.cdf(d), 1e-4, 1.0 - 1e-4))


class SyntheticDataGenerator:
    """Path-based synthetic market factory. Sanity harness, not a scoreboard."""

    def __init__(
        self,
        config: Optional[EnhancedMispriceConfig] = None,
        *,
        seed: Optional[int] = None,
    ) -> None:
        self.cfg = config or load_enhanced_config()
        self.seed = int(seed if seed is not None else self.cfg.synthetic_seed)
        self.rng = np.random.default_rng(self.seed)

    def _draw_drift(self, sigma_1s: float, w_ticks: int) -> float:
        """Per-tick drift such that cumulative window Sharpe is modest."""
        if self.rng.random() >= TREND_PROB:
            return 0.0
        sharpe = float(self.rng.uniform(TREND_SHARPE_LO, TREND_SHARPE_HI))
        direction = float(self.rng.choice((-1.0, 1.0)))
        return direction * sigma_1s * sharpe / math.sqrt(max(1, w_ticks))

    def _make_path(
        self,
        n_ticks: int,
        s0: float,
        sigma_1s: float,
        mu_1s: float,
        factor: Optional[np.ndarray],
        corr: float,
    ) -> np.ndarray:
        eps = self.rng.normal(size=n_ticks)
        if factor is not None and corr > 0:
            z = math.sqrt(corr) * factor + math.sqrt(1.0 - corr) * eps
        else:
            z = eps
        rets = mu_1s + sigma_1s * z
        return s0 * np.exp(np.cumsum(rets))

    def generate(
        self,
        n_markets: Optional[int] = None,
        *,
        decision_fracs: Optional[Sequence[float]] = None,
        null_edge: bool = False,
    ) -> SyntheticUniverse:
        cfg = self.cfg
        n = int(n_markets if n_markets is not None else cfg.synthetic_n_markets)
        if n_markets is None:
            n = int(min(cfg.synthetic_n_max, max(cfg.synthetic_n_min, n)))
        else:
            n = int(min(cfg.synthetic_n_max, max(50, n)))
        fracs = [f for f in (decision_fracs or cfg.decision_fracs) if 0.02 <= f <= 0.98]
        if len(fracs) < 2:
            fracs = [0.30, 0.60, 0.85]

        block_size = max(2, int(cfg.block_size))
        corr = float(np.clip(cfg.block_corr, 0.0, 0.95))
        n_blocks = int(np.ceil(n / block_size))

        markets_meta: list[dict] = []
        decisions: list[DecisionPoint] = []

        i = 0
        for b in range(n_blocks):
            take = min(block_size, n - i)
            # Whole block shares one window (same asset-time neighborhood)
            window_sec = float(self.rng.choice(WINDOW_CHOICES, p=WINDOW_WEIGHTS))
            w_ticks = int(window_sec / TICK_SEC)
            n_ticks = PRE_TICKS + w_ticks
            start_day = float(self.rng.uniform(0.0, 60.0))
            factor = self.rng.normal(size=n_ticks)
            asset = ASSETS[b % len(ASSETS)]
            s0 = ASSET_REF_PRICE[asset] * float(self.rng.lognormal(0.0, 0.05))

            for k in range(take):
                mid = f"syn_{i:05d}"
                sigma_ann = float(np.clip(self.rng.lognormal(math.log(0.55), 0.35), 0.25, 1.5))
                sigma_1s = sigma_ann / math.sqrt(SEC_PER_YEAR)
                mu_1s = self._draw_drift(sigma_1s, w_ticks)
                # Crowd prices most of the drift; residual is the honest edge.
                mu_seen = mu_1s * float(
                    self.rng.uniform(DRIFT_AWARENESS_LO, DRIFT_AWARENESS_HI)
                )

                path = self._make_path(n_ticks, s0, sigma_1s, mu_1s, factor, corr)
                open_i = PRE_TICKS
                strike = float(path[open_i])
                close = float(path[-1])
                resolved_yes = bool(close > strike)

                # Decoy path for the null-edge harness: same statistics,
                # zero information about the real outcome path.
                if null_edge:
                    decoy_mu = self._draw_drift(sigma_1s, w_ticks)
                    model_path = self._make_path(n_ticks, s0, sigma_1s, decoy_mu, None, 0.0)
                    model_strike = float(model_path[open_i])
                else:
                    model_path = path
                    model_strike = strike

                liquidity = float(self.rng.lognormal(mean=8.2, sigma=1.1))
                volume = liquidity * float(self.rng.uniform(0.4, 4.0))

                for frac in fracs:
                    di = open_i + max(1, int(round(frac * w_ticks)))
                    di = min(di, n_ticks - 2)
                    ticks_left = float((n_ticks - 1) - di)
                    remaining_frac = ticks_left / float(w_ticks)

                    spot = float(path[di])
                    # Market: near-posterior price. The crowd sees the same
                    # chart; its only blind spots are the residual unpriced
                    # drift and a SMALL logit-space noise. Large noise would
                    # hand a winner's-curse harvest to any strategy that
                    # conditions on stretched p — even an uninformed one —
                    # which is exactly what the null-edge guardrail forbids.
                    fair_mkt = _fair_prob(spot, strike, sigma_1s, ticks_left, mu_seen)
                    noise_logit = 0.5 * cfg.market_noise * (0.35 + 0.65 * remaining_frac)
                    logit = math.log(fair_mkt / (1.0 - fair_mkt)) + float(
                        self.rng.normal(0.0, noise_logit)
                    )
                    p = float(np.clip(1.0 / (1.0 + math.exp(-logit)), 0.02, 0.98))
                    # Diagnostic truth: conditional P(up) given state AND drift
                    true_q = _fair_prob(spot, strike, sigma_1s, ticks_left, mu_1s)

                    # Model: the live pipeline, fed only path history.
                    hist = model_path[max(0, di - PRE_TICKS) : di + 1]
                    times = np.arange(hist.size, dtype=float) * TICK_SEC
                    mom = _live_momentum(model_path, di)
                    res = ensemble_cex_implied_up(
                        prices=hist,
                        times=times,
                        momentum=mom,
                        timeframe="5m" if window_sec <= 300 else "15m",
                        pm_implied_up=p,
                        spot=float(model_path[di]),
                        strike=model_strike,
                        seconds_to_resolution=ticks_left * TICK_SEC,
                    )
                    q = float(np.clip(res.q, 0.02, 0.98))

                    decisions.append(
                        DecisionPoint(
                            market_id=mid,
                            decision_id=f"{mid}_f{int(frac * 100):02d}",
                            decision_time=start_day + (di - open_i) * TICK_SEC / 86400.0,
                            lifetime_frac=float(frac),
                            category="crypto",
                            block_id=b,
                            days_to_resolution=ticks_left * TICK_SEC / 86400.0,
                            p=p,
                            q=q,
                            liquidity_usd=liquidity,
                            volume_24h=volume,
                            true_q=true_q,
                            resolved_yes=resolved_yes,
                            resolution_time=start_day + window_sec / 86400.0,
                            meta={
                                "synthetic": True,
                                "seed": self.seed,
                                "asset": asset,
                                "q_source": "null_noise" if null_edge else "live_ensemble",
                                "ensemble_regime": res.regime,
                                "ensemble_fallback": res.used_fallback,
                            },
                        )
                    )

                markets_meta.append(
                    {
                        "market_id": mid,
                        "true_q": float(_fair_prob(strike, strike, sigma_1s, float(w_ticks), mu_1s)),
                        "resolved_yes": resolved_yes,
                        "block_id": b,
                        "category": "crypto",
                        "asset": asset,
                        "days_to_resolution_full": window_sec / 86400.0,
                        "window_sec": window_sec,
                        "liquidity_usd": liquidity,
                        "volume_24h": volume,
                        "strike": strike,
                        "close": close,
                        "sigma_ann": sigma_ann,
                        "mu_1s": mu_1s,
                        "null_edge": bool(null_edge),
                    }
                )
                i += 1

        logger.info(
            "SyntheticDataGenerator [SANITY-ONLY]: n_markets=%d decisions=%d blocks=%d "
            "corr=%.2f seed=%d null_edge=%s",
            n,
            len(decisions),
            n_blocks,
            corr,
            self.seed,
            null_edge,
        )
        return SyntheticUniverse(
            markets_meta=markets_meta,
            decisions=decisions,
            seed=self.seed,
            n_markets=n,
            block_corr=corr,
        )


def generate_synthetic_markets(
    n: int | None = None,
    *,
    config: EnhancedMispriceConfig | None = None,
    seed: int | None = None,
) -> list[MarketSnapshot]:
    """Backward-compatible flat list (one snapshot per decision point)."""
    gen = SyntheticDataGenerator(config=config, seed=seed)
    uni = gen.generate(n_markets=n)
    return [d.as_snapshot() for d in uni.chronological()]


def estimate_brier(markets: list[MarketSnapshot]) -> float:
    pairs = [(m.q, m.resolved_yes) for m in markets if m.resolved_yes is not None]
    if not pairs:
        return 1.0
    return float(np.mean([(q - (1.0 if y else 0.0)) ** 2 for q, y in pairs]))


def estimate_brier_from_decisions(decisions: list[DecisionPoint]) -> float:
    if not decisions:
        return 1.0
    return float(
        np.mean([(d.q - (1.0 if d.resolved_yes else 0.0)) ** 2 for d in decisions])
    )
