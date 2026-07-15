"""Hermes v2 Streamlit dashboard — $2000 paper bankroll observability.

Run locally:
  streamlit run dashboard.py --server.baseUrlPath=dashboard

Production (Docker): nginx proxies http://<VPS_IP>/dashboard → this app.
Auto-refreshes every 5 minutes. Reads STATE.md, LESSONS.md, and paper ledgers.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from hermes.logging_config import setup_logging

    setup_logging("dashboard")
except Exception:
    pass

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
    recent_lessons_scoped,
    recent_trade_table,
    scoped_market_cards,
    total_pnl,
)

st.set_page_config(
    page_title="Hermes v2 — Paper Desk",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Auto-refresh every 5 minutes (no extra dependency)
st.markdown(
    '<meta http-equiv="refresh" content="300">',
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

st.title("Hermes v2 · BTC Up/Down Paper Desk")
st.caption(
    f"Starting bankroll **${bankroll:,.0f}** USDC · **ONLY** BTC 5m + 15m Up/Down · "
    f"Mode `{state.get('mode', 'paper')}` · Auto-refresh 5 min · Chainlink + CLOB"
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

st.subheader("Scoped markets — BTC Up/Down only")
scoped = scoped_market_cards()
sc1, sc2 = st.columns(2)
for i, card in enumerate(scoped):
    col = sc1 if i == 0 else sc2
    with col:
        wr = f"{card['wr']:.0%}" if card["wr"] is not None else "—"
        size = card.get("current_size_usd")
        size_s = f"${size:.2f}" if size is not None else "—"
        skip = card.get("last_skip")
        st.markdown(
            f"""<div class="block-card">
            <div class="tag">{card['label']}</div>
            <div style="margin-top:0.4rem;font-size:0.8rem;opacity:0.75">{card.get('preferred_slug') or card['series']}</div>
            <div style="margin-top:0.6rem;font-family:JetBrains Mono,monospace">
            WR <b>{wr}</b> · trades <b>{card['n']}</b> · PnL <b>${card['pnl']:+.2f}</b><br/>
            last size <b>{size_s}</b>
            {" · <span style='color:#fbbf24'>SKIP</span>" if skip else " · sized"}
            · EV {card.get('last_live_ev') if card.get('last_live_ev') is not None else '—'}
            </div>
            <div style="margin-top:0.5rem;font-size:0.8rem;opacity:0.8">
            {'; '.join((card.get('last_reasons') or [])[:2]) or 'awaiting first pretrade'}
            </div>
            </div>""",
            unsafe_allow_html=True,
        )

left, right = st.columns([1.6, 1])

with left:
    st.subheader("Equity curve")
    if len(curve) > 1:
        df_eq = pd.DataFrame(curve)
        st.line_chart(df_eq.set_index(df_eq.index)["equity"], height=280)
    else:
        st.info("No settlements yet — equity at $2000. Bot scans BTC 5m/15m only.")

    st.subheader("Recent trades (scoped)")
    trades = recent_trade_table(40)
    if trades:
        st.dataframe(pd.DataFrame(trades), use_container_width=True, height=320)
    else:
        st.write("_No paper fills yet — verifier/sizing may be skipping._")

with right:
    st.subheader("Chainlink BTC")
    st.markdown('<div class="block-card">', unsafe_allow_html=True)
    if oracle.get("btc"):
        st.markdown(
            f"**BTC** `${oracle['btc']:,.2f}`  \n"
            f"<span class='tag'>{oracle.get('source')}</span>  "
            f"avg align `{oracle.get('avg_alignment', 0):.2f}`",
            unsafe_allow_html=True,
        )
    else:
        st.write("Oracle unavailable:", oracle.get("error", "—"))
    st.markdown("</div>", unsafe_allow_html=True)

    st.subheader("Open / portfolio")
    st.markdown(
        f"- Open positions: **{len(load_positions_open())}**  \n"
        f"- CUT / REDUCE: **{pm['cut']}** / **{pm['reduce']}**  \n"
        f"- Method: `{pm['method']}`"
    )

    st.subheader("Latest lessons (BTC fast markets)")
    lessons = recent_lessons_scoped(8) or recent_lessons(6)
    for rule in lessons:
        st.markdown(f"- {rule[:200]}")

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
    f"Scope: btc-updown-5m-* + btc-updown-15m-* only · "
    f"Last turn: `{state.get('last_turn', 'none')}` · "
    f"{state.get('last_turn_summary', '')}"
)
