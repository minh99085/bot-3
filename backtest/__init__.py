"""backtest package — production suite for validating 80%+ WR."""

from backtest.engine import BacktestEngine, run_backtest
from backtest.synthetic_generator import SyntheticDataGenerator

__all__ = ["BacktestEngine", "SyntheticDataGenerator", "run_backtest"]
