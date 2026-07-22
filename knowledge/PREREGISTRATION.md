# PREREGISTRATION — 10-lane btc-updown-15m experiment

Registered: 2026-07-22 (commit history of this file is the audit trail).
**Any edit to this file after data collection begins starts a NEW experiment;
conclusions may not be drawn from data collected under a different version.**

## Primary hypothesis (exactly one)

> **H1**: The pure barrier lane (`lane01_baseline`, `HERMES_PURE_MODE=1` —
> barrier q, realized σ, fixed 2% sizing, no adaptive stack) achieves
> **positive paired-window PnL versus the random-null lane** (`lane09_random`)
> on Polymarket btc-updown-15m, settled on Polymarket's actual resolutions.

Everything else — favorite/longshot/late/garch/market-σ/depth lanes, and the
lane01-vs-lane02 autonomy A/B — is **secondary / exploratory** and is reported
with multiple-comparisons correction, never promoted to a headline claim.

## Fixed horizon (no peeking verdicts)

* **No verdict of any kind** (winner, loser, "edge exists", "edge is dead")
  before the primary lane has **≥ 1000 resolved trades** AND **≥ 300
  paired-with-null windows** (`backtest/prereg.py: VERDICT_MIN_TRADES /
  VERDICT_MIN_PAIRED` — code enforces the lock in every scoreboard).
* Interim scoreboards are **descriptive only** and print the lock banner.
* At ~$40 fixed tickets and current fill rates this is weeks of runtime.
  That is the honest cost of an answer at these effect sizes.

## Test statistic & correction

* Per lane: **two-sided exact sign test** on paired per-window PnL
  differences (lane − null), ties dropped. Nonparametric on purpose:
  longshot PnL is wildly non-normal.
* Family: **Holm–Bonferroni across all lane-vs-null comparisons** at family
  α = 0.05. A lane is only "significant" if it survives the correction.
* Controls: `lane08_legacy` (negative control) is expected to LOSE — if it
  beats null, the harness is broken and NO result may be trusted.

## Non-stationarity guard

Every board computes early-half vs late-half median |window move| (pooled,
realized close/open). If the ratio falls outside **[0.5×, 2.0×]** the board is
flagged NON-STATIONARY: the sample spans different vol regimes and aggregate
rankings conflate them — report per-regime, do not conclude.

## What would falsify H1

* Horizon reached and the sign test is not significant after Holm, or the
  paired PnL difference is ≤ 0 → **H1 rejected; the pure barrier lane has no
  demonstrated edge over random at this venue.** Write that conclusion down
  as prominently as a win would have been.
