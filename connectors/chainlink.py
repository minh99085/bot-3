"""Chainlink Data Streams + on-chain AggregatorV3 price feeds.

Primary path: Data Streams REST (`api.dataengine.chain.link`) with HMAC auth
when CHAINLINK_API_KEY + CHAINLINK_API_SECRET are set.

Fallback path: public RPC `eth_call` to AggregatorV3Interface (BTC/ETH USD)
so paper overnight runs still get decentralized oracle ground-truth without
Data Streams credentials.

Used by discovery (regime), signal gen, verifier (oracle alignment), and
paper executor (fill realism for 5m/15m markets).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

DATA_STREAMS_HOST = os.environ.get(
    "CHAINLINK_DATA_STREAMS_HOST", "https://api.dataengine.chain.link"
)
# Common Data Streams feed IDs (override via env for your subscription)
FEED_BTC_USD = os.environ.get(
    "CHAINLINK_FEED_BTC_USD",
    "0x00039d9e45394f473ab1f050a1b963e6b05351e52d71e507509ada0c95ed75b8",
)
FEED_ETH_USD = os.environ.get(
    "CHAINLINK_FEED_ETH_USD",
    "0x000362205e10b3a147d02792eccee483dca6c7b44ecce701ec99de3aa4a97872",
)

# Ethereum mainnet AggregatorV3 proxies (public, no API key)
AGG_BTC_USD = "0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c"
AGG_ETH_USD = "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419"
DEFAULT_RPC = os.environ.get(
    "ETH_RPC_URL", "https://ethereum.publicnode.com"
)

# latestRoundData() selector
_LATEST_ROUND_SELECTOR = "0xfeaf968c"


@dataclass
class OraclePrice:
    asset: str  # BTC | ETH
    price_usd: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    observed_at: Optional[datetime] = None
    source: str = "unknown"  # data_streams | aggregator_v3 | cache | synthetic
    feed_id: str = ""
    raw: Optional[dict[str, Any]] = None
    stale: bool = False

    @property
    def age_seconds(self) -> float:
        if not self.observed_at:
            return 9999.0
        return max(0.0, (datetime.now(timezone.utc) - self.observed_at).total_seconds())


class ChainlinkClient:
    """Hybrid Chainlink client: Data Streams preferred, AggregatorV3 fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        rpc_url: Optional[str] = None,
        timeout: float = 12.0,
    ):
        self.api_key = api_key or os.environ.get("CHAINLINK_API_KEY", "")
        self.api_secret = api_secret or os.environ.get("CHAINLINK_API_SECRET", "")
        self.rpc_url = rpc_url or DEFAULT_RPC
        self.timeout = timeout
        self._cache: dict[str, OraclePrice] = {}

    @property
    def streams_enabled(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def _hmac_headers(self, method: str, full_path: str, body: bytes = b"") -> dict[str, str]:
        ts = str(int(time.time() * 1000))
        body_hash = hashlib.sha256(body).hexdigest()
        string_to_sign = f"{method.upper()} {full_path} {body_hash} {self.api_key} {ts}"
        sig = hmac.new(
            self.api_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return {
            "Authorization": self.api_key,
            "X-Authorization-Timestamp": ts,
            "X-Authorization-Signature-SHA256": sig,
            "Content-Type": "application/json",
        }

    def get_latest_streams_report(self, feed_id: str) -> dict[str, Any]:
        path = f"/api/v1/reports/latest?feedID={feed_id}"
        url = f"{DATA_STREAMS_HOST}{path}"
        headers = self._hmac_headers("GET", path)
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()

    def _decode_streams_price(self, payload: dict[str, Any], asset: str, feed_id: str) -> OraclePrice:
        """Best-effort decode of Data Streams report JSON (schema varies by SDK version)."""
        report = payload.get("report") or payload.get("data") or payload
        # Common fields across clients
        price = None
        bid = ask = None
        ts = None
        for key in ("price", "benchmarkPrice", "midPrice", "mid"):
            if key in report and report[key] is not None:
                price = float(report[key])
                # Fixed-point 1e18
                if price > 1e10:
                    price = price / 1e18
                break
        if "bid" in report:
            bid = float(report["bid"])
            if bid > 1e10:
                bid /= 1e18
        if "ask" in report:
            ask = float(report["ask"])
            if ask > 1e10:
                ask /= 1e18
        for tkey in ("observationsTimestamp", "timestamp", "validFromTimestamp"):
            if tkey in report and report[tkey] is not None:
                raw_ts = int(report[tkey])
                if raw_ts > 1e12:
                    raw_ts //= 1000
                ts = datetime.fromtimestamp(raw_ts, tz=timezone.utc)
                break
        if price is None:
            raise ValueError(f"cannot decode streams price from keys={list(report)[:12]}")
        return OraclePrice(
            asset=asset,
            price_usd=price,
            bid=bid,
            ask=ask,
            observed_at=ts or datetime.now(timezone.utc),
            source="data_streams",
            feed_id=feed_id,
            raw=payload if isinstance(payload, dict) else {"report": report},
        )

    def _eth_call_latest_round(self, aggregator: str) -> tuple[float, datetime]:
        """Read AggregatorV3Interface.latestRoundData via JSON-RPC."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [{"to": aggregator, "data": _LATEST_ROUND_SELECTOR}, "latest"],
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(self.rpc_url, json=payload)
            resp.raise_for_status()
            result = resp.json().get("result")
        if not result or result == "0x":
            raise RuntimeError(f"empty eth_call for {aggregator}")
        data = result[2:] if result.startswith("0x") else result
        # roundId, answer, startedAt, updatedAt, answeredInRound — each 32 bytes
        if len(data) < 64 * 5:
            raise RuntimeError(f"unexpected latestRoundData length {len(data)}")
        answer = int(data[64:128], 16)
        # handle signed int256
        if answer >= 2**255:
            answer -= 2**256
        updated_at = int(data[64 * 3 : 64 * 4], 16)
        # BTC/ETH feeds use 8 decimals
        price = answer / 1e8
        ts = datetime.fromtimestamp(updated_at, tz=timezone.utc)
        return price, ts

    def get_price(self, asset: str, *, max_stale_sec: Optional[float] = None) -> OraclePrice:
        """Fetch BTC or ETH USD price. Streams → AggregatorV3 → cache."""
        asset = asset.upper()
        if asset not in ("BTC", "ETH"):
            raise ValueError(f"unsupported asset {asset}")

        cached = self._cache.get(asset)
        if cached and cached.age_seconds < 5.0:
            return cached

        if self.streams_enabled:
            feed = FEED_BTC_USD if asset == "BTC" else FEED_ETH_USD
            try:
                raw = self.get_latest_streams_report(feed)
                px = self._decode_streams_price(raw, asset, feed)
                limit = max_stale_sec if max_stale_sec is not None else 120.0
                px.stale = px.age_seconds > limit
                self._cache[asset] = px
                return px
            except Exception as exc:  # noqa: BLE001
                logger.warning("Chainlink Data Streams failed (%s); trying AggregatorV3", exc)

        agg = AGG_BTC_USD if asset == "BTC" else AGG_ETH_USD
        try:
            price, ts = self._eth_call_latest_round(agg)
            # AggregatorV3 heartbeats are slower than Data Streams — allow 2h
            limit = max_stale_sec if max_stale_sec is not None else 7200.0
            px = OraclePrice(
                asset=asset,
                price_usd=price,
                observed_at=ts,
                source="aggregator_v3",
                feed_id=agg,
                stale=(datetime.now(timezone.utc) - ts).total_seconds() > limit,
            )
            self._cache[asset] = px
            return px
        except Exception as exc:  # noqa: BLE001
            logger.warning("AggregatorV3 failed (%s)", exc)

        if cached:
            cached.stale = True
            return cached
        synth = {"BTC": 95_000.0, "ETH": 3_400.0}[asset]
        px = OraclePrice(
            asset=asset,
            price_usd=synth,
            observed_at=datetime.now(timezone.utc),
            source="synthetic",
            stale=True,
        )
        self._cache[asset] = px
        return px

    def get_btc_eth(self) -> dict[str, OraclePrice]:
        return {"BTC": self.get_price("BTC"), "ETH": self.get_price("ETH")}

    def returns_proxy(self, asset: str, lookback_sec: float = 300.0) -> float:
        """Crude short-horizon return proxy using cache vs fresh read.

        For 5m/15m markets; real deployments should retain a price ring buffer.
        """
        prev = self._cache.get(asset)
        now = self.get_price(asset)
        if prev is None or prev.price_usd <= 0:
            return 0.0
        if prev.observed_at and now.observed_at:
            dt = (now.observed_at - prev.observed_at).total_seconds()
            if dt < 1:
                return 0.0
        return (now.price_usd - prev.price_usd) / prev.price_usd
