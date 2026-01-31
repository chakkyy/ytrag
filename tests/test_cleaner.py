# tests/test_cleaner.py
"""Tests for VTT cleaner module."""

import tempfile
import shutil
from pathlib import Path

import pytest
from ytrag.cleaner import (
    parse_vtt_timestamp,
    clean_vtt_content,
    capitalize_sentences,
    select_best_subtitle_file,
    process_directory,
)


class TestParseVTTTimestamp:
    """Tests for VTT timestamp parsing."""

    def test_parses_standard_timestamp(self):
        """Should parse HH:MM:SS.mmm format."""
        result = parse_vtt_timestamp("00:01:30.500")
        assert result == 90.5

    def test_parses_zero_timestamp(self):
        """Should parse zero timestamp."""
        result = parse_vtt_timestamp("00:00:00.000")
        assert result == 0.0

    def test_returns_none_for_invalid(self):
        """Should return None for invalid input."""
        assert parse_vtt_timestamp("invalid") is None
        assert parse_vtt_timestamp("") is None


class TestCleanVTTContent:
    """Tests for VTT content cleaning."""

    def test_removes_webvtt_header(self):
        """Should remove WEBVTT header and metadata."""
        content = "WEBVTT\nKind: captions\nLanguage: en\n\nHello world"
        result = clean_vtt_content(content)
        assert "WEBVTT" not in result
        assert "Kind:" not in result

    def test_removes_timestamps(self):
        """Should remove timestamp lines."""
        content = "00:00:00.000 --> 00:00:02.000\nhello world"
        result = clean_vtt_content(content)
        assert "-->" not in result
        assert "00:00" not in result

    def test_removes_html_tags(self):
        """Should remove HTML/inline tags."""
        content = "00:00:00.000 --> 00:00:02.000\nhello<00:00:01.000><c> world</c>"
        result = clean_vtt_content(content)
        assert "<c>" not in result
        assert "</c>" not in result

    def test_removes_music_markers(self):
        """Should remove [Music] and similar markers."""
        content = "00:00:00.000 --> 00:00:02.000\n[Music]\n\n00:00:02.000 --> 00:00:04.000\nhello"
        result = clean_vtt_content(content)
        assert "[Music]" not in result

    def test_preserves_actual_content(self):
        """Should preserve spoken content."""
        content = """WEBVTT

00:00:00.000 --> 00:00:02.000
hello world

00:00:02.000 --> 00:00:04.000
this is a test
"""
        result = clean_vtt_content(content)
        assert "hello" in result.lower()
        assert "test" in result.lower()

    def test_handles_empty_input(self):
        """Should handle empty input."""
        assert clean_vtt_content("") == ""

    def test_creates_paragraphs_on_pause(self):
        """Should create paragraph breaks on pauses > threshold."""
        content = """WEBVTT

00:00:00.000 --> 00:00:02.000
first sentence

00:00:10.000 --> 00:00:12.000
second sentence after long pause
"""
        result = clean_vtt_content(content, pause_threshold=2.5)
        assert "\n\n" in result


class TestCapitalizeSentences:
    """Tests for sentence capitalization."""

    def test_capitalizes_first_letter(self):
        """Should capitalize first letter."""
        assert capitalize_sentences("hello")[0] == "H"

    def test_capitalizes_after_period(self):
        """Should capitalize after period."""
        result = capitalize_sentences("hello. world")
        assert "Hello" in result
        assert "World" in result

    def test_handles_empty_string(self):
        """Should handle empty string."""
        assert capitalize_sentences("") == ""


class TestSelectBestSubtitleFile:
    """Tests for subtitle file selection."""

    def test_prefers_non_regional(self):
        """Should prefer .en.vtt over .en-US.vtt."""
        files = ["video.en.vtt", "video.en-US.vtt"]
        result = select_best_subtitle_file(files, "video")
        assert result == "video.en.vtt"

    def test_returns_regional_if_only_option(self):
        """Should use regional if no alternative."""
        files = ["video.en-US.vtt"]
        result = select_best_subtitle_file(files, "video")
        assert result == "video.en-US.vtt"

    def test_returns_none_if_no_match(self):
        """Should return None if no matching files."""
        files = ["other.en.vtt"]
        result = select_best_subtitle_file(files, "video")
        assert result is None


class TestProcessDirectory:
    """Tests for directory processing."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temp directory with sample VTT files."""
        temp = tempfile.mkdtemp()

        # Create channel folder
        channel_dir = Path(temp) / "TestChannel"
        channel_dir.mkdir()

        # Create sample VTT
        vtt_content = """WEBVTT
Kind: captions
Language: en

00:00:00.000 --> 00:00:02.000
Hello world

00:00:02.000 --> 00:00:04.000
This is a test
"""
        vtt_file = channel_dir / "20230101_Test Video.en.vtt"
        vtt_file.write_text(vtt_content, encoding='utf-8')

        yield temp
        shutil.rmtree(temp)

    def test_creates_biblioteca_folder(self, temp_workspace):
        """Should create _biblioteca folder."""
        process_directory(temp_workspace)
        biblioteca = Path(temp_workspace) / "_biblioteca"
        assert biblioteca.exists()

    def test_creates_channel_subfolder(self, temp_workspace):
        """Should create channel subfolder in biblioteca."""
        process_directory(temp_workspace)
        channel_folder = Path(temp_workspace) / "_biblioteca" / "TestChannel"
        assert channel_folder.exists()

    def test_creates_markdown_files(self, temp_workspace):
        """Should create markdown output files."""
        process_directory(temp_workspace)
        biblioteca = Path(temp_workspace) / "_biblioteca" / "TestChannel"
        md_files = list(biblioteca.glob("*.md"))
        assert len(md_files) == 1

    def test_markdown_has_correct_structure(self, temp_workspace):
        """Should create markdown with proper structure."""
        process_directory(temp_workspace)
        biblioteca = Path(temp_workspace) / "_biblioteca" / "TestChannel"
        md_file = list(biblioteca.glob("*.md"))[0]
        content = md_file.read_text(encoding='utf-8')

        assert content.startswith('#')
        assert '**Idioma:**' in content
        assert '**Fuente:**' in content
        assert '---' in content

    def test_skips_duplicate_regional(self, temp_workspace):
        """Should skip regional variant if non-regional exists."""
        channel_dir = Path(temp_workspace) / "TestChannel"

        # Add regional variant
        vtt_content = "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nDuplicate"
        (channel_dir / "20230101_Test Video.en-US.vtt").write_text(vtt_content)

        process_directory(temp_workspace)

        biblioteca = Path(temp_workspace) / "_biblioteca" / "TestChannel"
        md_files = list(biblioteca.glob("*.md"))
        # Should only have one file, not two
        assert len(md_files) == 1
