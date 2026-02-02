# tests/test_cleaner.py
"""Tests for VTT cleaner module."""

import pytest
from pathlib import Path
import tempfile

from ytrag.cleaner import (
    parse_vtt_timestamp,
    clean_vtt_content,
    capitalize_sentences,
    process_vtt_file,
    process_vtt_directory,
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
        assert parse_vtt_timestamp(None) is None


class TestCleanVTTContent:
    """Tests for VTT content cleaning."""

    def test_removes_webvtt_header(self):
        """Should remove WEBVTT header."""
        content = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nhello"
        result = clean_vtt_content(content)
        assert "WEBVTT" not in result

    def test_removes_timestamps(self):
        """Should remove timestamp lines."""
        content = "00:00:00.000 --> 00:00:01.000\nhello world"
        result = clean_vtt_content(content)
        assert "-->" not in result
        assert "hello world" in result.lower()

    def test_removes_html_tags(self):
        """Should remove HTML tags."""
        content = "00:00:00.000 --> 00:00:01.000\n<c>hello</c> world"
        result = clean_vtt_content(content)
        assert "<c>" not in result
        assert "</c>" not in result

    def test_removes_music_markers(self):
        """Should remove [Music] markers."""
        content = "00:00:00.000 --> 00:00:01.000\n[Music]\n00:00:01.000 --> 00:00:02.000\nhello"
        result = clean_vtt_content(content)
        assert "[Music]" not in result
        assert "[music]" not in result.lower()

    def test_preserves_actual_content(self):
        """Should preserve actual spoken content."""
        content = "00:00:00.000 --> 00:00:01.000\nhello world this is a test"
        result = clean_vtt_content(content)
        assert "hello world this is a test" in result.lower()

    def test_handles_empty_input(self):
        """Should handle empty input."""
        assert clean_vtt_content("") == ""
        assert clean_vtt_content(None) == ""

    def test_creates_paragraphs_on_pause(self):
        """Should create new paragraph after significant pause."""
        content = """00:00:00.000 --> 00:00:01.000
first sentence
00:00:05.000 --> 00:00:06.000
second sentence after pause"""
        result = clean_vtt_content(content, pause_threshold=2.0)
        assert "\n\n" in result


class TestCapitalizeSentences:
    """Tests for sentence capitalization."""

    def test_capitalizes_first_letter(self):
        """Should capitalize first letter."""
        result = capitalize_sentences("hello world")
        assert result == "Hello world"

    def test_capitalizes_after_period(self):
        """Should capitalize after period."""
        result = capitalize_sentences("hello. world")
        assert result == "Hello. World"

    def test_handles_empty_string(self):
        """Should handle empty string."""
        assert capitalize_sentences("") == ""


class TestProcessVTTFile:
    """Tests for single file processing."""

    def test_processes_valid_vtt(self):
        """Should process valid VTT file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vtt_path = Path(tmpdir) / "20240101_Test Video.en.vtt"
            vtt_path.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nhello world")

            result = process_vtt_file(vtt_path, "Test Channel")

            assert result is not None
            assert result['base_name'] == "20240101_Test Video"
            assert result['language'] == "EN"
            assert "hello world" in result['content'].lower()
            assert result['channel'] == "Test Channel"

    def test_returns_none_for_empty_content(self):
        """Should return None for empty VTT."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vtt_path = Path(tmpdir) / "empty.en.vtt"
            vtt_path.write_text("WEBVTT\n\n")

            result = process_vtt_file(vtt_path, "Test Channel")
            assert result is None


class TestProcessVTTDirectory:
    """Tests for directory processing."""

    def test_processes_multiple_files(self):
        """Should process all VTT files in directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create test files
            (tmpdir / "20240101_Video1.en.vtt").write_text(
                "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nfirst video"
            )
            (tmpdir / "20240102_Video2.en.vtt").write_text(
                "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nsecond video"
            )

            results = process_vtt_directory(tmpdir, "Test Channel")

            assert len(results) == 2
            assert results[0]['base_name'] == "20240101_Video1"
            assert results[1]['base_name'] == "20240102_Video2"

    def test_deduplicates_regional_variants(self):
        """Should skip regional variant if non-regional exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create both regional and non-regional
            (tmpdir / "20240101_Video.en.vtt").write_text(
                "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nnon-regional"
            )
            (tmpdir / "20240101_Video.en-US.vtt").write_text(
                "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nregional"
            )

            results = process_vtt_directory(tmpdir, "Test Channel")

            assert len(results) == 1
            assert "non-regional" in results[0]['content'].lower()
