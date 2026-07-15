"""Instance isolation + rotator selection."""

from __future__ import annotations

from models.market import MarketSnapshot, Side, TradeOpportunity
from strategy.enhanced_misprice import filter_markets_by_scope, rank_and_select


def test_filter_markets_by_scope(monkeypatch):
    monkeypatch.setenv("MARKET_FILTER", "eth5")
    monkeypatch.setenv("HERMES_SCOPE_BTC_UPDOWN_ONLY", "1")
    markets = [
        MarketSnapshot(market_id="1", slug="btc-updown-5m-1", p=0.4, q=0.9, timeframe="5m"),
        MarketSnapshot(market_id="2", slug="eth-updown-5m-1", p=0.4, q=0.9, timeframe="5m"),
        MarketSnapshot(market_id="3", slug="sol-updown-5m-1", p=0.4, q=0.9, timeframe="5m"),
    ]
    out = filter_markets_by_scope(markets)
    assert [m.slug for m in out] == ["eth-updown-5m-1"]


def test_rotator_max_one_trade(monkeypatch):
    monkeypatch.setenv("MARKET_FILTER", "rotator")
    monkeypatch.setenv("HERMES_SCOPE_BTC_UPDOWN_ONLY", "1")
    # Extreme-q + edge so hard filter can pass
    markets = [
        MarketSnapshot(
            market_id="a",
            slug="btc-updown-5m-10",
            p=0.70,
            q=0.92,
            timeframe="5m",
            liquidity_usd=20_000,
            volume_24h=50_000,
            seconds_to_resolution=200,
            category="crypto",
        ),
        MarketSnapshot(
            market_id="b",
            slug="eth-updown-5m-10",
            p=0.68,
            q=0.94,
            timeframe="5m",
            liquidity_usd=20_000,
            volume_24h=50_000,
            seconds_to_resolution=200,
            category="crypto",
        ),
    ]
    selected = rank_and_select(markets, market_filter="rotator", max_trades=1)
    assert len(selected) <= 1


def test_paper_dir_isolation(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_INSTANCE_ID", "eth5")
    monkeypatch.setenv("HERMES_PAPER_DIR", str(tmp_path / "paper_eth5"))
    from hermes.state_io import paper_dir, ledger_path, ensure_dirs

    ensure_dirs()
    assert paper_dir() == tmp_path / "paper_eth5"
    assert ledger_path().parent == tmp_path / "paper_eth5"
