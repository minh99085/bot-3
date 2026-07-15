"""Persist backtest runs under artifacts/backtest_runs/."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

ARTIFACT_ROOT = Path("artifacts/backtest_runs")


def new_run_dir(tag: str = "run") -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = ARTIFACT_ROOT / f"{tag}_{ts}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: Any) -> Path:
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path


def write_text(path: Path, text: str) -> Path:
    path.write_text(text)
    return path


def save_run_bundle(
    *,
    tag: str,
    metrics: dict[str, Any],
    summary_text: str,
    extra: Optional[dict[str, Any]] = None,
    plot_paths: Optional[list[Path]] = None,
) -> Path:
    run_dir = new_run_dir(tag)
    write_json(run_dir / "metrics.json", metrics)
    write_text(run_dir / "report.txt", summary_text)
    if extra:
        write_json(run_dir / "extra.json", extra)
    # Plot paths are already saved beside us; record index
    if plot_paths:
        write_json(
            run_dir / "plots_index.json",
            [str(p) for p in plot_paths if p is not None],
        )
    logger.info("Artifacts written to %s", run_dir)
    return run_dir
