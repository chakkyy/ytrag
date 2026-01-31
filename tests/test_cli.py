# tests/test_cli.py
"""Tests for CLI interface."""

import pytest
from typer.testing import CliRunner
from ytrag.main import app

runner = CliRunner()


class TestCLI:
    """Tests for CLI commands."""

    def test_version(self):
        """Should show version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.stdout

    def test_help(self):
        """Should show help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "ytrag" in result.stdout.lower()

    def test_clean_command_exists(self):
        """Should have clean command."""
        result = runner.invoke(app, ["clean", "--help"])
        assert result.exit_code == 0

    def test_consolidate_command_exists(self):
        """Should have consolidate command."""
        result = runner.invoke(app, ["consolidate", "--help"])
        assert result.exit_code == 0

    def test_download_command_exists(self):
        """Should have download command."""
        result = runner.invoke(app, ["download", "--help"])
        assert result.exit_code == 0

    def test_all_command_exists(self):
        """Should have all command."""
        result = runner.invoke(app, ["all", "--help"])
        assert result.exit_code == 0
