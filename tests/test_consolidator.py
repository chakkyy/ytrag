# tests/test_consolidator.py
"""Tests for consolidator module."""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from ytrag.consolidator import (
    validate_markdown_file,
    extract_title,
    consolidate_channel,
    consolidate_all,
)


class TestValidateMarkdownFile:
    """Tests for markdown validation."""

    def test_valid_markdown(self):
        """Should return True for valid markdown."""
        content = "# Title\n**Idioma:** EN\n---\nContent"
        assert validate_markdown_file(content) is True

    def test_invalid_no_header(self):
        """Should return False for missing header."""
        content = "Just some text without header"
        assert validate_markdown_file(content) is False

    def test_empty_content(self):
        """Should return False for empty content."""
        assert validate_markdown_file("") is False


class TestExtractTitle:
    """Tests for title extraction."""

    def test_extracts_title(self):
        """Should extract title from markdown."""
        content = "# My Video Title\n**Idioma:** EN"
        assert extract_title(content) == "My Video Title"

    def test_handles_date_prefix(self):
        """Should include date in title."""
        content = "# 20230101_Video Title\n---"
        assert "20230101" in extract_title(content)


class TestConsolidateChannel:
    """Tests for channel consolidation."""

    @pytest.fixture
    def temp_biblioteca(self):
        """Create temp biblioteca with markdown files."""
        temp = tempfile.mkdtemp()

        biblioteca = Path(temp) / "_biblioteca" / "TestChannel"
        biblioteca.mkdir(parents=True)

        # Create 15 markdown files
        for i in range(15):
            content = f"""# 2023{i+1:02d}01_Video {i+1}
**Idioma:** EN
**Fuente:** video{i+1}.vtt
---

This is content for video {i+1}.
"""
            (biblioteca / f"2023{i+1:02d}01_Video {i+1} [EN].md").write_text(content)

        yield temp
        shutil.rmtree(temp)

    def test_creates_exports_folder(self, temp_biblioteca):
        """Should create _exports folder."""
        consolidate_all(temp_biblioteca)
        exports = Path(temp_biblioteca) / "_exports"
        assert exports.exists()

    def test_creates_volume_files(self, temp_biblioteca):
        """Should create volume txt files."""
        consolidate_all(temp_biblioteca)
        exports = Path(temp_biblioteca) / "_exports"
        txt_files = list(exports.glob("*.txt"))
        assert len(txt_files) >= 1

    def test_creates_manifest(self, temp_biblioteca):
        """Should create manifest.json."""
        consolidate_all(temp_biblioteca)
        manifest = Path(temp_biblioteca) / "_exports" / "manifest.json"
        assert manifest.exists()

        data = json.loads(manifest.read_text())
        assert "generated_at" in data
        assert "channels" in data

    def test_volume_has_index(self, temp_biblioteca):
        """Should include index at end of volume."""
        consolidate_all(temp_biblioteca)
        exports = Path(temp_biblioteca) / "_exports"
        txt_file = list(exports.glob("*.txt"))[0]
        content = txt_file.read_text()

        assert "ÍNDICE" in content
