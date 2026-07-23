"""Market scope + MARKET_FILTER for multi-instance Hermes."""

from __future__ import annotations

from hermes.market_scope import (
    PREFERRED_SLUGS,
    active_filter_keys,
    all_discovery_slugs,
    is_allowed_slug,
    load_market_filters_config,
    market_filter,
    parse_slug,
    scope_enabled,
)


def test_preferred_slugs_parse():
    assert "btc-updown-15m-1784113200" in PREFERRED_SLUGS
    assert "btc-updown-5m-1784113500" in PREFERRED_SLUGS
    s15 = parse_slug("btc-updown-15m-1784113200")
    s5 = parse_slug("btc-updown-5m-1784113500")
    assert s15 and s15.series == "btc_updown_15m" and s15.timeframe == "15m"
    assert s5 and s5.series == "btc_updown_5m" and s5.timeframe == "5m"
    assert s5.filter_key == "btc5"
    eth = parse_slug("eth-updown-5m-1784113500")
    sol = parse_slug("sol-updown-5m-1784113500")
    assert eth and eth.filter_key == "eth5" and eth.asset == "eth"
    assert sol and sol.filter_key == "sol5" and sol.asset == "sol"


def test_rejects_other_markets():
    assert not is_allowed_slug("will-bitcoin-hit-1m-before-gta-vi-872-424")
    assert not is_allowed_slug("btc-updown-1h-123")
    assert not is_allowed_slug("xrp-updown-5m-123")


def test_market_filter_btc5_only(monkeypatch):
    monkeypatch.setenv("MARKET_FILTER", "btc5")
    assert is_allowed_slug("btc-updown-5m-1784113500")
    assert not is_allowed_slug("btc-updown-15m-1784113200")
    assert not is_allowed_slug("eth-updown-5m-1784113500")
    assert active_filter_keys() == ["btc5"]


def test_market_filter_eth5(monkeypatch):
    monkeypatch.setenv("MARKET_FILTER", "eth5")
    assert is_allowed_slug("eth-updown-5m-1")
    assert not is_allowed_slug("btc-updown-5m-1")


def test_rotator_allows_all_four(monkeypatch):
    monkeypatch.setenv("MARKET_FILTER", "rotator")
    assert is_allowed_slug("btc-updown-5m-1")
    assert is_allowed_slug("btc-updown-15m-1")
    assert is_allowed_slug("eth-updown-5m-1")
    assert is_allowed_slug("sol-updown-5m-1")
    assert set(active_filter_keys()) == {"btc5", "btc15", "eth5", "eth15", "sol5"}


def test_discovery_slugs_respect_filter(monkeypatch):
    monkeypatch.setenv("MARKET_FILTER", "sol5")
    slugs = all_discovery_slugs()
    assert slugs
    assert all(s.startswith("sol-updown-5m-") for s in slugs)
    assert all(is_allowed_slug(s) for s in slugs)


def test_market_filters_yaml_loaded():
    cfg = load_market_filters_config()
    assert "filters" in cfg
    assert set(cfg["filters"]) >= {"btc5", "btc15", "eth5", "sol5"}


def test_scope_enabled_default(monkeypatch):
    monkeypatch.delenv("HERMES_SCOPE_BTC_UPDOWN_ONLY", raising=False)
    monkeypatch.delenv("MARKET_FILTER", raising=False)
    assert scope_enabled() is True
    assert market_filter() == "legacy_btc"


def test_series_from_record_no_substring_collision():
    from hermes.market_scope import (
        SERIES_5M,
        SERIES_15M,
        record_belongs_to_series,
        series_from_record,
    )

    rec_15m = {"substrategy_id": "btc_updown_15m|mispricing|low_vol|h14|15m"}
    rec_5m = {"substrategy_id": "btc_updown_5m|mispricing|low_vol|h14|5m"}
    assert series_from_record(rec_15m) == SERIES_15M
    assert series_from_record(rec_5m) == SERIES_5M
    assert record_belongs_to_series(rec_15m, SERIES_15M)
    assert not record_belongs_to_series(rec_15m, SERIES_5M)
