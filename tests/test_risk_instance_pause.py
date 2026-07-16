"""Risk pause is per-instance — must not write Pause Loop into shared STATE.md."""

from __future__ import annotations

from hermes.models import RiskSnapshot
from hermes.risk_monitor import apply_risk_to_state, instance_paused, risk_state_path


def test_apply_risk_writes_instance_file(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_INSTANCE_ID", "btc5")
    monkeypatch.setenv("HERMES_PAPER_DIR", str(tmp_path / "btc5"))
    (tmp_path / "btc5").mkdir(parents=True)

    snap = RiskSnapshot(
        capital_usd=2000.0,
        open_exposure_usd=0.0,
        daily_pnl_usd=0.0,
        rolling_wr_20=0.0,
        rolling_pf_20=0.0,
        max_drawdown_pct=0.0,
        consecutive_losses=4,
        circuit_breaker_tripped=True,
        trip_reason="consecutive_losses=4",
        pause_loop=True,
    )
    apply_risk_to_state(snap)

    path = risk_state_path(paper=True)
    assert path.exists()
    assert path.parent.name == "btc5"
    paused, reason = instance_paused(paper=True)
    assert paused is True
    assert "consecutive_losses" in reason
