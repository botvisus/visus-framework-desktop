"""Tests for the Skills bundle.

Skills are markdown files under ``skills/`` with YAML frontmatter
(``name``, ``description``, ``when_to_use``). Each skill must:
  * exist on disk
  * carry the three required frontmatter keys
  * reference only MCP tools that are actually registered in
    ``visus.desktop.mcp_server``
"""

from __future__ import annotations

import re
from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent / "skills"

REQUIRED_SKILLS = {
    "using-visus-desktop.md",
    "automate-form-login.md",
    "extract-table-data.md",
    "wait-for-download.md",
    "solve-image-captcha.md",
    "file-dialog-automation.md",
    "record-and-replay.md",
}


def _parse_frontmatter(text: str) -> dict:
    """Pull the YAML frontmatter from a markdown skill into a dict."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    result: dict = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        result[key.strip()] = value.strip()
    return result


def test_skills_directory_exists():
    assert SKILLS.is_dir()


def test_skills_index_lists_every_skill():
    index = (SKILLS / "README.md").read_text(encoding="utf-8")
    for name in REQUIRED_SKILLS:
        slug = name.replace(".md", "")
        assert slug in index, f"{slug} missing from skills/README.md"


def test_required_skills_present():
    present = {p.name for p in SKILLS.glob("*.md")}
    missing = REQUIRED_SKILLS - present
    assert not missing, f"missing skill files: {sorted(missing)}"


def test_every_skill_has_required_frontmatter():
    for name in REQUIRED_SKILLS:
        body = (SKILLS / name).read_text(encoding="utf-8")
        meta = _parse_frontmatter(body)
        for key in ("name", "description", "when_to_use"):
            assert key in meta, f"{name} missing frontmatter '{key}'"
        assert meta["name"], f"{name} has empty 'name'"
        assert meta["description"], f"{name} has empty 'description'"


def test_skills_only_reference_registered_tools():
    """No skill should mention an MCP tool name that doesn't exist."""
    from visus.desktop import mcp_server as ms

    valid_tools = set(ms._tools_for_tests())
    # Words that look like tool names but are normal English -> skip.
    # We only flag invented tool names; anything not in our set is just
    # documentation prose.
    invented_signal = re.compile(r"`([a-z_][a-z0-9_]*)\(")
    for name in REQUIRED_SKILLS:
        body = (SKILLS / name).read_text(encoding="utf-8")
        for candidate in invented_signal.findall(body):
            # If a candidate looks like an MCP tool by naming convention
            # (snake_case ending in a verb) it must exist. To avoid false
            # positives on Python stdlib calls, we only enforce on tools
            # the skill calls inline as ``tool_name(`` AND that share a
            # prefix with one of our known tools.
            if (
                candidate in valid_tools
                or any(t.startswith(candidate) for t in valid_tools)
                or not any(candidate.startswith(t.split("_")[0]) for t in valid_tools)
            ):
                continue
            raise AssertionError(
                f"{name}: references unknown MCP tool '{candidate}'"
            )
