"""Backward-compatible re-exports — prefer synthetic_generator.SyntheticDataGenerator."""

from __future__ import annotations

from backtest.synthetic_generator import (
    SyntheticDataGenerator,
    estimate_brier,
    estimate_brier_from_decisions,
    generate_synthetic_markets,
)

__all__ = [
    "SyntheticDataGenerator",
    "generate_synthetic_markets",
    "estimate_brier",
    "estimate_brier_from_decisions",
]
