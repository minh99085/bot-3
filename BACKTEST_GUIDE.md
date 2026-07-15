# Backtest Guide — Prove the 80%+ Win Rate (Plain English)

This guide is for anyone who has never run a trading backtest before. You do **not** need a PhD. You need about 10 minutes and the command at the top of the README.

## What is a backtest?

A backtest asks: *If we had used today’s rules on thousands of fake-but-realistic markets, how often would we have been right?*

We generate markets where we secretly know the true probability (`true_q`), let a slightly noisy model produce `q`, let a noisy crowd produce market price `p`, then run the **exact same** Hermes filters used in paper trading. At the end we compare predictions to coin-flip outcomes drawn from `true_q`.

If the math is sound and the model is reasonably calibrated (Brier score &lt; 0.18), filtered trades should win **≥ 80%** of the time with drawdowns under **15%**.

---

## Quick commands

```bash
export PYTHONPATH=.
pip install -r requirements.txt

# 1) First thing to run — validate 80% WR
python -m backtest run --synthetic --n_markets 8000 --seed 42 --plots

# 2) Is it consistent across random universes?
python -m backtest monte-carlo --n_runs 100 --n_markets 4000 --plots

# 3) How much do Beta + Kelly help vs naive edge-only?
python -m backtest compare --n_markets 8000

# 4) Search for a robust config
python -m backtest tune --trials 30 --n_markets 5000
```

Reports land in `artifacts/backtest_runs/`.

---

## What each metric means

| Metric | Plain meaning | Why it matters for 80%+ |
|--------|---------------|-------------------------|
| **Win rate** | Fraction of taken trades that made money | Primary goal ≥ 80% |
| **Selectivity** | Trades taken ÷ decision points seen | Lower often means pickier → higher WR |
| **Profit factor** | Gross wins ÷ gross losses | &gt; 1 means positive expectancy |
| **Expectancy** | Average $ per trade | Must be &gt; 0 |
| **Max drawdown** | Worst peak-to-trough equity drop | Must stay ≤ 15% |
| **Brier score** | How wrong the model’s probabilities are | Need &lt; 0.18 for the WR target to be trustworthy |
| **WR by conviction / edge** | Win rate inside buckets | Shows *which* filters create the edge |

---

## How the math raises win rate

1. **Misprice** finds places where model `q` and market `p` disagree.
2. **Beta conviction** asks: given a Beta prior centered on `q` with strength `n_eff`, how confident are we that the true probability is on our side of `p`?
   - YES: `conviction = 1 − BetaCDF(p; α=q·n_eff, β=(1−q)·n_eff)`
3. **Hard filter** only allows trades when:
   - `|q − p| ≥ min_edge`
   - `conviction ≥ min_conviction`
   - `q` is extreme (`≥ extreme_q_high` or `≤ extreme_q_low`)
4. **Kelly** sizes the bet: YES `f* = (q−p)/(1−p)`, then `f = κ · min(f*, 1)`, capped at 10% of bankroll.
5. **Risk budget** refuses new bets when aggregate risk units would exceed the portfolio limit — important once correlated markets show up in the synthetic blocks.

Together: fewer, higher-conviction tickets → higher realized win rate.

---

## How to read the plots

- **Equity + underwater drawdown** — growing equity is good; deep red underwater patches mean painful streaks. Keep max DD &lt; 15%.
- **Calibration (reliability diagram)** — points near the diagonal mean `q` matches reality. If the curve bows away, fix the model before trusting WR.
- **Win rate vs min_conviction** — shows which threshold lands on 80%, 82%, 85%. Use this when tuning.
- **Monte Carlo histogram** — a tight bump above 80% with 5th percentile still ≥ 75% means the edge is *consistent*, not a lucky seed.

---

## If win rate is below 80%

1. Check **Brier**. If ≥ 0.18, improve the probability model first.
2. Raise `min_conviction` (e.g. 0.95 → 0.97) in `config/enhanced_misprice.yaml`.
3. Raise `min_edge` (e.g. 0.12 → 0.14).
4. Push extremes: `extreme_q_high: 0.88`, `extreme_q_low: 0.12`.
5. Increase `n_eff.crypto` (80 → 100) so Beta conviction is stricter.
6. Lower `kappa_base` (0.35 → 0.25) to cut size during learning.
7. Re-run: `python -m backtest run --synthetic --n_markets 8000 --seed 42 --plots`
8. Or let the tuner search: `python -m backtest tune --trials 40`

---

## No look-ahead bias

At each decision point the strategy only sees `p`, `q`, liquidity, and time-to-resolution. It never sees `true_q` or the eventual outcome until the resolution event. Correlated blocks stress-test the risk budget the same way clustered live markets would.

---

## Historical CSV mode

```bash
python -m backtest run --historical --csv data/backtest/example_historical.csv --plots
```

Required columns: `market_id, decision_time, p, q, resolution_outcome`  
Optional: `true_q, category, days_to_resolution, liquidity_usd, volume_24h`.

---

## Same code as paper trading

The backtester imports:

- `strategy.enhanced_misprice.evaluate_market`
- `risk.portfolio_risk.PortfolioRiskManager`
- `paper_trader.simulator.PaperSimulator`

No duplicated Kelly / Beta formulas. What you validate here is what the overnight Hermes loop uses.
