"""C2 — conservative paper fills: depth cap, near-money penalty, report caveat."""

from __future__ import annotations

import pytest

from hermes.fill_model import (
    NEAR_MONEY_BAND,
    NEAR_MONEY_EXTRA_BPS,
    PAPER_CAVEAT,
    conservative_paper_fill,
    near_money_penalty_bps,
)


BOOK = [(0.24, 1000.0), (0.25, 2000.0), (0.30, 9999.0)]  # 3rd level outside 1¢


def test_near_money_penalty_shape():
    assert near_money_penalty_bps(0.5) == pytest.approx(NEAR_MONEY_EXTRA_BPS)
    half = near_money_penalty_bps(0.5 + NEAR_MONEY_BAND / 2)
    assert half == pytest.approx(NEAR_MONEY_EXTRA_BPS / 2)
    assert near_money_penalty_bps(0.5 + NEAR_MONEY_BAND) == 0.0
    assert near_money_penalty_bps(0.24) == 0.0
    assert near_money_penalty_bps(None) == 0.0


def test_depth_cap_limits_oversized_ticket():
    # near-touch notional = 0.24*1000 + 0.25*2000 = $740 → 25% = $185
    filled, px, _slip, note = conservative_paper_fill(
        BOOK, size_usd=1000.0, limit_price=0.24, mid=0.245
    )
    assert filled == pytest.approx(740.0 * 0.25)
    assert "depth_cap" in note
    assert px >= 0.24  # never better than limit


def test_small_ticket_fills_fully_at_vwap():
    filled, px, _slip, note = conservative_paper_fill(
        BOOK, size_usd=100.0, limit_price=0.24, mid=0.245
    )
    assert filled == pytest.approx(100.0)
    # $100 fits inside the $185 cap; walks level 1 then 2 → vwap ≥ best ask
    assert 0.24 <= px <= 0.25


def test_near_money_fill_is_priced_worse():
    at_money = [(0.50, 5000.0)]
    filled, px, slip, note = conservative_paper_fill(
        at_money, size_usd=40.0, limit_price=0.50, mid=0.50
    )
    assert filled == pytest.approx(40.0)
    assert px == pytest.approx(0.50 * (1 + NEAR_MONEY_EXTRA_BPS / 10_000))
    assert "near_money" in note and slip > 0


def test_far_from_money_no_penalty():
    far = [(0.20, 5000.0)]
    _f, px, _s, note = conservative_paper_fill(
        far, size_usd=40.0, limit_price=0.20, mid=0.20
    )
    assert px == pytest.approx(0.20)
    assert "near_money" not in note


def test_no_book_falls_back():
    filled, px, slip, note = conservative_paper_fill(
        [], size_usd=40.0, limit_price=0.3, mid=None
    )
    assert note == "no_book" and filled == 40.0


def test_broker_paper_fill_applies_model(monkeypatch):
    import connectors.broker as bk
    import connectors.polymarket as pm
    from hermes.models import Direction, EntryMode, OrderIntent

    class FakeBook:
        mid = 0.50
        asks = [type("L", (), {"price": 0.50, "size": 200.0})()]  # $100 notional
        bids = []

    monkeypatch.setattr(pm.PolymarketClient, "get_orderbook", lambda self, t: FakeBook())
    intent = OrderIntent(
        signal_id="s", market_id="m", direction=Direction.UP,
        size_usd=400.0, limit_price=0.50, entry_mode=EntryMode.MISPRICING,
        paper=True,
    )
    fill = bk.BrokerClient(paper=True).execute(intent, token_id="tok", asset="BTC")
    # $100 near-touch × 25% = $25 materialized in the FILL, not just a note
    assert fill.size_usd == pytest.approx(25.0)
    assert fill.fill_price > 0.50  # near-money penalty is in the price
    assert fill.paper is True


def test_paper_report_always_carries_caveat():
    from backtest.paper_ledger import build_real_report

    text = build_real_report([], bankroll=2000.0).text()
    assert PAPER_CAVEAT in text
