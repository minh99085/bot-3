"""Hermes v2 Streamlit dashboard — $2000 paper bankroll observability.

Run alongside the bot:
  streamlit run dashboard.py

Auto-refreshes every 8 seconds. Reads STATE.md, LESSONS.md, and paper ledgers.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from hermes.dashboard_data import (
    STARTING_BANKROLL,
    equity_curve,
    load_positions_open,
    load_pretrade,
    load_state,
    oracle_alignment_snapshot,
    portfolio_metrics,
    recent_lessons,
    recent_trade_table,
    substrategy_cards,
    total_pnl,
)

st.set_page_config(
    page_title="Hermes v2 — Paper Desk",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Auto-refresh every 8s (no extra dependency)
st.markdown(
    '<meta http-equiv="refresh" content="8">',
    unsafe_allow_html=True,
)

# ── Styles ──────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp {
  background: radial-gradient(1200px 600px at 10% -10%, #1a3a2f 0%, transparent 55%),
              radial-gradient(900px 500px at 100% 0%, #1e293b 0%, transparent 50%),
              #0b1220;
  color: #e8eef7;
}
h1, h2, h3 { letter-spacing: -0.02em; }
div[data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace; }
.block-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 1rem 1.1rem;
  margin-bottom: 0.75rem;
}
.tag {
  display: inline-block;
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  border-radius: 6px;
  background: rgba(56, 189, 248, 0.15);
  color: #7dd3fc;
  font-family: 'JetBrains Mono', monospace;
}
</style>
""",
    unsafe_allow_html=True,
)

state = load_state()
bankroll = float(state.get("starting_bankroll_usd") or STARTING_BANKROLL)
capital = float(state.get("capital_usd") or bankroll)
pnl = total_pnl(bankroll)
curve = equity_curve(bankroll)
equity_now = curve[-1]["equity"] if curve else bankroll
pm = portfolio_metrics()
oracle = oracle_alignment_snapshot()

st.title("Hermes v2 · Paper Trading Desk")
st.caption(
    f"Starting bankroll **${bankroll:,.0f}** USDC · Mode `{state.get('mode', 'paper')}` · "
    f"Auto-refresh 8s · Loop Engineering + Ruuj allocation + Chainlink ground-truth"
)

# ── Top metrics ─────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Equity", f"${equity_now:,.2f}", f"{pnl:+.2f} PnL")
c2.metric("Bankroll", f"${capital:,.2f}")
c3.metric("Div. Ratio", f"{pm['diversification_ratio']:.3f}")
c4.metric("Concentration HHI", f"{pm['concentration_hhi']:.3f}")
c5.metric(
    "Circuit",
    str(state.get("circuit_breaker", "clear")).upper(),
    str(state.get("pause_loop", False)),
)

left, right = st.columns([1.6, 1])

with left:
    st.subheader("Equity curve")
    if len(curve) > 1:
        df_eq = pd.DataFrame(curve)
        st.line_chart(df_eq.set_index(df_eq.index)["equity"], height=280)
    else:
        st.info("No settlements yet — equity sits at starting bankroll. Run `python -m hermes.hermes_loop demo`.")

    st.subheader("Recent trades")
    trades = recent_trade_table(40)
    if trades:
        st.dataframe(pd.DataFrame(trades), use_container_width=True, height=320)
    else:
        st.write("_No trades in ledger yet._")

with right:
    st.subheader("Chainlink ↔ Polymarket")
    st.markdown('<div class="block-card">', unsafe_allow_html=True)
    if oracle.get("btc"):
        st.markdown(
            f"**BTC** `${oracle['btc']:,.2f}` · **ETH** `${oracle.get('eth') or 0:,.2f}`  \n"
            f"<span class='tag'>{oracle.get('source')}</span>  "
            f"avg align `{oracle.get('avg_alignment', 0):.2f}`",
            unsafe_allow_html=True,
        )
    else:
        st.write("Oracle unavailable:", oracle.get("error", "—"))
    st.markdown("</div>", unsafe_allow_html=True)

    st.subheader("Portfolio")
    st.markdown(
        f"- Active sleeves: **{pm['substrategies_active']}**  \n"
        f"- CUT / REDUCE: **{pm['cut']}** / **{pm['reduce']}**  \n"
        f"- Method: `{pm['method']}`  \n"
        f"- Open positions: **{len(load_positions_open())}**"
    )
    if pm.get("top_weights"):
        st.bar_chart(pd.Series(pm["top_weights"], name="weight"))

    st.subheader("Latest lessons")
    for rule in recent_lessons(6):
        st.markdown(f"- {rule[:180]}")

st.subheader("Sub-strategy performance")
cards = substrategy_cards()
if cards:
    cols = st.columns(min(3, len(cards)))
    for i, card in enumerate(cards[:9]):
        with cols[i % len(cols)]:
            trend = "↑" if card["trend"] == "up" else "↓"
            st.markdown(
                f"""<div class="block-card">
                <div class="tag">{card['substrategy_id'][:48]}</div>
                <div style="margin-top:0.6rem;font-family:JetBrains Mono,monospace">
                WR <b>{card['wr']:.0%}</b> · EV <b>{card['ev']:+.3f}</b> · n={card['n']}<br/>
                weight <b>{card['weight']:.1%}</b> · recent {trend} {card['recent_wr']:.0%}<br/>
                PnL <b>${card['pnl']:+.2f}</b>
                </div></div>""",
                unsafe_allow_html=True,
            )
else:
    st.write("_No settled sub-strategy history yet._")

st.subheader("Pre-trade sizing decisions")
pt = load_pretrade()[-25:][::-1]
if pt:
    df = pd.DataFrame(
        [
            {
                "sleeve": p.get("substrategy_id"),
                "skip": p.get("skip"),
                "size_%": p.get("recommended_size_pct"),
                "size_$": p.get("recommended_size_usd"),
                "live_ev": p.get("live_ev"),
                "reasons": "; ".join((p.get("reasons") or [])[:2]),
            }
            for p in pt
        ]
    )
    st.dataframe(df, use_container_width=True, height=280)
else:
    st.write("_No pre-trade decisions logged yet._")

st.caption(
    f"Last turn: `{state.get('last_turn', 'none')}` · "
    f"{state.get('last_turn_summary', '')} · "
    f"Updated continuously from knowledge/ + data/paper/"
)
