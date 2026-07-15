# LESSONS.md — Self-Improving Memory (Signals + Allocation)

> Every loss, rejection, **CUT/REDUCE**, or near-miss adds a dated rule.
> Drives both alpha filters and portfolio heuristics. Verifier + allocator read this.

## How to write a lesson

- **Imperative** (`AVOID:` / `EXPLOIT:` / `CUT:` / `REDUCE:` / `REQUIRE:`)
- **Evidence** (sleeve id, numbers)
- **Applies to** (include `allocation` when weight logic changes)
- **Promote to** ALPHA_RESEARCH_SKILL / SKILL
- Separate **currently_losing** from **model_broken**

## Seed Lessons (Hermes + Ruuj)

### [2026-07-15] `les_seed_osmani` — CRITICAL (rejection)

- **Rule**: AVOID:osmani_lane in all regimes until walk-forward WR > 65% and +EV. CUT when rolling EV collapsing — do not merely REDUCE if model broken.
- **Evidence**: Hermes v1 underperformance; toxic when degrading.
- **Applies to**: osmani_lane, high_vol, allocation, cut
- **Promote to**: ALPHA_RESEARCH_SKILL
- **Retired**: false

### [2026-07-15] `les_seed_exec_drag` — HIGH (near_miss)

- **Rule**: REQUIRE:entry_vwap_target inside spread and pre_entry_stability_ok=true before PASS.
- **Evidence**: Hermes v1 execution drag.
- **Applies to**: momentum, mean_reversion, liquidity_sweep
- **Promote to**: ALPHA_RESEARCH_SKILL
- **Retired**: false

### [2026-07-15] `les_seed_down_bias` — MEDIUM (rejection)

- **Rule**: REQUIRE:dynamic DOWN bias from STATE.md; do not hardcode static YES preference.
- **Evidence**: Hermes v1 implicit bias drift.
- **Applies to**: direction, regime
- **Promote to**: ALPHA_RESEARCH_SKILL
- **Retired**: false

### [2026-07-15] `les_seed_perf_gates` — HIGH (risk_halt)

- **Rule**: AVOID:trading when rolling WR(20) < 55% or PF(20) < 1.2 — pause the loop.
- **Evidence**: Missing daily/rolling gates.
- **Applies to**: risk_monitor, hermes_main
- **Promote to**: SKILL
- **Retired**: false

### [2026-07-15] `les_seed_hour_guards` — MEDIUM (rejection)

- **Rule**: REQUIRE:hourly_bucket + confidence_tier guards; reject unknown combos without bucket history.
- **Evidence**: Weak hour/regime guards.
- **Applies to**: discovery, verifier
- **Promote to**: ALPHA_RESEARCH_SKILL
- **Retired**: false

### [2026-07-15] `les_seed_lw_cov` — CRITICAL (allocation)

- **Rule**: REQUIRE:Ledoit-Wolf shrinkage on all covariance used for HRP/BL. Never raw sample covariance for sizing.
- **Evidence**: Ruuj robust portfolio construction — sample cov overfits sleeves.
- **Applies to**: allocation, portfolio, hrp
- **Promote to**: ALPHA_RESEARCH_SKILL
- **Retired**: false

### [2026-07-15] `les_seed_cut_vs_lose` — HIGH (allocation)

- **Rule**: REQUIRE:separate currently_losing from model_broken. currently_losing → REDUCE; model_broken → CUT even if recent PnL positive.
- **Evidence**: Ruuj Ch.5 — cutting too late on broken models destroys WR.
- **Applies to**: allocation, cut, reduce
- **Promote to**: ALPHA_RESEARCH_SKILL
- **Retired**: false

### [2026-07-15] `les_seed_verifier_alloc` — HIGH (allocation)

- **Rule**: REQUIRE:verifier approve both signal and proposed allocation size. Reject if HHI would exceed 0.45 or diversification collapses.
- **Evidence**: Signal-only verify → over-concentration fragility (~62% WR).
- **Applies to**: verifier, allocation
- **Promote to**: SKILL
- **Retired**: false

### [2026-07-15] `les_seed_chainlink_gt` — CRITICAL (data)

- **Rule**: REQUIRE:Chainlink oracle ground-truth for BTC/ETH signals. REJECT 5m/15m when oracle_stale or oracle_alignment < 0.45. Prefer Data Streams; AggregatorV3 is acceptable fallback.
- **Evidence**: CEX-only ticks are manipulable on short windows; Polymarket 5m/15m resolve via Chainlink + Automation.
- **Applies to**: oracle, btc_updown, eth_updown, verifier, allocation
- **Promote to**: ALPHA_RESEARCH_SKILL
- **Retired**: false

### [2026-07-15] `les_seed_clob_vwap` — HIGH (execution)

- **Rule**: REQUIRE:paper fills walk live CLOB orderbook (py-clob-client-v2) for VWAP/slippage; do not use flat synthetic slip when token_id is known.
- **Evidence**: Flat slip understates execution drag on thin 5m books.
- **Applies to**: executor, broker, polymarket
- **Promote to**: ALPHA_RESEARCH_SKILL
- **Retired**: false

### [2026-07-15] `les_seed_pretrade_pct` — HIGH (allocation)

- **Rule**: REQUIRE:pre-trade analysis before every order. Size as % of bankroll (max 3%) or skip at 0%. Verifier rejects if pretrade_skip or size unapproved. Log reasons for dashboard.
- **Evidence**: Fixed notional sizing ignored sleeve health and lessons → fragile WR.
- **Applies to**: pretrade, allocation, verifier, handoff
- **Promote to**: ALPHA_RESEARCH_SKILL
- **Retired**: false

## Active Lessons

<!-- lessons_engine appends new dated lessons below -->
