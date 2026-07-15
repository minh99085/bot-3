"""Hard scope: only BTC 5m/15m Up/Down markets."""

from __future__ import annotations

from hermes.market_scope import (
    PREFERRED_SLUGS,
    all_discovery_slugs,
    is_allowed_slug,
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


def test_rejects_other_markets():
    assert not is_allowed_slug("will-bitcoin-hit-1m-before-gta-vi-872-424")
    assert not is_allowed_slug("eth-updown-5m-123")
    assert not is_allowed_slug("btc-updown-1h-123")


def test_discovery_slugs_include_preferred():
    slugs = all_discovery_slugs()
    assert any(s.startswith("btc-updown-5m-") for s in slugs)
    assert any(s.startswith("btc-updown-15m-") for s in slugs)
    assert all(is_allowed_slug(s) for s in slugs)


def test_scope_enabled_default(monkeypatch):
    monkeypatch.delenv("HERMES_SCOPE_BTC_UPDOWN_ONLY", raising=False)
    assert scope_enabled() is True


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
