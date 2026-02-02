# ytrag/main.py
"""ytrag CLI - YouTube transcripts to RAG-ready volumes."""

import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel

from ytrag import __version__
from ytrag.downloader import Downloader
from ytrag.cleaner import process_vtt_directory
from ytrag.consolidator import create_volumes, write_manifest
from ytrag.utils import ARCHIVE_FILE, ensure_dir

app = typer.Typer(
    name="ytrag",
    help="YouTube transcripts -> RAG-ready volumes",
    add_completion=False,
)
console = Console()


def version_callback(value: bool):
    """Show version and exit."""
    if value:
        console.print(f"ytrag version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
):
    """ytrag - YouTube transcripts to RAG-ready volumes."""
    pass


@app.command(name="all")
def all_pipeline(
    url: str = typer.Argument(..., help="YouTube URL"),
    output: Path = typer.Option(".", "--output", "-o", help="Output directory"),
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Subtitle languages. Defaults to video's language."),
    per_volume: int = typer.Option(100, "--per-volume", "-n", help="Transcripts per volume"),
):
    """Download YouTube transcripts and create RAG-ready volumes."""
    output = Path(output).resolve()

    console.print(Panel.fit(
        f"[bold blue]ytrag[/] v{__version__}\n{url}",
        title="ytrag",
    ))

    downloader = Downloader(output_dir=output)

    # Get channel info
    with console.status("[bold green]Connecting to YouTube..."):
        try:
            info = downloader.get_channel_info(url)
        except Exception as e:
            console.print(f"[red]Error:[/] Could not fetch info: {e}")
            raise typer.Exit(1)

    channel_name = info['channel']

    # Determine languages
    if lang:
        langs = [l.strip() for l in lang.split(",")]
    else:
        default_lang = info.get('default_language') or 'en'
        langs = [default_lang]
        console.print(f"  [dim]Language: {default_lang}[/]")

    console.print(f"  Channel: {channel_name}")
    console.print(f"  Videos: {info['video_count']}")

    # Create channel output directory
    channel_dir = ensure_dir(output / channel_name)
    archive_path = channel_dir / ARCHIVE_FILE

    # Download to temp directory
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  BarColumn(), TaskProgressColumn(), console=console) as progress:
        task = progress.add_task("Downloading subtitles...", total=None)
        temp_dir, download_stats = downloader.download_to_temp(
            url, langs=langs, archive_path=archive_path
        )

    try:
        # Process VTT files
        with console.status("[bold green]Processing transcripts..."):
            transcripts = process_vtt_directory(temp_dir, channel_name)

        if not transcripts:
            console.print("\n[yellow]No new transcripts to process.[/]")
            raise typer.Exit(0)

        console.print(f"\n  Processed: {len(transcripts)} transcripts")

        # Create volumes
        with console.status("[bold green]Creating volumes..."):
            stats = create_volumes(
                transcripts=transcripts,
                output_dir=channel_dir,
                channel_name=channel_name,
                transcripts_per_volume=per_volume,
            )
            write_manifest(channel_dir, channel_name, stats)

        console.print(f"  Volumes: {len(stats['volumes'])}")
        console.print(f"\n[bold green]Done![/] Output: {channel_dir}")

    finally:
        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.command()
def status(
    directory: Path = typer.Argument(".", help="Directory to check"),
):
    """Show status of ytrag output."""
    directory = Path(directory).resolve()

    # Find channel folders (folders with volumes)
    channels = []
    for item in directory.iterdir():
        if item.is_dir():
            volumes = list(item.glob("*_Vol*.txt"))
            manifest = item / "manifest.json"
            if volumes or manifest.exists():
                channels.append({
                    'name': item.name,
                    'volumes': len(volumes),
                    'has_manifest': manifest.exists(),
                })

    if not channels:
        console.print(Panel.fit(
            f"[bold blue]ytrag[/] Status\n\n"
            f"Directory: {directory}\n\n"
            f"No ytrag output found.",
            title="Status",
        ))
        return

    status_lines = [f"Directory: {directory}\n"]
    for ch in channels:
        status_lines.append(f"\n{ch['name']}:")
        status_lines.append(f"  Volumes: {ch['volumes']}")

    console.print(Panel.fit(
        f"[bold blue]ytrag[/] Status\n\n" + "\n".join(status_lines),
        title="Status",
    ))


if __name__ == "__main__":
    app()
