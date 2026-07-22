"""C1 — capacity ceiling math on synthetic books (offline)."""

from __future__ import annotations

import pytest

from backtest.capacity import (
    MAX_IMPACT_CENTS,
    PARTICIPATION_MAX,
    WINDOWS_PER_WEEK_15M,
    estimate_capacity,
    estimate_signal_rate,
    fillable_usd,
)


def test_fillable_respects_impact_band_and_participation():
    book = [
        (0.24, 1000.0),   # best ask: $240 notional
        (0.25, 2000.0),   # +1¢: inside band → $500
        (0.26, 50000.0),  # +2¢: outside band → excluded
    ]
    got = fillable_usd(book, max_impact_cents=0.01, participation=1.0)
    assert got == pytest.approx(0.24 * 1000 + 0.25 * 2000)
    haircut = fillable_usd(book, max_impact_cents=0.01, participation=0.25)
    assert haircut == pytest.approx(got * 0.25)


def test_fillable_empty_and_garbage_levels():
    assert fillable_usd([]) == 0.0
    assert fillable_usd([(0.0, 100.0), (-1.0, 5.0)]) == 0.0


def test_signal_rate_from_ledger_windows():
    # 7 days of 15m windows, fleet fired on ~10% of them
    base = 1_784_000_000
    windows = [base + i * 900 for i in range(0, 672, 10)]  # every 10th window
    rate = estimate_signal_rate(windows)
    assert rate == pytest.approx(0.1, abs=0.02)
    assert estimate_signal_rate([]) == 0.0


def test_signal_rate_caps_at_one():
    base = 1_784_000_000
    windows = [base + i * 900 for i in range(96)]  # every window for a day
    assert estimate_signal_rate(windows) == pytest.approx(1.0, abs=0.05)


def test_weekly_ceiling_composition():
    yes = [(0.24, 1000.0)]
    no = [(0.76, 500.0)]
    est = estimate_capacity(yes, no, signal_rate=0.10, windows_per_week=672)
    fy = 0.24 * 1000 * PARTICIPATION_MAX
    fn = 0.76 * 500 * PARTICIPATION_MAX
    assert est.fillable_yes_usd == pytest.approx(fy)
    assert est.fillable_no_usd == pytest.approx(fn)
    per_window = (fy + fn) / 2
    assert est.weekly_ceiling_usd == pytest.approx(per_window * 672 * 0.10)
    # $60+$95 → /2 ≈ $77/window → thin-book note must fire
    assert any("THIN" in n for n in est.notes)
    assert any("adverse selection" in n for n in est.notes)


def test_report_text_carries_the_number():
    est = estimate_capacity([(0.5, 10_000.0)], [(0.5, 10_000.0)], signal_rate=0.2)
    text = est.text()
    assert "WEEKLY CEILING" in text
    assert f"{WINDOWS_PER_WEEK_15M}" in text
    assert f"{MAX_IMPACT_CENTS*100:.0f}" in text
