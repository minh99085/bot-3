"""Tests for strategy.signal_calibration self-improving hooks."""

from __future__ import annotations

from strategy.signal_calibration import (
    load_fusion_overrides,
    record_resolved_trade,
)


def test_record_and_recalibrate(tmp_path):
    path = tmp_path / "weights.json"
    for i in range(30):
        # Well-calibrated model around truth
        record_resolved_trade(
            p_up=0.8 if i % 2 == 0 else 0.2,
            resolved_yes=(i % 2 == 0),
            components={"momentum": 0.7 if i % 2 == 0 else 0.3, "obi": 0.6},
            path=path,
        )
    ov = load_fusion_overrides(path)
    assert "swarm_weight" in ov
    assert 0.55 <= ov["swarm_weight"] <= 0.80
    assert abs(ov["swarm_weight"] + ov["market_blend"] - 1.0) < 1e-6


def test_no_override_before_threshold(tmp_path):
    path = tmp_path / "w.json"
    record_resolved_trade(p_up=0.6, resolved_yes=True, path=path)
    assert load_fusion_overrides(path) == {}
