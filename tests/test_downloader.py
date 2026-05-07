# tests/test_downloader.py
"""Tests for YouTube downloader module."""

import pytest
from ytrag.downloader import Downloader, get_ydl_options, normalize_youtube_collection_url


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

    def test_accepts_progress_hooks(self):
        """Should pass progress hooks through to yt-dlp."""
        hook = lambda data: None
        opts = get_ydl_options("/tmp", "/tmp/archive.txt", progress_hooks=[hook])
        assert opts['progress_hooks'] == [hook]


class TestNormalizeYoutubeCollectionUrl:
    """Tests for YouTube collection URL normalization."""

    def test_adds_videos_tab_to_handle_root(self):
        """Should use the videos tab for channel handle roots."""
        url = normalize_youtube_collection_url("https://www.youtube.com/@rinconapologetico")
        assert url == "https://www.youtube.com/@rinconapologetico/videos"

    def test_adds_videos_tab_to_channel_root(self):
        """Should use the videos tab for channel ID roots."""
        url = normalize_youtube_collection_url("https://www.youtube.com/channel/UCabc123")
        assert url == "https://www.youtube.com/channel/UCabc123/videos"

    def test_leaves_playlist_urls_unchanged(self):
        """Should not alter playlist URLs."""
        url = "https://www.youtube.com/playlist?list=PLabc123"
        assert normalize_youtube_collection_url(url) == url

    def test_leaves_watch_urls_unchanged(self):
        """Should not alter individual video URLs."""
        url = "https://www.youtube.com/watch?v=abc123"
        assert normalize_youtube_collection_url(url) == url

    def test_leaves_existing_channel_tab_unchanged(self):
        """Should not duplicate an existing channel tab."""
        url = "https://www.youtube.com/@rinconapologetico/shorts"
        assert normalize_youtube_collection_url(url) == url


class TestDownloaderChannelUrls:
    """Tests for channel URL handling in downloader operations."""

    def test_get_channel_info_uses_videos_tab_for_channel_roots(self, monkeypatch, tmp_path):
        """Should fetch channel info from the videos tab for accurate counts."""
        calls = []

        class FakeYoutubeDL:
            def __init__(self, opts):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                pass

            def extract_info(self, url, download=False):
                calls.append(url)
                return {
                    'title': 'Channel - Videos',
                    'channel': 'Channel',
                    'playlist_count': 1861,
                    'entries': [{'id': 'a'}],
                }

        monkeypatch.setattr('ytrag.downloader.yt_dlp.YoutubeDL', FakeYoutubeDL)

        info = Downloader(tmp_path).get_channel_info("https://www.youtube.com/@channel")

        assert calls == ["https://www.youtube.com/@channel/videos"]
        assert info['video_count'] == 1861

    def test_download_to_temp_uses_videos_tab_for_channel_roots(self, monkeypatch, tmp_path):
        """Should download channel roots from the videos tab."""
        calls = []

        class FakeYoutubeDL:
            def __init__(self, opts):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                pass

            def download(self, urls):
                calls.extend(urls)

        monkeypatch.setattr('ytrag.downloader.yt_dlp.YoutubeDL', FakeYoutubeDL)
        downloader = Downloader(tmp_path)
        monkeypatch.setattr(downloader.rate_limiter, 'wait', lambda: None)

        temp_dir, _stats = downloader.download_to_temp(
            "https://www.youtube.com/@channel",
            archive_path=tmp_path / ".archive",
        )

        assert calls == ["https://www.youtube.com/@channel/videos"]
        assert temp_dir.exists()
