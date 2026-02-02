# tests/test_consolidator.py
"""Tests for consolidator module."""

import pytest
import json
from pathlib import Path
import tempfile

from ytrag.consolidator import (
    format_transcript,
    create_volumes,
    write_manifest,
)


def make_transcript(base_name: str, content: str = "Test content") -> dict:
    """Helper to create transcript dict."""
    return {
        'base_name': base_name,
        'language': 'EN',
        'content': content,
        'source_file': f"{base_name}.en.vtt",
        'channel': 'Test Channel',
    }


class TestFormatTranscript:
    """Tests for transcript formatting."""

    def test_formats_with_all_fields(self):
        """Should include all metadata fields."""
        transcript = make_transcript("20240101_Test Video")
        result = format_transcript(transcript)

        assert "# 20240101_Test Video" in result
        assert "**Idioma:** EN" in result
        assert "**Canal:** Test Channel" in result
        assert "**Fuente:** 20240101_Test Video.en.vtt" in result
        assert "Test content" in result


class TestCreateVolumes:
    """Tests for volume creation."""

    def test_creates_single_volume(self):
        """Should create single volume for small batch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            transcripts = [make_transcript(f"video{i}") for i in range(5)]

            stats = create_volumes(
                transcripts=transcripts,
                output_dir=output_dir,
                channel_name="TestChannel",
                transcripts_per_volume=100,
            )

            assert stats['total'] == 5
            assert len(stats['volumes']) == 1
            assert (output_dir / "TestChannel_Vol01.txt").exists()

    def test_creates_multiple_volumes(self):
        """Should split into multiple volumes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            transcripts = [make_transcript(f"video{i}") for i in range(25)]

            stats = create_volumes(
                transcripts=transcripts,
                output_dir=output_dir,
                channel_name="TestChannel",
                transcripts_per_volume=10,
            )

            assert stats['total'] == 25
            assert len(stats['volumes']) == 3
            assert (output_dir / "TestChannel_Vol01.txt").exists()
            assert (output_dir / "TestChannel_Vol02.txt").exists()
            assert (output_dir / "TestChannel_Vol03.txt").exists()

    def test_volume_has_header(self):
        """Should include volume header."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            transcripts = [make_transcript("video1")]

            create_volumes(
                transcripts=transcripts,
                output_dir=output_dir,
                channel_name="TestChannel",
            )

            content = (output_dir / "TestChannel_Vol01.txt").read_text()
            assert "=== COLECCIÓN: TestChannel ===" in content
            assert "=== VOLUMEN: 1 de 1 ===" in content

    def test_volume_has_index(self):
        """Should include index at end."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            transcripts = [
                make_transcript("20240101_First"),
                make_transcript("20240102_Second"),
            ]

            create_volumes(
                transcripts=transcripts,
                output_dir=output_dir,
                channel_name="TestChannel",
            )

            content = (output_dir / "TestChannel_Vol01.txt").read_text()
            assert "=== ÍNDICE DE ESTE VOLUMEN ===" in content
            assert "1. 20240101_First" in content
            assert "2. 20240102_Second" in content

    def test_handles_empty_transcripts(self):
        """Should handle empty transcript list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            stats = create_volumes(
                transcripts=[],
                output_dir=output_dir,
                channel_name="TestChannel",
            )

            assert stats['total'] == 0
            assert stats['volumes'] == []


class TestWriteManifest:
    """Tests for manifest writing."""

    def test_writes_manifest_json(self):
        """Should write valid JSON manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            stats = {'total': 10, 'volumes': ['Vol01.txt', 'Vol02.txt'], 'skipped': []}

            manifest_path = write_manifest(output_dir, "TestChannel", stats)

            assert manifest_path.exists()
            data = json.loads(manifest_path.read_text())
            assert data['channel'] == "TestChannel"
            assert data['total_transcripts'] == 10
            assert len(data['volumes']) == 2

    def test_manifest_has_timestamp(self):
        """Should include generation timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            stats = {'total': 5, 'volumes': ['Vol01.txt'], 'skipped': []}

            manifest_path = write_manifest(output_dir, "TestChannel", stats)

            data = json.loads(manifest_path.read_text())
            assert 'generated_at' in data
