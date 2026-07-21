#!/usr/bin/env python3
"""Retire stale AVOID/SKIP lessons learned from corrupted-era data.

The lessons engine formed AVOID rules from settlements measured by the buggy
settlement path (entry-mid reference / live-mid exit / hash fills) and under
the 5m/15m series mislabel. Those rules now block honest trading. This marks
every active AVOID:/SKIP: runtime lesson as retired (doctrine sections
untouched), stamping the reason. Stdlib only; run on the VPS:

    python3 scripts/reset_stale_lessons.py --lessons knowledge/LESSONS.md
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path


def retire_stale(text: str, stamp: str) -> tuple[str, int]:
    """Mark active AVOID/SKIP lesson blocks retired; return (new_text, count)."""
    pattern = re.compile(
        r"(### \[.+?\].*?\n(?:- \*\*.*?\n)*?)(- \*\*Retired\*\*: false)",
        re.MULTILINE,
    )
    retired = 0

    def _fix(match: re.Match[str]) -> str:
        nonlocal retired
        head = match.group(1)
        if re.search(r"- \*\*Rule\*\*: (AVOID:|SKIP:)", head):
            retired += 1
            return head + (
                "- **Retired**: true\n"
                f"- **Retire evidence**: measured under corrupted settlement/"
                f"series-mislabel era; reset {stamp}"
            )
        return match.group(0)

    return pattern.sub(_fix, text), retired


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lessons", default="knowledge/LESSONS.md")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.lessons)
    if not path.is_file():
        print(f"not found: {path}")
        return 2
    text = path.read_text()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    new_text, n = retire_stale(text, stamp)
    print(f"retired {n} stale AVOID/SKIP lessons")
    if n and not args.dry_run:
        backup = path.with_suffix(".md.bak")
        backup.write_text(text)
        path.write_text(new_text)
        print(f"written; backup at {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
