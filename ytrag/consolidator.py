# ytrag/consolidator.py
"""Consolidate markdown files into LLM-ready volumes."""

import os
import json
import math
from pathlib import Path
from datetime import datetime
from typing import Optional

from ytrag.utils import BIBLIOTECA_FOLDER, EXPORTS_FOLDER, ensure_dir

# Configuration
TRANSCRIPTS_PER_VOLUME = 100
SEPARATOR = "\n\n---\n[FIN DE TRANSCRIPCION]\n---\n\n"


def validate_markdown_file(content: str) -> bool:
    """Validate that content is a properly formatted markdown file."""
    if not content:
        return False
    return content.strip().startswith("# ")


def extract_title(content: str) -> str:
    """Extract title from markdown content."""
    first_line = content.split('\n')[0]
    return first_line.lstrip('# ').strip()


def consolidate_channel(
    channel_biblioteca: Path,
    exports_dir: Path,
    channel_name: str,
    transcripts_per_volume: int = TRANSCRIPTS_PER_VOLUME,
) -> dict:
    """Consolidate a single channel's markdown files into volumes."""
    md_files = sorted(channel_biblioteca.glob("*.md"))

    if not md_files:
        return {'total': 0, 'volumes': [], 'skipped': []}

    total_files = len(md_files)
    total_volumes = math.ceil(total_files / transcripts_per_volume)

    volumes = []
    skipped = []

    for vol_num in range(total_volumes):
        start = vol_num * transcripts_per_volume
        end = start + transcripts_per_volume
        batch = md_files[start:end]

        volume_name = f"{channel_name}_Vol{vol_num + 1:02d}.txt"
        volume_path = exports_dir / volume_name

        content_parts = []
        index_entries = []
        included_count = 0

        # Volume header
        content_parts.append(f"=== COLECCIÓN: {channel_name} ===\n")
        content_parts.append(f"=== VOLUMEN: {vol_num + 1} de {total_volumes} ===\n")
        content_parts.append(f"=== CONTENIDO: Transcripciones {start + 1} a {start + len(batch)} ===\n\n")

        for idx, md_file in enumerate(batch):
            try:
                file_content = md_file.read_text(encoding='utf-8')

                if not validate_markdown_file(file_content):
                    skipped.append(md_file.name)
                    continue

                title = extract_title(file_content)
                index_entries.append(f"{start + included_count + 1}. {title}")

                content_parts.append(file_content)
                included_count += 1

                if idx < len(batch) - 1:
                    content_parts.append(SEPARATOR)

            except Exception:
                skipped.append(md_file.name)

        # Add index at the end
        if index_entries:
            content_parts.append("\n\n" + "=" * 60 + "\n")
            content_parts.append("=== ÍNDICE DE ESTE VOLUMEN ===\n")
            content_parts.append("=" * 60 + "\n\n")
            content_parts.append("\n".join(index_entries))
            content_parts.append("\n")

        volume_path.write_text("".join(content_parts), encoding='utf-8')
        volumes.append(volume_name)

    return {'total': total_files, 'volumes': volumes, 'skipped': skipped}


def consolidate_all(
    base_dir: str | Path,
    transcripts_per_volume: int = TRANSCRIPTS_PER_VOLUME,
) -> dict:
    """Consolidate all channels in base directory."""
    base_dir = Path(base_dir)
    biblioteca_dir = base_dir / BIBLIOTECA_FOLDER
    exports_dir = ensure_dir(base_dir / EXPORTS_FOLDER)

    manifest = {
        'generated_at': datetime.now().isoformat(),
        'working_directory': str(base_dir),
        'channels': {},
    }

    if not biblioteca_dir.exists():
        return manifest

    for channel_dir in biblioteca_dir.iterdir():
        if not channel_dir.is_dir():
            continue

        channel_name = channel_dir.name

        result = consolidate_channel(
            channel_biblioteca=channel_dir,
            exports_dir=exports_dir,
            channel_name=channel_name,
            transcripts_per_volume=transcripts_per_volume,
        )

        manifest['channels'][channel_name] = {
            'total_transcripciones': result['total'],
            'volumenes': result['volumes'],
            'archivos_omitidos': result['skipped'] if result['skipped'] else None,
        }

    # Save manifest
    manifest_path = exports_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )

    return manifest
