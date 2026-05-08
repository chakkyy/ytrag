# tests/test_cli.py
"""Tests for CLI interface."""

import pytest
from typer.testing import CliRunner
from pathlib import Path

from ytrag.main import app, build_output_paths, extract_download_progress, should_prompt

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

    def test_all_command_exposes_notebooklm_export_options(self):
        """Should expose NotebookLM-oriented export options."""
        result = runner.invoke(app, ["all", "--help"])
        assert result.exit_code == 0
        assert "--target-volumes" in result.stdout
        assert "--per-volume" in result.stdout
        assert "--keep-raw" in result.stdout
        assert "--source-marker-freq" in result.stdout
        assert "--interactive" in result.stdout
        assert "--no-interactive" in result.stdout

    def test_status_command_exists(self):
        """Should have status command."""
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0

    def test_rebuild_command_exists(self):
        """Should expose a command for rebuilding volumes from local VTT files."""
        result = runner.invoke(app, ["rebuild", "--help"])
        assert result.exit_code == 0
        assert "VTT" in result.stdout

    def test_rebuild_command_exposes_export_options(self):
        """Should expose the same export controls for rebuild."""
        result = runner.invoke(app, ["rebuild", "--help"])
        assert result.exit_code == 0
        assert "--target-volumes" in result.stdout
        assert "--keep-raw" in result.stdout
        assert "--source-marker-freq" in result.stdout

    def test_status_detects_new_rag_volume_folder(self, tmp_path):
        """Should detect volumes in the new rag-volumes layout."""
        volumes_dir = tmp_path / "ytrag-TestChannel" / "rag-volumes"
        volumes_dir.mkdir(parents=True)
        (volumes_dir / "TestChannel_Vol01.txt").write_text("volume")

        result = runner.invoke(app, ["status", str(tmp_path)])

        assert result.exit_code == 0
        assert "ytrag-TestChannel" in result.stdout
        assert "Volumes: 1" in result.stdout

    def test_rebuild_uses_target_volumes_and_does_not_keep_raw_by_default(self, tmp_path):
        """Should calculate volume size from target volumes and omit raw output by default."""
        source = tmp_path / "source"
        source.mkdir()
        for index in range(10):
            (source / f"202401{index + 1:02d}_Video {index}.es.vtt").write_text(
                "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\ncontenido"
            )

        result = runner.invoke(
            app,
            [
                "rebuild",
                str(source),
                "Test Channel",
                "--output",
                str(tmp_path),
                "--target-volumes",
                "5",
                "--no-interactive",
            ],
        )

        project = tmp_path / "ytrag-Test Channel"
        volumes = list((project / "rag-volumes").glob("*_Vol*.txt"))
        assert result.exit_code == 0
        assert len(volumes) == 5
        assert not (project / "raw-subtitles").exists()

    def test_rebuild_per_volume_overrides_target_volumes_and_can_keep_raw(self, tmp_path):
        """Should let per-volume override target volume calculation and keep raw on request."""
        source = tmp_path / "source"
        source.mkdir()
        for index in range(10):
            (source / f"202401{index + 1:02d}_Video {index}.es.vtt").write_text(
                "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\ncontenido"
            )

        result = runner.invoke(
            app,
            [
                "rebuild",
                str(source),
                "Test Channel",
                "--output",
                str(tmp_path),
                "--target-volumes",
                "5",
                "--per-volume",
                "4",
                "--keep-raw",
                "--no-interactive",
            ],
        )

        project = tmp_path / "ytrag-Test Channel"
        volumes = list((project / "rag-volumes").glob("*_Vol*.txt"))
        raw_files = list((project / "raw-subtitles").glob("*.vtt"))
        assert result.exit_code == 0
        assert len(volumes) == 3
        assert len(raw_files) == 10


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


class TestOutputPaths:
    """Tests for output folder layout."""

    def test_builds_single_project_folder_with_named_subfolders(self, tmp_path):
        """Should keep raw, clean, and rag-ready outputs under one project folder."""
        paths = build_output_paths(tmp_path, "Rincón Apologético")

        assert paths['project'] == tmp_path / "ytrag-Rincón Apologético"
        assert paths['raw'] == paths['project'] / "raw-subtitles"
        assert paths['clean'] == paths['project'] / "clean-transcripts"
        assert paths['volumes'] == paths['project'] / "rag-volumes"
        assert paths['archive'] == paths['project'] / ".ytrag_archive"


class TestInteractiveMode:
    """Tests for interactive prompt selection."""

    def test_explicit_interactive_true_prompts(self):
        """Should prompt when explicitly requested."""
        assert should_prompt(True, is_tty=False) is True

    def test_explicit_interactive_false_never_prompts(self):
        """Should not prompt when disabled."""
        assert should_prompt(False, is_tty=True) is False

    def test_auto_prompts_only_in_tty(self):
        """Should prompt automatically only for real terminals."""
        assert should_prompt(None, is_tty=True) is True
        assert should_prompt(None, is_tty=False) is False
