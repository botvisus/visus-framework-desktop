#!/usr/bin/env python3
"""Sync the canonical docs into the package so the MCP server can ship them.

``docs/mcp.md`` and ``docs/cli.md`` are the source of truth (rendered on
GitHub, linked from the README). The MCP server exposes them as resources
(`visus://docs/mcp`, `visus://docs/cli`), reading from copies bundled inside
the package at ``src/visus/desktop/resources/``. This script copies the
canonical docs into that location so the two never drift.

Run manually with ``python scripts/sync_mcp_resources.py``; it also runs as a
pre-commit hook. Exit code 1 if it had to update a file (so pre-commit asks you
to stage the change), 0 if everything was already in sync.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESOURCES = ROOT / "src" / "visus" / "desktop" / "resources"
DOCS = ROOT / "docs"

# canonical doc -> bundled resource name
FILES = {"mcp.md": "mcp.md", "cli.md": "cli.md"}


def main() -> int:
    RESOURCES.mkdir(parents=True, exist_ok=True)
    changed = False
    for src_name, dst_name in FILES.items():
        src = DOCS / src_name
        dst = RESOURCES / dst_name
        if not src.exists():
            print(f"missing canonical doc: {src}", file=sys.stderr)
            return 2
        new = src.read_text(encoding="utf-8")
        old = dst.read_text(encoding="utf-8") if dst.exists() else None
        if new != old:
            dst.write_text(new, encoding="utf-8")
            print(f"synced {src_name} -> {dst.relative_to(ROOT)}")
            changed = True
    if changed:
        print("resources updated — stage the changes and commit again.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
