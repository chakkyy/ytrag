# tests/test_cli.py
"""Tests for CLI interface."""

import pytest
from typer.testing import CliRunner
from ytrag.main import app, extract_download_progress

runner = CliRunner()


class TestCLI:
    """Tests for CLI commands."""

    def test_version(self):
        """Should show version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "ytrag version" in result.stdout

    def test_help(self):
        """Should show help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "ytrag" in result.stdout.lower()

    def test_all_command_exists(self):
        """Should have all command."""
        result = runner.invoke(app, ["all", "--help"])
        assert result.exit_code == 0
        assert "YouTube URL" in result.stdout

    def test_all_command_exposes_rate_limit_options(self):
        """Should expose controls for large channel rate limiting."""
        result = runner.invoke(app, ["all", "--help"])
        assert result.exit_code == 0
        assert "--sleep-interval" in result.stdout
        assert "--stop-after-errors" in result.stdout
        assert "--rate-limit-retries" in result.stdout

    def test_status_command_exists(self):
        """Should have status command."""
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0


class TestDownloadProgress:
    """Tests for yt-dlp progress parsing."""

    def test_extracts_playlist_progress_from_info_dict(self):
        """Should return current index and total count from yt-dlp metadata."""
        progress = extract_download_progress(
            {'info_dict': {'playlist_index': 12, 'playlist_count': 50}},
            fallback_total=3,
        )
        assert progress == (12, 50)

    def test_uses_fallback_total_when_hook_has_no_total(self):
        """Should keep the preflight total when yt-dlp omits playlist_count."""
        progress = extract_download_progress(
            {'info_dict': {'playlist_index': 4}},
            fallback_total=20,
        )
        assert progress == (4, 20)

    def test_returns_none_for_missing_index(self):
        """Should ignore hook payloads that cannot identify the current item."""
        progress = extract_download_progress({'status': 'downloading'}, fallback_total=20)
        assert progress == (None, 20)
