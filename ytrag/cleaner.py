"""VTT cleaner module for converting subtitles to clean, readable text."""

import re
from pathlib import Path
from typing import Optional

from ytrag.utils import (
    extract_base_name,
    is_regional_variant,
    get_language_from_filename,
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
    """Convert VTT timestamp (HH:MM:SS.mmm) to seconds."""
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
    """Capitalize the first letter after sentence-ending punctuation and at the start."""
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
        line = RE_POSITION_ATTRS.sub('', line).strip()
        line = RE_INLINE_TIMESTAMP.sub('', line)
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
        paragraph = ' '.join(block['text'])
        paragraph = RE_MULTIPLE_SPACES.sub(' ', paragraph).strip()
        if paragraph:
            paragraphs.append(paragraph)

    # Join paragraphs with double newline
    final_text = '\n\n'.join(paragraphs)

    # Capitalize sentences
    final_text = capitalize_sentences(final_text)

    return final_text


def process_vtt_file(vtt_path: Path, channel_name: str) -> Optional[dict]:
    """
    Process a single VTT file and return cleaned content.

    Returns:
        Dict with keys: base_name, language, content, source_file
        Or None if processing failed or content is empty.
    """
    try:
        filename = vtt_path.name
        base_name = extract_base_name(filename)
        language = get_language_from_filename(filename)

        content = vtt_path.read_text(encoding='utf-8', errors='ignore')
        cleaned = clean_vtt_content(content)

        if not cleaned.strip():
            return None

        return {
            'base_name': base_name,
            'language': language,
            'content': cleaned,
            'source_file': filename,
            'channel': channel_name,
        }
    except Exception:
        return None


def process_vtt_directory(temp_dir: Path, channel_name: str) -> list[dict]:
    """
    Process all VTT files in a directory.

    Returns list of processed transcript dicts, sorted by base_name.
    Handles deduplication (prefers non-regional variants).
    """
    vtt_files = list(temp_dir.glob('*.vtt'))

    # Sort to process non-regional variants first
    def sort_key(f: Path) -> tuple[int, str]:
        return (1 if is_regional_variant(f.name) else 0, f.name)

    vtt_files.sort(key=sort_key)

    processed_bases: set[str] = set()
    results: list[dict] = []

    for vtt_file in vtt_files:
        base_name = extract_base_name(vtt_file.name)

        # Skip if already processed (deduplication)
        if base_name in processed_bases:
            continue

        result = process_vtt_file(vtt_file, channel_name)
        if result:
            results.append(result)
            processed_bases.add(base_name)

    # Sort by base_name (which typically starts with date)
    results.sort(key=lambda x: x['base_name'])

    return results
