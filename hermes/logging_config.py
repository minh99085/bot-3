"""Structured file logging + paper-mode lock for 24/7 VPS runs."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def enforce_paper_only() -> None:
    """Hard lock: Hermes Paper deployment never places live orders."""
    paper_only = os.environ.get("HERMES_PAPER_ONLY", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if paper_only:
        os.environ["HERMES_LIVE"] = "0"
        os.environ["HERMES_PAPER_ONLY"] = "1"


def is_paper_only() -> bool:
    return os.environ.get("HERMES_PAPER_ONLY", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def setup_logging(service: str = "bot") -> Path:
    """Configure console + rotating file logs under HERMES_LOG_DIR."""
    enforce_paper_only()
    log_dir = Path(os.environ.get("HERMES_LOG_DIR", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"hermes-{service}.log"

    root = logging.getLogger()
    if getattr(root, "_hermes_configured", False):
        return log_path

    level = getattr(logging, os.environ.get("HERMES_LOG_LEVEL", "INFO").upper(), logging.INFO)
    root.setLevel(level)
    fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Clear default handlers if re-init
    for h in list(root.handlers):
        root.removeHandler(h)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    try:
        fh = RotatingFileHandler(
            log_path,
            maxBytes=int(os.environ.get("HERMES_LOG_MAX_BYTES", 10_000_000)),
            backupCount=int(os.environ.get("HERMES_LOG_BACKUP_COUNT", 5)),
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except OSError as exc:
        logging.getLogger("hermes").warning("file logging disabled (%s): %s", log_path, exc)

    root._hermes_configured = True  # type: ignore[attr-defined]
    logging.getLogger("hermes").info(
        "logging ready service=%s file=%s paper_only=%s",
        service,
        log_path,
        is_paper_only(),
    )
    return log_path
