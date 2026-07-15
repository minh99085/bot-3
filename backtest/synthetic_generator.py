"""SyntheticDataGenerator — production-grade synthetic Polymarket universe.

Creates 5k–20k markets with:
  - fat-tailed true_q (Beta mixture)
  - market noise that shrinks toward resolution (no look-ahead)
  - liquidity / volume distributions
  - days-to-resolution mix (3 / 14 / 45 / 120)
  - block-diagonal correlation (0.6–0.85) across related themes
  - 2–4 decision points per market (e.g. 30%, 60%, 85% of lifetime)
  - Bernoulli resolution at true_q

Consumers walk DecisionPoints chronologically. Strategy only sees p, q,
liquidity, and time — never true_q / outcome until settlement.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np
from scipy.stats import norm

from models.config import EnhancedMispriceConfig, load_enhanced_config
from models.market import DecisionPoint, MarketSnapshot

logger = logging.getLogger(__name__)

CATEGORIES_DEFAULT = ["crypto", "elections", "sports", "economics"]


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


class SyntheticDataGenerator:
    """Configurable synthetic market factory for proving 80%+ WR math."""

    def __init__(
        self,
        config: Optional[EnhancedMispriceConfig] = None,
        *,
        seed: Optional[int] = None,
    ) -> None:
        self.cfg = config or load_enhanced_config()
        self.seed = int(seed if seed is not None else self.cfg.synthetic_seed)
        self.rng = np.random.default_rng(self.seed)

    def generate(
        self,
        n_markets: Optional[int] = None,
        *,
        decision_fracs: Optional[Sequence[float]] = None,
    ) -> SyntheticUniverse:
        cfg = self.cfg
        n = int(n_markets if n_markets is not None else cfg.synthetic_n_markets)
        # Respect explicit CLI n_markets; only clamp when using config default path
        if n_markets is None:
            n = int(min(cfg.synthetic_n_max, max(cfg.synthetic_n_min, n)))
        else:
            n = int(min(cfg.synthetic_n_max, max(500, n)))
        fracs = list(decision_fracs or cfg.decision_fracs)
        if len(fracs) < 2:
            fracs = [0.30, 0.60, 0.85]

        # --- correlation blocks ---
        block_size = max(2, int(cfg.block_size))
        n_blocks = int(np.ceil(n / block_size))
        corr = float(np.clip(cfg.block_corr, 0.0, 0.95))

        # Latent Gaussian factors → correlated true probabilities via Φ
        # true_q = Φ(√ρ · Z_block + √(1-ρ) · ε_i) mixed with extreme Beta mass
        true_q = np.empty(n)
        block_ids = np.empty(n, dtype=int)
        categories = list(cfg.categories) or CATEGORIES_DEFAULT
        cat_of = []

        idx = 0
        for b in range(n_blocks):
            take = min(block_size, n - idx)
            z_b = self.rng.normal()
            eps = self.rng.normal(size=take)
            latent = np.sqrt(corr) * z_b + np.sqrt(1.0 - corr) * eps
            # Map latent → (0,1); then blend with extreme Beta for fat tails
            base = norm.cdf(latent)
            # Extreme overlay for a fraction of names in the block
            extreme_mask = self.rng.random(take) < cfg.extreme_mass
            lo = self.rng.beta(1.6, 18.0, size=take)
            hi = self.rng.beta(18.0, 1.6, size=take)
            pick_hi = self.rng.random(take) > 0.5
            extreme = np.where(pick_hi, hi, lo)
            tq = np.where(extreme_mask, extreme, base)
            # Mild pull toward block consensus (keeps correlation meaningful)
            tq = np.clip(0.85 * tq + 0.15 * float(np.mean(tq)), 0.02, 0.98)
            true_q[idx : idx + take] = tq
            block_ids[idx : idx + take] = b
            cat = categories[b % len(categories)]
            cat_of.extend([cat] * take)
            idx += take

        # Days to resolution
        days_choices = np.asarray(cfg.days_to_res_choices, dtype=float)
        weights = np.asarray(cfg.days_to_res_weights, dtype=float)
        weights = weights / weights.sum()
        days = self.rng.choice(days_choices, size=n, p=weights)

        # Liquidity / volume (lognormal) — thin books → lower liquidity_score
        liquidity = self.rng.lognormal(mean=8.2, sigma=1.1, size=n)  # ~$3.6k median
        volume = liquidity * self.rng.uniform(0.4, 4.0, size=n)

        # Start times staggered so decisions interleave across markets
        start_day = self.rng.uniform(0.0, 60.0, size=n)
        resolution_time = start_day + days

        # Outcomes — ground truth Bernoulli(true_q)
        resolved_yes = self.rng.random(n) < true_q

        markets_meta: list[dict] = []
        decisions: list[DecisionPoint] = []

        for i in range(n):
            mid = f"syn_{i:05d}"
            markets_meta.append(
                {
                    "market_id": mid,
                    "true_q": float(true_q[i]),
                    "resolved_yes": bool(resolved_yes[i]),
                    "block_id": int(block_ids[i]),
                    "category": cat_of[i],
                    "days_to_resolution_full": float(days[i]),
                    "liquidity_usd": float(liquidity[i]),
                    "volume_24h": float(volume[i]),
                }
            )
            for frac in fracs:
                # Remaining life; market noise shrinks as we approach resolution
                remaining_frac = max(0.05, 1.0 - float(frac))
                days_left = float(days[i]) * remaining_frac
                # Model error → Brier roughly in 0.12–0.18 band when calibrated
                model_err = self.rng.normal(0.0, cfg.brier_noise_calibrated)
                q = float(np.clip(true_q[i] + model_err, 0.02, 0.98))
                # Crowd noise larger early, smaller late
                mkt_sigma = cfg.market_noise * (0.45 + 0.55 * remaining_frac)
                lag = self.rng.choice([-0.08, -0.04, 0.0, 0.04, 0.08])
                p = float(
                    np.clip(
                        true_q[i] + self.rng.normal(0.0, mkt_sigma) + lag,
                        0.02,
                        0.98,
                    )
                )
                decision_time = float(start_day[i] + days[i] * float(frac))
                did = f"{mid}_f{int(frac * 100):02d}"
                decisions.append(
                    DecisionPoint(
                        market_id=mid,
                        decision_id=did,
                        decision_time=decision_time,
                        lifetime_frac=float(frac),
                        category=cat_of[i],
                        block_id=int(block_ids[i]),
                        days_to_resolution=days_left,
                        p=p,
                        q=q,
                        liquidity_usd=float(liquidity[i]),
                        volume_24h=float(volume[i]),
                        true_q=float(true_q[i]),
                        resolved_yes=bool(resolved_yes[i]),
                        resolution_time=float(resolution_time[i]),
                        meta={"synthetic": True, "seed": self.seed},
                    )
                )

        logger.info(
            "SyntheticDataGenerator: n_markets=%d decisions=%d blocks=%d corr=%.2f seed=%d",
            n,
            len(decisions),
            n_blocks,
            corr,
            self.seed,
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
