"""Persistence helpers — the agent forgets, the repo doesn't.

Reads/writes STATE.md, LESSONS.md, trade ledger JSONL, and parquet handoffs
between discovery → signal → verify → execute stages.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Type, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
DATA = ROOT / "data"


def _instance_id() -> str:
    """Per-container isolation key (btc5, btc15, eth5, sol5, rotator, …)."""
    import os

    env = os.environ.get("HERMES_INSTANCE_ID", "").strip().lower()
    if env:
        return env
    try:
        from hermes.market_scope import instance_id

        return instance_id()
    except Exception:  # noqa: BLE001
        return "default"


def paper_dir() -> Path:
    """Isolated paper ledger root: data/paper/<instance>/."""
    import os

    override = os.environ.get("HERMES_PAPER_DIR", "").strip()
    if override:
        return Path(override)
    return DATA / "paper" / _instance_id()


def handoff_dir() -> Path:
    import os

    override = os.environ.get("HERMES_HANDOFF_DIR", "").strip()
    if override:
        return Path(override)
    return DATA / "handoff" / _instance_id()


# Module-level aliases kept for older imports; resolve at call time via helpers.
HANDOFF = DATA / "handoff"
LEDGER = DATA / "paper" / "trade_ledger.jsonl"  # legacy path; prefer ledger_path()
INBOX = DATA / "paper" / "human_inbox.jsonl"

T = TypeVar("T", bound=BaseModel)


def ledger_path() -> Path:
    return paper_dir() / "trade_ledger.jsonl"


def inbox_path() -> Path:
    return paper_dir() / "human_inbox.jsonl"


def ensure_dirs() -> None:
    import os

    log_dir = Path(os.environ.get("HERMES_LOG_DIR", str(ROOT / "logs")))
    for p in (
        KNOWLEDGE,
        paper_dir(),
        DATA / "live",
        handoff_dir(),
        log_dir,
        ROOT / "artifacts" / _instance_id(),
    ):
        p.mkdir(parents=True, exist_ok=True)


def knowledge_path(name: str) -> Path:
    return KNOWLEDGE / name


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def append_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(content)
        if not content.endswith("\n"):
            f.write("\n")


def read_skill() -> str:
    return read_text(knowledge_path("SKILL.md"))


def read_alpha_skill() -> str:
    return read_text(knowledge_path("ALPHA_RESEARCH_SKILL.md"))


def read_state_md() -> str:
    return read_text(knowledge_path("STATE.md"))


def read_lessons_md() -> str:
    return read_text(knowledge_path("LESSONS.md"))


def parse_state_fields(md: Optional[str] = None) -> dict[str, Any]:
    """Best-effort parse of key: value lines from STATE.md front matter / table."""
    text = md if md is not None else read_state_md()
    fields: dict[str, Any] = {}
    for line in text.splitlines():
        m = re.match(r"^[-*]\s+\*\*(.+?)\*\*:\s*(.+)$", line)
        if m:
            key = m.group(1).strip().lower().replace(" ", "_")
            val = m.group(2).strip()
            fields[key] = _coerce(val)
            continue
        m = re.match(r"^([A-Za-z0-9_ /]+):\s*(.+)$", line)
        if m and not line.startswith("#"):
            key = m.group(1).strip().lower().replace(" ", "_").replace("/", "_")
            fields[key] = _coerce(m.group(2).strip())
    # Normalize circuit breaker aliases
    if "circuit_breaker" in fields:
        cb = fields["circuit_breaker"]
        if isinstance(cb, str) and cb.lower() in ("clear", "ok", "none", "off"):
            fields["circuit_breaker"] = False
            fields["circuit_breaker_tripped"] = False
        elif isinstance(cb, str) and cb.lower() in ("tripped", "halt", "active", "on"):
            fields["circuit_breaker"] = True
            fields["circuit_breaker_tripped"] = True
    return fields


def _coerce(val: str) -> Any:
    v = val.strip().strip("`")
    # Strip HTML comments appended by update_state_field
    if "<!--" in v:
        v = v.split("<!--", 1)[0].strip()
    if v.lower() in ("true", "yes"):
        return True
    if v.lower() in ("false", "no"):
        return False
    try:
        if "." in v:
            return float(v.replace("%", "").replace("$", "").replace(",", ""))
        return int(v.replace(",", ""))
    except ValueError:
        return v


def update_state_field(key: str, value: Any) -> None:
    """Replace a `**Key**: value` line in STATE.md, or append if missing.

    Never truncates the document. Strips prior HTML comment suffixes on replace.
    """
    path = knowledge_path("STATE.md")
    text = read_text(path)
    if not text.strip():
        # Recover from accidental wipe
        text = (
            "# STATE.md — Hermes Runtime Memory\n\n## Current Snapshot\n\n"
            "- **Mode**: paper\n"
            "- **Live Enabled**: false\n"
            "- **Paper Only Lock**: true\n"
            "- **Starting Bankroll USD**: 2000\n"
            "- **Capital USD**: 2000\n"
            "- **Pause Loop**: false\n"
            "- **Circuit Breaker**: clear\n"
        )
    pattern = rf"(^[-*]\s+\*\*{re.escape(key)}\*\*:\s*).+$"
    repl = rf"\g<1>{value}"
    new_text, n = re.subn(pattern, repl, text, flags=re.MULTILINE | re.IGNORECASE)
    if n == 0:
        new_text = text.rstrip() + f"\n- **{key}**: {value}\n"
    try:
        write_text(path, new_text)
    except OSError as exc:
        # Permission races on shared knowledge/ must not kill overnight loops
        logger.warning("STATE.md update failed for %s: %s", key, exc)


def append_jsonl(path: Path, obj: BaseModel | dict[str, Any]) -> None:
    ensure_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = obj.model_dump(mode="json") if isinstance(obj, BaseModel) else obj
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, default=str) + "\n")


def read_jsonl(path: Path, model: Optional[Type[T]] = None) -> list[Any]:
    if not path.exists():
        return []
    rows: list[Any] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            rows.append(model.model_validate(data) if model else data)
    return rows


def write_handoff(stage: str, items: Iterable[BaseModel], turn_id: str) -> Path:
    """Write stage output as JSON (and optionally parquet) for the next stage."""
    ensure_dirs()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = handoff_dir() / f"{stage}_{turn_id}_{stamp}.json"
    payload = [i.model_dump(mode="json") for i in items]
    out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    # Parquet twin when pandas/pyarrow available
    try:
        import pandas as pd

        if payload:
            pq = out.with_suffix(".parquet")
            pd.DataFrame(payload).to_parquet(pq, index=False)
    except Exception as exc:  # noqa: BLE001
        logger.debug("parquet handoff skipped: %s", exc)
    return out


def load_handoff(path: Path, model: Type[T]) -> list[T]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [model.model_validate(row) for row in data]


def push_inbox(item: dict[str, Any]) -> None:
    """Human-in-the-loop inbox for anything the loop cannot confidently handle."""
    item = {**item, "queued_at": datetime.now(timezone.utc).isoformat()}
    append_jsonl(inbox_path(), item)
    logger.warning("deferred to human inbox: %s", item.get("reason", item))


def ledger_path(paper: bool = True) -> Path:
    """Instance-isolated trade ledger (paper or live twin)."""
    if paper:
        p = paper_dir()
    else:
        p = DATA / "live" / _instance_id()
    p.mkdir(parents=True, exist_ok=True)
    return p / "trade_ledger.jsonl"
