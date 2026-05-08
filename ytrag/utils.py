"""Utility functions for ytrag."""

import os
import re
from pathlib import Path

# Archive file to track processed videos
ARCHIVE_FILE = ".ytrag_archive"
LANGUAGE_SUFFIX_RE = re.compile(r'\.([a-z]{2,3}(?:-[a-z0-9]{2,8})?)\.vtt$', re.IGNORECASE)


def is_valid_youtube_url(url: str) -> bool:
    """
    Validate URL is a YouTube URL.

    Matches:
    - youtube.com (with or without www/m prefix)
    - youtu.be (short URLs)
    """
    youtube_pattern = re.compile(
        r'^https?://'
        r'(www\.|m\.)?'
        r'(youtube\.com|youtu\.be)'
        r'/.*$',
        re.IGNORECASE
    )
    return bool(youtube_pattern.match(url))


def ensure_dir(path: Path) -> Path:
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_filename(name: str) -> str:
    """Remove or replace invalid filename characters."""
    # Prevent path traversal
    name = name.replace('..', '_')
    # Replace problematic characters
    name = name.replace('/', '⧸').replace('\\', '⧸')
    name = name.replace(':', '：').replace('|', '｜')
    name = name.replace('?', '？').replace('"', '＂')
    name = name.replace('<', '＜').replace('>', '＞')
    name = name.replace('*', '＊')
    return name.strip()


def extract_base_name(filepath: str) -> str:
    """
    Extract base name without language suffix and extension.
    '20251226_Video Title.en.vtt' -> '20251226_Video Title'
    """
    name = os.path.basename(filepath)
    # Remove extension(s)
    name = LANGUAGE_SUFFIX_RE.sub('', name)
    name = re.sub(r'\.vtt$', '', name, flags=re.IGNORECASE)
    return name


def is_regional_variant(filepath: str) -> bool:
    """Check if file is a regional variant (en-US vs en)."""
    name = os.path.basename(filepath).lower()
    return '.en-us.' in name or '.es-es.' in name or '_en-us.' in name or '_es-es.' in name


def get_language_from_filename(filename: str) -> str:
    """Extract language code from filename."""
    match = LANGUAGE_SUFFIX_RE.search(os.path.basename(filename))
    if match:
        return match.group(1).upper()
    return 'ES'  # Default
