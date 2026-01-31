# tests/test_downloader.py
"""Tests for YouTube downloader module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from ytrag.downloader import (
    get_ydl_options,
    select_best_subtitles,
    Downloader,
)


class TestGetYdlOptions:
    """Tests for yt-dlp options configuration."""

    def test_skip_download_is_true(self):
        """Should set skip_download to True."""
        opts = get_ydl_options("/tmp", "/tmp/archive.txt")
        assert opts['skip_download'] is True

    def test_writes_subtitles(self):
        """Should enable subtitle writing."""
        opts = get_ydl_options("/tmp", "/tmp/archive.txt")
        assert opts['writesubtitles'] is True
        assert opts['writeautomaticsub'] is True

    def test_sets_subtitle_languages(self):
        """Should set subtitle languages."""
        opts = get_ydl_options("/tmp", "/tmp/archive.txt")
        assert 'es' in opts['subtitleslangs']
        assert 'en' in opts['subtitleslangs']

    def test_sets_archive_path(self):
        """Should set download archive path."""
        opts = get_ydl_options("/tmp", "/tmp/archive.txt")
        assert opts['download_archive'] == "/tmp/archive.txt"

    def test_sets_output_template(self):
        """Should set output template with channel and date."""
        opts = get_ydl_options("/output", "/tmp/archive.txt")
        assert '%(channel)s' in opts['outtmpl']
        assert '%(upload_date)s' in opts['outtmpl']


class TestSelectBestSubtitles:
    """Tests for subtitle selection logic."""

    def test_prefers_manual_over_auto(self):
        """Should prefer manual subtitles over automatic."""
        subs = {
            'en': [{'ext': 'vtt', 'url': 'manual'}],
            'en-orig': [{'ext': 'vtt', 'url': 'auto'}],
        }
        auto_subs = {
            'en': [{'ext': 'vtt', 'url': 'auto-en'}],
        }

        result = select_best_subtitles(subs, auto_subs)
        assert result is not None
        assert result[0] == 'en'

    def test_uses_auto_if_no_manual(self):
        """Should use auto subtitles if no manual available."""
        subs = {}
        auto_subs = {
            'en': [{'ext': 'vtt', 'url': 'auto-en'}],
        }

        result = select_best_subtitles(subs, auto_subs)
        assert result is not None

    def test_returns_none_if_no_subs(self):
        """Should return None if no subtitles available."""
        result = select_best_subtitles({}, {})
        assert result is None

    def test_prefers_es_over_en(self):
        """Should prefer Spanish over English when both manual."""
        subs = {
            'es': [{'ext': 'vtt', 'url': 'es-url'}],
            'en': [{'ext': 'vtt', 'url': 'en-url'}],
        }

        result = select_best_subtitles(subs, {}, preferred_langs=['es', 'en'])
        assert result[0] == 'es'
