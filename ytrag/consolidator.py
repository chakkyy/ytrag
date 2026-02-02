# ytrag/consolidator.py
"""Consolidate transcripts into LLM-ready volumes."""

import json
import math
from pathlib import Path
from datetime import datetime

from ytrag.utils import ensure_dir

# Configuration
TRANSCRIPTS_PER_VOLUME = 100
SEPARATOR = "\n\n---\n[FIN DE TRANSCRIPCION]\n---\n\n"


def format_transcript(transcript: dict) -> str:
    """Format a single transcript for inclusion in a volume."""
    lines = [
        f"# {transcript['base_name']}",
        f"**Idioma:** {transcript['language']}",
        f"**Canal:** {transcript['channel']}",
        f"**Fuente:** {transcript['source_file']}",
        "---\n",
        transcript['content'],
    ]
    return '\n'.join(lines)


def create_volumes(
    transcripts: list[dict],
    output_dir: Path,
    channel_name: str,
    transcripts_per_volume: int = TRANSCRIPTS_PER_VOLUME,
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
            formatted = format_transcript(transcript)
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
        'skipped': stats['skipped'] if stats['skipped'] else None,
    }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )

    return manifest_path
