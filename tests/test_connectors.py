"""Chainlink + Polymarket hybrid connector tests."""

from __future__ import annotations

from connectors.chainlink import ChainlinkClient, OraclePrice
from connectors.hybrid_data import oracle_alignment_score, regime_from_oracle
from connectors.polymarket import infer_timeframe
from hermes.models import Regime


def test_infer_timeframe():
    assert infer_timeframe("btc-updown-5m", "Bitcoin Up or Down") == "5m"
    assert infer_timeframe("eth-15m-updown", "") == "15m"
    assert infer_timeframe("will-btc-hit-100k", "Will BTC hit 100k?") == "1h"


def test_oracle_alignment_and_regime():
    score = oracle_alignment_score(yes_price=0.55, oracle_return=0.002, timeframe="5m")
    assert 0.0 <= score <= 1.0
    assert regime_from_oracle(0.002, 50, 0.5, "5m") == Regime.TRENDING_UP
    assert regime_from_oracle(-0.002, 50, 0.5, "5m") == Regime.TRENDING_DOWN


def test_chainlink_client_returns_price():
    cl = ChainlinkClient()
    px = cl.get_price("BTC")
    assert isinstance(px, OraclePrice)
    assert px.price_usd > 0
    assert px.source in ("data_streams", "aggregator_v3", "synthetic", "cache")
