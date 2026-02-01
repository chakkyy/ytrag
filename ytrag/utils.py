"""Utility functions for ytrag."""

import os
import re
from pathlib import Path

# Folders to ignore when scanning
IGNORE_FOLDERS = {'__pycache__', '.git', '.vscode', 'venv', 'env', '_biblioteca', '_exports'}

# Output folder names
BIBLIOTECA_FOLDER = "_biblioteca"
EXPORTS_FOLDER = "_exports"
ARCHIVE_FILE = ".ytrag_archive.txt"


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


def get_output_paths(base_dir: Path) -> dict:
    """Get standard output paths for ytrag."""
    return {
        'biblioteca': base_dir / BIBLIOTECA_FOLDER,
        'exports': base_dir / EXPORTS_FOLDER,
        'archive': base_dir / ARCHIVE_FILE,
    }


def ensure_dir(path: Path) -> Path:
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_filename(name: str) -> str:
    """Remove or replace invalid filename characters."""
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
    name = re.sub(r'\.(en|es|en-US|es-ES)?\.vtt$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\.vtt$', '', name, flags=re.IGNORECASE)
    return name


def is_regional_variant(filepath: str) -> bool:
    """Check if file is a regional variant (en-US vs en)."""
    name = os.path.basename(filepath).lower()
    return '.en-us.' in name or '.es-es.' in name or '_en-us.' in name or '_es-es.' in name


def get_language_from_filename(filename: str) -> str:
    """Extract language code from filename."""
    name = filename.lower()
    if '.en-us.' in name or '_en-us.' in name:
        return 'EN-US'
    if '.en.' in name or '_en.' in name:
        return 'EN'
    if '.es-es.' in name or '_es-es.' in name:
        return 'ES-ES'
    if '.es.' in name or '_es.' in name:
        return 'ES'
    return 'ES'  # Default


def get_output_filename(base_name: str, language: str) -> str:
    """Get consistent output filename for markdown files."""
    return f"{base_name} [{language}].md"


def create_subtitle_callback(
    output_dir: Path,
    verbose: bool = False,
    console=None
):
    """
    Create a callback for processing downloaded subtitle files.
    
    Args:
        output_dir: Base output directory
        verbose: If True, print progress messages
        console: Rich Console instance for output (required if verbose)
    
    Returns:
        Callback function that processes VTT files to markdown
    """
    # Import here to avoid circular imports
    from ytrag.cleaner import clean_vtt_content, create_markdown_output, get_file_info
    
    def on_subtitle_downloaded(path: Path):
        try:
            content = path.read_text(encoding='utf-8', errors='ignore')
            cleaned = clean_vtt_content(content)
            if cleaned:
                base_name, language = get_file_info(path.name)
                channel = path.parent.name
                biblioteca_dir = ensure_dir(output_dir / BIBLIOTECA_FOLDER / channel)
                output_file = biblioteca_dir / get_output_filename(base_name, language)
                markdown = create_markdown_output(
                    content=cleaned,
                    base_name=base_name,
                    language=language,
                    source_file=path.name,
                    channel=channel,
                )
                output_file.write_text(markdown, encoding='utf-8')
                if verbose and console:
                    console.print(f"  Cleaned: {output_file.name}")
        except Exception as e:
            if verbose and console:
                console.print(f"  [yellow]Warning:[/] Error cleaning {path.name}: {e}")
    
    return on_subtitle_downloaded

