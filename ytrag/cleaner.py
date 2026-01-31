"""VTT cleaner module for converting subtitles to clean, readable text."""

import logging
import os
import re
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ProcessResult(Enum):
    """Result of processing a single VTT file."""
    SUCCESS = "success"
    SKIPPED_DUPLICATE = "skipped_duplicate"
    SKIPPED_REGIONAL = "skipped_regional"
    SKIPPED_EMPTY = "skipped_empty"
    ERROR = "error"


logger = logging.getLogger(__name__)

from ytrag.utils import (
    IGNORE_FOLDERS,
    BIBLIOTECA_FOLDER,
    ensure_dir,
    is_regional_variant,
    get_language_from_filename,
    extract_base_name,
)

# Useless markers to filter (case-insensitive)
USELESS_MARKERS = {
    '[music]', '[applause]', '[laughter]', '[cheering]', '[silence]',
    '[inaudible]', '[crosstalk]', '[noise]', '[background noise]',
    '[foreign]', '[speaking foreign language]', '[no audio]',
    '[pause]', '[sighs]', '[coughs]', '[clears throat]',
}

# Precompiled regex patterns for performance
RE_TIMESTAMP_LINE = re.compile(r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})')
RE_HTML_TAGS = re.compile(r'<[^>]+>')
RE_POSITION_ATTRS = re.compile(r'align:\w+|position:\d+%')
RE_INLINE_TIMESTAMP = re.compile(r'<\d{2}:\d{2}:\d{2}\.\d{3}>')
RE_MULTIPLE_SPACES = re.compile(r'\s+')


def parse_vtt_timestamp(timestamp: str) -> Optional[float]:
    """
    Convert VTT timestamp (HH:MM:SS.mmm) to seconds.

    Args:
        timestamp: Timestamp string in HH:MM:SS.mmm format

    Returns:
        Float seconds, or None if parsing fails
    """
    if not timestamp:
        return None
    try:
        parts = timestamp.split(':')
        if len(parts) != 3:
            return None
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    except (ValueError, IndexError):
        return None


def capitalize_sentences(text: str) -> str:
    """
    Capitalize the first letter after sentence-ending punctuation and at the start.

    Args:
        text: Input text to capitalize

    Returns:
        Text with properly capitalized sentences
    """
    if not text:
        return text

    # Capitalize start
    text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()

    # Capitalize after sentence-ending punctuation
    result = []
    capitalize_next = False

    for i, char in enumerate(text):
        if capitalize_next and char.isalpha():
            result.append(char.upper())
            capitalize_next = False
        else:
            result.append(char)

        if char in '.?!' and i < len(text) - 1:
            capitalize_next = True

    return ''.join(result)


