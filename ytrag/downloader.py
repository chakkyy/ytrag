# ytrag/downloader.py
"""YouTube subtitle downloader using yt-dlp."""

import os
from pathlib import Path
from typing import Optional, Callable
import yt_dlp

from ytrag.rate_limiter import AdaptiveRateLimiter
from ytrag.utils import ARCHIVE_FILE, ensure_dir, is_valid_youtube_url


def get_ydl_options(
    output_dir: str,
    archive_path: str,
    progress_hooks: Optional[list[Callable]] = None,
    subtitles_langs: Optional[list[str]] = None,
) -> dict:
    """Get yt-dlp options configured for subtitle-only download."""
    if subtitles_langs is None:
        subtitles_langs = ['es', 'en', 'es-ES', 'en-US']

    return {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': subtitles_langs,
        'subtitlesformat': 'vtt',
        'download_archive': archive_path,
        'sleep_interval': 1,
        'sleep_interval_requests': 1,
        'outtmpl': f'{output_dir}/%(channel)s/%(upload_date)s_%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'progress_hooks': progress_hooks or [],
    }


def select_best_subtitles(
    subtitles: dict,
    automatic_captions: dict,
    preferred_langs: Optional[list[str]] = None,
) -> Optional[tuple[str, dict]]:
    """Select the best subtitle track from available options."""
    if preferred_langs is None:
        preferred_langs = ['es', 'en', 'es-ES', 'en-US']

    # Try manual subtitles first
    for lang in preferred_langs:
        if lang in subtitles:
            return (lang, subtitles[lang])

    # Any manual subtitle
    if subtitles:
        first_lang = next(iter(subtitles))
        return (first_lang, subtitles[first_lang])

    # Try auto-generated
    for lang in preferred_langs:
        if lang in automatic_captions:
            return (lang, automatic_captions[lang])

    # Any auto subtitle
    if automatic_captions:
        first_lang = next(iter(automatic_captions))
        return (first_lang, automatic_captions[first_lang])

    return None


class Downloader:
    """YouTube subtitle downloader with adaptive rate limiting."""

    def __init__(
        self,
        output_dir: Path,
        on_subtitle_downloaded: Optional[Callable[[Path], None]] = None,
        rate_limiter: Optional[AdaptiveRateLimiter] = None,
    ):
        self.output_dir = Path(output_dir)
        self.archive_path = self.output_dir / ARCHIVE_FILE
        self.on_subtitle_downloaded = on_subtitle_downloaded
        self.rate_limiter = rate_limiter or AdaptiveRateLimiter()
        ensure_dir(self.output_dir)

    def _create_progress_hook(self) -> Callable:
        """Create progress hook for yt-dlp."""
        def hook(d: dict):
            if d['status'] == 'finished':
                filename = d.get('filename', '')
                if filename.endswith('.vtt') and self.on_subtitle_downloaded:
                    self.on_subtitle_downloaded(Path(filename))
        return hook

    def get_channel_info(self, url: str) -> dict:
        """Get channel/playlist info without downloading."""
        if not is_valid_youtube_url(url):
            raise ValueError(f"Invalid YouTube URL: {url}")

        opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return {
            'title': info.get('title', info.get('channel', 'Unknown')),
            'channel': info.get('channel', info.get('uploader', 'Unknown')),
            'video_count': len(info.get('entries', [])) if 'entries' in info else 1,
            'url': url,
        }

    def download(self, url: str, langs: Optional[list[str]] = None) -> dict:
        """Download subtitles from URL."""
        if not is_valid_youtube_url(url):
            raise ValueError(f"Invalid YouTube URL: {url}")

        progress_hooks = [self._create_progress_hook()]
        opts = get_ydl_options(
            output_dir=str(self.output_dir),
            archive_path=str(self.archive_path),
            progress_hooks=progress_hooks,
            subtitles_langs=langs,
        )
        stats = {'downloaded': 0, 'skipped': 0, 'errors': 0}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
                stats['downloaded'] += 1
            self.rate_limiter.on_success()
        except yt_dlp.utils.DownloadError as e:
            if '429' in str(e) or 'Too Many Requests' in str(e):
                self.rate_limiter.on_rate_limit()
            stats['errors'] += 1

        self.rate_limiter.wait()
        return stats
