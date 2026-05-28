"""Light sanity checks on the documentation tree (Phase 1, DOC1/DOC2/DOC3).

These tests are not a substitute for human review of docs; they only
catch the obvious "I forgot to add the file" / "I broke an internal
link" regression. Nothing here parses Markdown semantically.
"""

from __future__ import annotations

from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"


class TestCookbook:
    """The Phase 1 cookbook scaffolding exists and is indexed."""

    def test_cookbook_directory_exists(self):
        assert (DOCS / "cookbook").is_dir()

    def test_cookbook_has_index(self):
        assert (DOCS / "cookbook" / "README.md").is_file()

    def test_required_cookbook_recipes_exist(self):
        expected = {
            "download-wait.md",
            "oracle-forms.md",
            "captcha.md",
            "excel-input.md",
            "file-dialogs.md",
        }
        present = {p.name for p in (DOCS / "cookbook").glob("*.md")}
        missing = expected - present
        assert not missing, f"missing cookbook recipes: {sorted(missing)}"

    def test_cookbook_is_linked_from_docs_readme(self):
        content = (DOCS / "README.md").read_text(encoding="utf-8")
        assert "cookbook/README.md" in content


class TestMigrationGuide:
    """The Phase 1 migration guide exists and is indexed."""

    def test_migration_doc_exists(self):
        assert (DOCS / "migration.md").is_file()

    def test_migration_doc_covers_rename(self):
        content = (DOCS / "migration.md").read_text(encoding="utf-8")
        assert "BotVision" in content
        assert "VisusBot" in content
        assert "visus-desktop" in content
        # Should mention at least one of the new opt-ins
        assert "screenshot" in content.lower() or "doctor" in content.lower()

    def test_migration_is_linked_from_docs_readme(self):
        content = (DOCS / "README.md").read_text(encoding="utf-8")
        assert "migration.md" in content


class TestTroubleshooting:
    """The Phase 1 troubleshooting guide exists and is indexed."""

    def test_troubleshooting_doc_exists(self):
        assert (DOCS / "troubleshooting.md").is_file()

    def test_troubleshooting_covers_required_topics(self):
        """The required Phase 1 acceptance topics are present."""
        content = (DOCS / "troubleshooting.md").read_text(encoding="utf-8").lower()
        for required in ("ocr", "dpi", "pywinauto", "tcl"):
            assert required in content, f"missing topic: {required}"

    def test_troubleshooting_is_linked_from_docs_readme(self):
        content = (DOCS / "README.md").read_text(encoding="utf-8")
        assert "troubleshooting.md" in content
