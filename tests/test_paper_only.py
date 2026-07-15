"""Paper-only lock tests for Hermes Paper deployment."""

from __future__ import annotations

import os

from hermes.logging_config import enforce_paper_only, is_paper_only


def test_paper_only_default(monkeypatch):
    monkeypatch.delenv("HERMES_PAPER_ONLY", raising=False)
    monkeypatch.delenv("HERMES_LIVE", raising=False)
    enforce_paper_only()
    assert is_paper_only()
    assert os.environ.get("HERMES_LIVE") == "0"


def test_paper_only_blocks_live_env(monkeypatch):
    monkeypatch.setenv("HERMES_PAPER_ONLY", "1")
    monkeypatch.setenv("HERMES_LIVE", "1")
    enforce_paper_only()
    assert os.environ.get("HERMES_LIVE") == "0"


def test_broker_refuses_live_when_paper_only(monkeypatch):
    monkeypatch.setenv("HERMES_PAPER_ONLY", "1")
    from connectors.broker import BrokerClient

    b = BrokerClient(paper=False)
    assert b.paper is True
