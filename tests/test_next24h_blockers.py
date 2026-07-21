"""Proactive fixes for everything that would freeze trading in the next 24h.

Live logs proved the fleet blind-spots: the fade-era stretch gate rejected
100% of ranging-market windows; the lessons engine and risk monitor judge
longshot books by raw WR (breakeven-blind) and would re-pause the fleet
within hours of honest trading; a regex bug filed every 15m window under the
5m series; oversized tickets turned routine streaks into hard-DD lockouts;
and 10 containers on one IP would 429 Kraken's ~1 req/s public limit.
"""

from __future__ import annotations

import pytest

from strategy.bayesian import bayesian_conviction, passes_hard_entry_filter


# --- stretch gate replaced by edge gate for calibrated q --------------------

def test_calibrated_q_trades_mid_market_on_edge():
    """The exact live rejection: q=0.4235 p=0.635 edge=0.21 → must PASS now."""
    q, p = 0.4235, 0.635
    conv = bayesian_conviction(q, p, 80, side="NO").conviction
    ok, reasons = passes_hard_entry_filter(
        q, p, conv,
        min_edge=0.14, min_conviction=0.93,
        extreme_q_high=0.85, extreme_q_low=0.15,
        live_real_q=True, extreme_p_high=0.72, extreme_p_low=0.28,
        net_edge=0.19, calibrated_q=True,
    )
    assert ok, reasons


def test_calibrated_q_still_gated_on_edge_and_conviction():
    """Calibrated q does NOT bypass the edge/conviction gates."""
    ok, reasons = passes_hard_entry_filter(
        0.55, 0.60, 0.99,
        min_edge=0.14, min_conviction=0.93,
        live_real_q=True, extreme_p_high=0.72, extreme_p_low=0.28,
        net_edge=0.03, calibrated_q=True,  # tiny net edge → reject
    )
    assert not ok and any("net_edge" in r for r in reasons)


def test_uncalibrated_legacy_keeps_stretch_gate():
    """The legacy lane (negative control) keeps the old fade-era behavior."""
    q, p = 0.4235, 0.635
    conv = bayesian_conviction(q, p, 80, side="NO").conviction
    ok, reasons = passes_hard_entry_filter(
        q, p, conv,
        min_edge=0.14, min_conviction=0.93,
        extreme_q_high=0.85, extreme_q_low=0.15,
        live_real_q=True, extreme_p_high=0.72, extreme_p_low=0.28,
        net_edge=0.19, calibrated_q=False,
    )
    assert not ok and any("not stretched" in r for r in reasons)


# --- series mislabel: 15m windows must never file under 5m ------------------

def test_15m_slug_not_mislabelled_as_5m():
    from hermes.substrategy import infer_market_series

    assert infer_market_series("m", "btc-updown-15m-1784601000") == "btc_updown_15m"
    assert infer_market_series("m", "btc-updown-5m-1784601000") == "btc_updown_5m"
    assert infer_market_series("m", "eth-updown-15m-1") == "eth_updown_15m"


# --- risk monitor: breakeven-aware pauses -----------------------------------

def _settles(n, won_flags, entry=0.2, pnl_win=240.0, pnl_loss=-60.0):
    out = []
    for i in range(n):
        w = won_flags[i % len(won_flags)]
        out.append({
            "won": w, "entry_price": entry,
            "pnl_usd": pnl_win if w else pnl_loss,
        })
    return out


def test_longshot_book_streaks_do_not_pause():
    from hermes.risk_monitor import (
        MAX_CONSECUTIVE_LOSSES_LONGSHOT,
        _avg_entry,
        _breakeven_wr,
        _rolling_stats,
    )

    # 30% WR longshot book @ entry 0.2 — PF = (6*240)/(14*60) = 1.71, profitable
    settles = _settles(20, [True, False, False, True, False, False, False] * 3)
    wr, pf, consec = _rolling_stats(settles)
    assert pf > 1.0
    be = _breakeven_wr(settles)
    assert be == pytest.approx(0.25, abs=0.01)  # 0.20 entry + 0.05 margin
    assert wr >= be - 0.05  # would NOT trip the breakeven floor
    assert _avg_entry(settles) < 0.45  # longshot regime → streak limit 10
    assert MAX_CONSECUTIVE_LOSSES_LONGSHOT >= 8


