# ytrag/consolidator.py
"""Consolidate transcripts into LLM-ready volumes."""

import json
import math
import re
from pathlib import Path
from datetime import datetime

from ytrag.utils import ensure_dir, sanitize_filename

# Configuration
TRANSCRIPTS_PER_VOLUME = 50
SEPARATOR = "\n\n---\n[FIN DE TRANSCRIPCION]\n---\n\n"
DATE_PREFIX = re.compile(r'^(?P<date>\d{4})(?P<month>\d{2})(?P<day>\d{2})_(?P<title>.+)$')


def calculate_transcripts_per_volume(
    total_transcripts: int,
    target_volumes: int = 50,
    per_volume: int | None = None,
) -> int:
    """Calculate transcripts per volume from an explicit override or target count."""
    if per_volume is not None:
        return max(1, per_volume)
    if total_transcripts <= 0:
        return TRANSCRIPTS_PER_VOLUME
    return max(1, math.ceil(total_transcripts / max(1, target_volumes)))


def extract_video_metadata(base_name: str) -> dict:
    """Extract friendly date/title metadata from a transcript base name."""
    match = DATE_PREFIX.match(base_name)
    if not match:
        return {'date': None, 'title': base_name, 'label': base_name}

    date = f"{match.group('date')}-{match.group('month')}-{match.group('day')}"
    title = match.group('title').strip()
    return {'date': date, 'title': title, 'label': f"{date} · {title}"}


def format_transcript(transcript: dict, source_marker_frequency: int = 3) -> str:
    """Format a single transcript for inclusion in a volume."""
    metadata = extract_video_metadata(transcript['base_name'])
    source_marker = f"[Fuente: {metadata['label']}]"
    paragraphs = [p.strip() for p in transcript['content'].split('\n\n') if p.strip()]
    body_parts = []
    frequency = max(1, source_marker_frequency)

    for index, paragraph in enumerate(paragraphs):
        if index % frequency == 0:
            body_parts.append(f"{source_marker}\n{paragraph}")
        else:
            body_parts.append(paragraph)

    lines = [
        f"## {metadata['label']}",
        f"**Idioma:** {transcript['language']}",
        f"**Canal:** {transcript['channel']}",
        f"**Fecha:** {metadata['date'] or 'Sin fecha'}",
        f"**Video:** {metadata['title']}",
        f"**Archivo fuente:** {transcript['source_file']}",
        "---\n",
        "\n\n".join(body_parts),
    ]
    return '\n'.join(lines)


def create_volumes(
    transcripts: list[dict],
    output_dir: Path,
    channel_name: str,
    transcripts_per_volume: int = TRANSCRIPTS_PER_VOLUME,
    source_marker_frequency: int = 3,
) -> dict:
    """
    Create consolidated volumes from transcripts.

    Args:
        transcripts: List of transcript dicts from cleaner
        output_dir: Directory to write volumes (channel folder)
        channel_name: Name of the channel
        transcripts_per_volume: How many transcripts per volume file

    Returns:
        Dict with consolidation stats
    """
    if not transcripts:
        return {'total': 0, 'volumes': [], 'skipped': []}

    ensure_dir(output_dir)
    for stale_volume in output_dir.glob("*_Vol*.txt"):
        stale_volume.unlink()

    total_transcripts = len(transcripts)
    total_volumes = math.ceil(total_transcripts / transcripts_per_volume)

    volumes = []

    for vol_num in range(total_volumes):
        start = vol_num * transcripts_per_volume
        end = start + transcripts_per_volume
        batch = transcripts[start:end]

        volume_name = f"{channel_name}_Vol{vol_num + 1:02d}.txt"
        volume_path = output_dir / volume_name

        content_parts = []
        index_entries = []

        # Volume header
        content_parts.append(f"=== COLECCIÓN: {channel_name} ===\n")
        content_parts.append(f"=== VOLUMEN: {vol_num + 1} de {total_volumes} ===\n")
        content_parts.append(f"=== CONTENIDO: Transcripciones {start + 1} a {start + len(batch)} ===\n\n")

        for idx, transcript in enumerate(batch):
            # Format and add transcript
            formatted = format_transcript(transcript, source_marker_frequency=source_marker_frequency)
            content_parts.append(formatted)

            # Add to index
            index_entries.append(f"{start + idx + 1}. {transcript['base_name']}")

            # Add separator between transcripts (not after last one)
            if idx < len(batch) - 1:
                content_parts.append(SEPARATOR)

        # Add index at the end
        if index_entries:
            content_parts.append("\n\n" + "=" * 60 + "\n")
            content_parts.append("=== ÍNDICE DE ESTE VOLUMEN ===\n")
            content_parts.append("=" * 60 + "\n\n")
            content_parts.append("\n".join(index_entries))
            content_parts.append("\n")

        volume_path.write_text("".join(content_parts), encoding='utf-8')
        volumes.append(volume_name)

    return {
        'total': total_transcripts,
        'volumes': volumes,
        'skipped': [],
    }


def create_clean_transcript_files(
    transcripts: list[dict],
    output_dir: Path,
    source_marker_frequency: int = 3,
) -> list[str]:
    """Write one clean markdown transcript per video."""
    ensure_dir(output_dir)
    for stale_transcript in output_dir.glob("*.md"):
        stale_transcript.unlink()

    files = []
    for transcript in transcripts:
        filename = f"{sanitize_filename(transcript['base_name'])}.md"
        path = output_dir / filename
        path.write_text(
            format_transcript(transcript, source_marker_frequency=source_marker_frequency),
            encoding='utf-8',
        )
        files.append(filename)

    return files


def write_manifest(
    output_dir: Path,
    channel_name: str,
    stats: dict,
) -> Path:
    """Write manifest.json with consolidation metadata."""
    manifest = {
        'generated_at': datetime.now().isoformat(),
        'channel': channel_name,
        'total_transcripts': stats['total'],
        'volumes': stats['volumes'],
        'clean_transcripts': stats.get('clean_transcripts'),
        'skipped': stats['skipped'] if stats['skipped'] else None,
    }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )

    return manifest_path
