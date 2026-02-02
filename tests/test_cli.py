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

    def test_status_command_exists(self):
        """Should have status command."""
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0