def clean_vtt_content(content: str, pause_threshold: float = 2.5) -> str:
    """
    Clean VTT content and convert it to coherent paragraphs.

    Uses pauses between timestamps to detect paragraph breaks.

    Args:
        content: Raw VTT file content
        pause_threshold: Seconds of pause to trigger paragraph break

    Returns:
        Cleaned text with proper paragraphs
    """
    if not content:
        return ""

    # First pass: extract blocks with timestamps
    blocks = []
    current_end_time: Optional[float] = None
    current_block_text: list[str] = []
    seen_lines: set[str] = set()

    lines = content.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Skip metadata lines
        if (not line or
            line == "WEBVTT" or
            line.startswith("Kind:") or
            line.startswith("Language:") or
            line.isdigit()):
            i += 1
            continue

        # Detect timestamp line
        match_time = RE_TIMESTAMP_LINE.search(line)
        if match_time:
            start_time = parse_vtt_timestamp(match_time.group(1))
            end_time = parse_vtt_timestamp(match_time.group(2))

            # Check for significant pause (new paragraph)
            if current_end_time is not None and start_time is not None:
                pause = start_time - current_end_time
                if pause >= pause_threshold and current_block_text:
                    # Save current block and start new paragraph
                    blocks.append({
                        'text': current_block_text.copy(),
                        'is_new_paragraph': True
                    })
                    current_block_text = []
                    seen_lines = set()

            current_end_time = end_time
            i += 1
            continue

        # Process text line
        # Remove position attributes that sometimes remain on the line
        line = RE_POSITION_ATTRS.sub('', line).strip()

        # Remove inline timestamps like <00:00:01.000>
        line = RE_INLINE_TIMESTAMP.sub('', line)

        # Remove HTML tags
        plain_text = RE_HTML_TAGS.sub('', line)

        # Replace HTML entities
        plain_text = (plain_text
            .replace('&nbsp;', ' ')
            .replace('&amp;', '&')
            .replace('&#39;', "'")
            .replace('&quot;', '"')
            .replace('  ', ' ')
            .strip())

        # Filter useless markers
        if plain_text.lower() in USELESS_MARKERS:
            i += 1
            continue

        # Also filter if contains only a marker
        text_without_marker = plain_text
        for marker in USELESS_MARKERS:
            text_without_marker = text_without_marker.lower().replace(marker, '').strip()
        if not text_without_marker:
            i += 1
            continue

        # Deduplicate
        if plain_text and plain_text not in seen_lines:
            current_block_text.append(plain_text)
            seen_lines.add(plain_text)

        i += 1

    # Add last block
    if current_block_text:
        blocks.append({
            'text': current_block_text,
            'is_new_paragraph': False
        })

    # Second pass: join lines into paragraphs
    paragraphs = []

    for block in blocks:
        if not block['text']:
            continue

        # Join all lines of the block into a paragraph
        paragraph = ' '.join(block['text'])

        # Clean multiple spaces
        paragraph = RE_MULTIPLE_SPACES.sub(' ', paragraph).strip()

        if paragraph:
            paragraphs.append(paragraph)

    # Join paragraphs with double newline
    final_text = '\n\n'.join(paragraphs)

    # Capitalize sentences
    final_text = capitalize_sentences(final_text)

    return final_text


def select_best_subtitle_file(files: list[str], base_name: str) -> Optional[str]:
    """
    Select the best subtitle file from a list of candidates.

    Prefers non-regional variants (e.g., .en.vtt over .en-US.vtt).

    Args:
        files: List of subtitle filenames
        base_name: Base name of the video file

    Returns:
        Best matching filename, or None if no match
    """
    matching_files = [f for f in files if f.startswith(base_name)]

    if not matching_files:
        return None

    # Prefer non-regional variant
    for f in matching_files:
        # Check if it's a simple language code (e.g., .en.vtt) not regional (e.g., .en-US.vtt)
        if re.search(r'\.[a-z]{2}\.vtt$', f, re.IGNORECASE):
            return f

    # Return any matching file if no non-regional found
    return matching_files[0]


def get_file_info(filename: str) -> tuple[str, str]:
    """
    Extract base name and language from subtitle filename.

    Args:
        filename: Subtitle filename

    Returns:
        Tuple of (base_name, language_code)
    """
    language = "ES"
    if ".en." in filename.lower() or "_en." in filename.lower():
        language = "EN"
    elif ".es." in filename.lower() or "_es." in filename.lower():
        language = "ES"

    # Remove double extension (e.g., .en.vtt -> base)
    base_name = os.path.splitext(os.path.splitext(filename)[0])[0]

    return base_name, language


def create_markdown_output(
    content: str,
    base_name: str,
    language: str,
    source_file: str,
    channel: Optional[str] = None
) -> str:
    """
    Create markdown-formatted output from cleaned content.

    Args:
        content: Cleaned transcript text
        base_name: Video base name (used as title)
        language: Language code (EN, ES, etc.)
        source_file: Original subtitle filename
        channel: Optional channel name

    Returns:
        Markdown-formatted string
    """
    lines = [
        f"# {base_name}",
        f"**Idioma:** {language}",
        f"**Fuente:** {source_file}",
    ]

    if channel:
        lines.insert(2, f"**Canal:** {channel}")

    lines.append("---\n")
    lines.append(content)

    return '\n'.join(lines)


