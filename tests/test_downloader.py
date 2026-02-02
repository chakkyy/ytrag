# tests/test_downloader.py
"""Tests for YouTube downloader module."""

import pytest
from ytrag.downloader import get_ydl_options


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
        """Should set default subtitle language to English."""
        opts = get_ydl_options("/tmp", "/tmp/archive.txt")
        assert 'en' in opts['subtitleslangs']

    def test_accepts_custom_languages(self):
        """Should accept custom subtitle languages."""
        opts = get_ydl_options("/tmp", "/tmp/archive.txt", subtitles_langs=['fr', 'de'])
        assert 'fr' in opts['subtitleslangs']
        assert 'de' in opts['subtitleslangs']

    def test_sets_archive_path(self):
        """Should set download archive path."""
        opts = get_ydl_options("/tmp", "/tmp/archive.txt")
        assert opts['download_archive'] == "/tmp/archive.txt"

    def test_sets_output_template(self):
        """Should set output template with date."""
        opts = get_ydl_options("/output", "/tmp/archive.txt")
        assert '%(upload_date)s' in opts['outtmpl']
        assert '%(title)s' in opts['outtmpl']
