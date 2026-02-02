# ytrag/downloader.py
"""YouTube subtitle downloader using yt-dlp."""

import tempfile
import shutil
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
        subtitles_langs = ['en']  # Fallback to English if nothing specified

    return {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': subtitles_langs,
        'subtitlesformat': 'vtt',
        'download_archive': archive_path,
        'sleep_interval': 1,
        'sleep_interval_requests': 1,
        'outtmpl': f'{output_dir}/%(upload_date)s_%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'progress_hooks': progress_hooks or [],
    }


class Downloader:
    """YouTube subtitle downloader with streaming processing."""

    def __init__(
        self,
        output_dir: Path,
        rate_limiter: Optional[AdaptiveRateLimiter] = None,
    ):
        self.output_dir = Path(output_dir)
        self.rate_limiter = rate_limiter or AdaptiveRateLimiter()
        ensure_dir(self.output_dir)

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

        # Try to detect default language from channel/video metadata
        default_lang = info.get('language') or info.get('original_language')

        return {
            'title': info.get('title', info.get('channel', 'Unknown')),
            'channel': info.get('channel', info.get('uploader', 'Unknown')),
            'video_count': len(info.get('entries', [])) if 'entries' in info else 1,
            'url': url,
            'default_language': default_lang,
        }

    def download_to_temp(
        self,
        url: str,
        langs: Optional[list[str]] = None,
        archive_path: Optional[Path] = None,
    ) -> tuple[Path, dict]:
        """
        Download subtitles to a temporary directory.

        Returns:
            Tuple of (temp_dir_path, stats_dict)
            Caller is responsible for cleaning up temp_dir.
        """
        if not is_valid_youtube_url(url):
            raise ValueError(f"Invalid YouTube URL: {url}")

        # Create temp directory for downloads
        temp_dir = Path(tempfile.mkdtemp(prefix='ytrag_'))

        # Use provided archive path or create one in output dir
        if archive_path is None:
            archive_path = self.output_dir / ARCHIVE_FILE

        opts = get_ydl_options(
            output_dir=str(temp_dir),
            archive_path=str(archive_path),
            subtitles_langs=langs,
        )

        stats = {'downloaded': 0, 'skipped': 0, 'errors': 0}

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            self.rate_limiter.on_success()
        except yt_dlp.utils.DownloadError as e:
            if '429' in str(e) or 'Too Many Requests' in str(e):
                self.rate_limiter.on_rate_limit()
            stats['errors'] += 1

        self.rate_limiter.wait()

        # Count downloaded files
        vtt_files = list(temp_dir.glob('*.vtt'))
        stats['downloaded'] = len(vtt_files)

        return temp_dir, stats