def process_single_file(
    vtt_path: Path,
    output_dir: Path,
    channel_name: str,
    processed_bases: set[str]
) -> tuple[Optional[str], ProcessResult]:
    """
    Process a single VTT file and write markdown output.

    Args:
        vtt_path: Path to the VTT file
        output_dir: Directory to write markdown output
        channel_name: Name of the channel (folder name)
        processed_bases: Set of already processed base names (for deduplication)

    Returns:
        Tuple of (output_path, result_type). output_path is None if not processed.
    """
    try:
        filename = vtt_path.name
        base_name = extract_base_name(filename)

        # Skip if we already processed this base (deduplication)
        if base_name in processed_bases:
            return None, ProcessResult.SKIPPED_DUPLICATE

        # Skip regional variant if non-regional exists
        if is_regional_variant(filename):
            # Check if non-regional version exists in same directory
            non_regional_patterns = [
                vtt_path.parent / f"{base_name}.en.vtt",
                vtt_path.parent / f"{base_name}.es.vtt",
            ]
            for pattern in non_regional_patterns:
                if pattern.exists():
                    return None, ProcessResult.SKIPPED_REGIONAL

        # Read and clean VTT content
        content = vtt_path.read_text(encoding='utf-8')
        cleaned = clean_vtt_content(content)

        if not cleaned.strip():
            return None, ProcessResult.SKIPPED_EMPTY

        # Get language from filename
        language = get_language_from_filename(filename)

        # Create markdown output
        markdown = create_markdown_output(
            content=cleaned,
            base_name=base_name,
            language=language,
            source_file=filename,
            channel=channel_name
        )

        # Ensure output directory exists
        channel_output_dir = ensure_dir(output_dir / channel_name)

        # Write output file
        output_path = channel_output_dir / f"{base_name} [{language}].md"
        output_path.write_text(markdown, encoding='utf-8')

        # Mark as processed
        processed_bases.add(base_name)

        return str(output_path), ProcessResult.SUCCESS

    except Exception as e:
        logger.warning(f"Error processing {vtt_path}: {e}")
        return None, ProcessResult.ERROR


def process_directory(
    base_dir: str | Path,
    progress: Any = None,
    task_id: Any = None
) -> dict:
    """
    Process all VTT files in a directory tree.

    Walks the directory tree, finds VTT files, cleans them, and writes
    markdown output to _biblioteca/{channel}/ folders.

    Args:
        base_dir: Base directory to scan
        progress: Optional Rich Progress instance for progress tracking
        task_id: Optional task ID for progress updates

    Returns:
        Dictionary with stats: {'processed': int, 'skipped': int, 'errors': int}
    """
    base_path = Path(base_dir)
    biblioteca_path = ensure_dir(base_path / BIBLIOTECA_FOLDER)

    stats = {'processed': 0, 'skipped': 0, 'errors': 0}

    # Collect all VTT files grouped by channel
    channel_files: dict[str, list[Path]] = {}

    for root, dirs, files in os.walk(base_path):
        # Filter out ignored folders
        dirs[:] = [d for d in dirs if d not in IGNORE_FOLDERS]

        root_path = Path(root)

        # Skip if we're inside _biblioteca
        if BIBLIOTECA_FOLDER in root_path.parts:
            continue

        # Determine channel name (parent folder of VTT files)
        # The channel is the immediate parent of the VTT files
        if root_path == base_path:
            continue  # Skip root level files

        channel_name = root_path.name

        # Collect VTT files
        vtt_files = [root_path / f for f in files if f.lower().endswith('.vtt')]

        if vtt_files:
            if channel_name not in channel_files:
                channel_files[channel_name] = []
            channel_files[channel_name].extend(vtt_files)

    # Process files by channel
    total_files = sum(len(files) for files in channel_files.values())

    if progress and task_id is not None:
        progress.update(task_id, total=total_files)

    processed_count = 0

    for channel_name, vtt_files in channel_files.items():
        # Track processed base names within this channel for deduplication
        processed_bases: set[str] = set()

        # Sort files to process non-regional variants first
        def sort_key(f: Path) -> tuple[int, str]:
            return (1 if is_regional_variant(f.name) else 0, f.name)

        vtt_files.sort(key=sort_key)

        # Process files sequentially (shared state for deduplication)
        for vtt_file in vtt_files:
            output_path, result_type = process_single_file(
                vtt_path=vtt_file,
                output_dir=biblioteca_path,
                channel_name=channel_name,
                processed_bases=processed_bases
            )

            if result_type == ProcessResult.SUCCESS:
                stats['processed'] += 1
            elif result_type == ProcessResult.ERROR:
                stats['errors'] += 1
            else:
                stats['skipped'] += 1

            processed_count += 1
            if progress and task_id is not None:
                progress.update(task_id, completed=processed_count)

    return stats