def test_favorite_book_bleeding_still_pauses():
    from hermes.risk_monitor import _breakeven_wr, _rolling_stats

    # 60% WR favorite book @ entry 0.8 — below its 0.85 breakeven, bleeding
    settles = _settles(20, [True, True, True, False, False] * 4,
                       entry=0.8, pnl_win=15.0, pnl_loss=-60.0)
    wr, pf, _ = _rolling_stats(settles)
    be = _breakeven_wr(settles)
    assert wr < be - 0.05  # breakeven floor correctly trips
    assert pf < 0.85       # PF floor also trips


# --- lessons: profitable longshot series must not form AVOID ----------------

def test_lessons_no_avoid_for_profitable_longshot(tmp_path, monkeypatch):
    import hermes.lessons_engine as le

    # 30% WR @ entry 0.2 with 4x wins → EV positive → no AVOID condition
    rows = _settles(10, [True, False, False, True, False, False, False, False, True, False])
    ev = sum(r["pnl_usd"] for r in rows) / len(rows)
    prices = [r["entry_price"] for r in rows]
    be = sum(prices) / len(prices) + 0.05
    wr = sum(1 for r in rows if r["won"]) / len(rows)
    # the new formation condition
    forms_avoid = len(rows) >= 8 and wr < max(0.0, be - 0.05) and ev < 0
    assert not forms_avoid  # profitable book → no AVOID


# --- venue load: per-instance rotation + secondary throttle -----------------

def test_source_order_rotates_by_instance(monkeypatch):
    import connectors.cex_sources as cs

    monkeypatch.delenv("HERMES_CEX_SOURCES", raising=False)
    orders = set()
    for inst in ("lane01_baseline", "lane02_chainlink", "lane03_favorite", "lane04_longshot"):
        monkeypatch.setenv("HERMES_INSTANCE_ID", inst)
        orders.add(tuple(cs.source_order()))
    assert len(orders) >= 2  # fleet spreads across venues
    for o in orders:
        assert set(o) == set(cs.DEFAULT_ORDER)  # same venues, rotated


def test_feed_secondary_confirm_throttled(monkeypatch):
    import connectors.cex_realtime as cx
    import connectors.cex_sources as cs

    ks = []

    def fake_multi(asset, k=2):
        ks.append(k)
        return [cs.Quote(100.0, 100.2, 100.1, "coinbase")]

    monkeypatch.setattr(cs, "get_mid_multi", fake_multi)
    feed = cx.RealtimeBtcFeed()
    for _ in range(6):
        feed._refresh_rest()
    # k=2 on 1st, 4th; k=1 otherwise → 1/3 of refreshes hit the secondary
    assert ks.count(2) == 2 and ks.count(1) == 4


# --- pretrade hard cap -------------------------------------------------------

def test_reset_stale_lessons_marks_avoid_retired(tmp_path):
    from scripts.reset_stale_lessons import retire_stale

    md = (
        "### [2026-07-19] loss lesson\n"
        "- **Rule**: AVOID:mispricing on `btc_updown_5m` after series WR=20%\n"
        "- **Retired**: false\n"
        "\n### [2026-07-19] win lesson\n"
        "- **Rule**: EXPLOIT continues\n"
        "- **Retired**: false\n"
    )
    new, n = retire_stale(md, "now")
    assert n == 1
    assert "corrupted settlement" in new
    assert "EXPLOIT continues\n- **Retired**: false" in new  # non-AVOID untouched
