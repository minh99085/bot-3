"""Market / opportunity / position pydantic models for enhanced misprice."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Side(str, Enum):
    YES = "YES"
    NO = "NO"
    UP = "UP"
    DOWN = "DOWN"


class MarketSnapshot(BaseModel):
    """Normalized live or synthetic market state."""

    market_id: str
    slug: str = ""
    question: str = ""
    category: str = "crypto"
    timeframe: str = "5m"
    p: float = Field(..., ge=0.0, le=1.0, description="Market implied P(YES/UP)")
    q: float = Field(..., ge=0.0, le=1.0, description="Model fair P(YES/UP)")
    liquidity_usd: float = 0.0
    volume_24h: float = 0.0
    seconds_to_resolution: float = 300.0
    true_q: Optional[float] = None  # backtest only
    resolved_yes: Optional[bool] = None  # backtest only
    # Optional advanced-ensemble diagnostics (populated when CEX history exists)
    multi_level_obi: Optional[float] = None
    ir: Optional[float] = None
    vamp: Optional[float] = None
    hurst: Optional[float] = None
    ou_theta: Optional[float] = None
    kalman_q: Optional[float] = None
    garch_vol: Optional[float] = None
    multi_tf_slopes: Optional[dict[str, float]] = None
    meta: dict[str, Any] = Field(default_factory=dict)
    as_of: datetime = Field(default_factory=utc_now)


class TradeOpportunity(BaseModel):
    """Ranked, filter-passing trade candidate with Kelly size."""

    market_id: str
    slug: str = ""
    side: Side
    p: float  # price paid for the chosen side
    q: float  # model prob for YES/UP
    edge: float
    conviction: float
    conviction_score: float
    kelly_f_star: float
    kelly_f: float
    kappa: float
    size_usd: float
    risk_unit: float
    liquidity_score: float
    time_decay_factor: float
    passes_hard_filter: bool
    reasons: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class OpenPosition(BaseModel):
    """Paper / backtest open position."""

    position_id: str
    market_id: str
    slug: str = ""
    side: Side
    entry_price: float
    size_usd: float
    shares: float = 0.0
    q_at_entry: float
    conviction_at_entry: float
    risk_unit: float
    opened_at: datetime = Field(default_factory=utc_now)
    meta: dict[str, Any] = Field(default_factory=dict)


class ClosedTrade(BaseModel):
    """Resolved or early-exited trade for reporting."""

    position_id: str
    market_id: str
    side: Side
    entry_price: float
    exit_price: float
    size_usd: float
    pnl_usd: float
    won: bool
    conviction_at_entry: float
    edge_at_entry: float
    early_exit: bool = False
    closed_at: datetime = Field(default_factory=utc_now)
    meta: dict[str, Any] = Field(default_factory=dict)


class DecisionPoint(BaseModel):
    """One no-lookahead observation of a synthetic/historical market.

    Strategy may only see ``p``, ``q``, liquidity, and time — never
    ``true_q`` or ``resolved_yes`` until resolution.
    """

    market_id: str
    decision_id: str
    decision_time: float  # chronological sort key (days from t0)
    lifetime_frac: float  # 0.3 / 0.6 / 0.85 etc.
    category: str = "crypto"
    block_id: int = 0  # correlation block
    days_to_resolution: float = 14.0
    p: float  # market price at decision (visible)
    q: float  # model probability at decision (visible)
    liquidity_usd: float = 0.0
    volume_24h: float = 0.0
    true_q: float  # hidden until analysis / resolution
    resolved_yes: bool  # hidden until resolution event
    resolution_time: float = 0.0
    meta: dict[str, Any] = Field(default_factory=dict)

    def as_snapshot(self) -> MarketSnapshot:
        """Public view for the strategy (true outcome stripped from inputs)."""
        return MarketSnapshot(
            market_id=self.market_id,
            slug=f"{self.category}-{self.market_id}",
            category=self.category,
            timeframe="synthetic",
            p=self.p,
            q=self.q,
            liquidity_usd=self.liquidity_usd,
            volume_24h=self.volume_24h,
            seconds_to_resolution=max(0.0, self.days_to_resolution) * 86400.0,
            # Engine may attach true_q/resolved for settlement only
            true_q=self.true_q,
            resolved_yes=self.resolved_yes,
            meta={
                "decision_id": self.decision_id,
                "lifetime_frac": self.lifetime_frac,
                "block_id": self.block_id,
                "days_to_resolution": self.days_to_resolution,
                **(self.meta or {}),
            },
        )


class DecisionRecord(BaseModel):
    """Every evaluated decision (taken or rejected) for selectivity analysis."""

    decision_id: str
    market_id: str
    taken: bool
    reject_reasons: list[str] = Field(default_factory=list)
    side: Optional[Side] = None
    p: float = 0.0
    q: float = 0.0
    edge: float = 0.0
    conviction: float = 0.0
    conviction_score: float = 0.0
    size_usd: float = 0.0
    kelly_f: float = 0.0
    category: str = ""
    days_to_resolution: float = 0.0
    lifetime_frac: float = 0.0
    true_q: float = 0.5
    resolved_yes: Optional[bool] = None
    won: Optional[bool] = None
    pnl_usd: Optional[float] = None
