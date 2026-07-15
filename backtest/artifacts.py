"""Persist backtest runs under artifacts/backtest_runs/YYYYMMDD_HHMMSS/."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

ARTIFACT_ROOT = Path("artifacts/backtest_runs")
BEST_PARAMS_PATH = Path("config/best_params.json")


def new_run_dir(tag: str = "") -> Path:
    """Timestamped folder: artifacts/backtest_runs/YYYYMMDD_HHMMSS[/tag]."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = ARTIFACT_ROOT / ts
    if tag:
        path = path  # keep flat timestamp; tag goes in report metadata
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: Any) -> Path:
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path


def write_text(path: Path, text: str) -> Path:
    path.write_text(text)
    return path


def write_yaml(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(yaml.safe_dump(payload, sort_keys=False, default_flow_style=False))
    return path


def save_best_params(params: dict[str, Any], *, metrics: Optional[dict] = None) -> Path:
    """Persist tuned params for paper trader / future runs."""
    BEST_PARAMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "params": params,
        "metrics": metrics or {},
    }
    write_json(BEST_PARAMS_PATH, payload)
    # Also mirror into a yaml snippet the user can paste
    write_yaml(Path("config/best_params.yaml"), params)
    logger.info("Best params saved → %s", BEST_PARAMS_PATH)
    return BEST_PARAMS_PATH


def apply_best_params_to_config(
    config_path: Path | str = "config/enhanced_misprice.yaml",
    params: Optional[dict[str, Any]] = None,
) -> Path:
    """Merge best params into the active YAML config (in-place)."""
    path = Path(config_path)
    raw: dict[str, Any] = {}
    if path.is_file():
        raw = yaml.safe_load(path.read_text()) or {}
    params = params or {}
    mapping = {
        "min_edge": "min_edge",
        "min_conviction": "min_conviction",
        "kappa_base": "kappa_base",
        "risk_budget": "risk_budget",
        "extreme_q_high": "extreme_q_high",
        "extreme_q_low": "extreme_q_low",
    }
    for src, dst in mapping.items():
        if src in params:
            raw[dst] = params[src]
    if "n_eff_crypto" in params:
        n_eff = raw.get("n_eff") or {}
        if not isinstance(n_eff, dict):
            n_eff = {}
        n_eff["crypto"] = params["n_eff_crypto"]
        raw["n_eff"] = n_eff
    write_yaml(path, raw)
    logger.info("Updated active config %s with best params", path)
    return path


def save_run_bundle(
    *,
    tag: str = "run",
    metrics: dict[str, Any],
    summary_text: str,
    command: str = "",
    parameters: Optional[dict[str, Any]] = None,
    extra: Optional[dict[str, Any]] = None,
    plot_paths: Optional[list[Path]] = None,
    verdict: str = "",
) -> Path:
    """Write report.json, report.txt, parameters_used.yaml, plots index."""
    run_dir = new_run_dir(tag)
    report_body = summary_text
    if command:
        report_body = (
            f"Reproduce with:\n  {command}\n\n"
            f"{'=' * 60}\n\n"
            f"{verdict}\n\n"
            f"{summary_text}"
        )
    elif verdict:
        report_body = f"{verdict}\n\n{summary_text}"

    write_json(
        run_dir / "report.json",
        {
            "tag": tag,
            "command": command,
            "verdict": verdict,
            "metrics": metrics,
            "extra": extra or {},
        },
    )
    # Keep metrics.json alias for older tools
    write_json(run_dir / "metrics.json", metrics)
    write_text(run_dir / "report.txt", report_body)
    write_yaml(run_dir / "parameters_used.yaml", parameters or {})
    if extra:
        write_json(run_dir / "extra.json", extra)
    if plot_paths:
        write_json(
            run_dir / "plots_index.json",
            [str(p) for p in plot_paths if p is not None],
        )
    logger.info("Artifacts written to %s", run_dir)
    return run_dir
