# ytrag/main.py
"""ytrag CLI - YouTube transcripts to RAG-ready volumes."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel

from ytrag import __version__
from ytrag.downloader import Downloader
from ytrag.cleaner import process_directory
from ytrag.consolidator import consolidate_all
from ytrag.utils import create_subtitle_callback

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


@app.command()
def download(
    url: str = typer.Argument(..., help="YouTube URL (video, playlist, or channel)"),
    output: Path = typer.Option(".", "--output", "-o", help="Output directory"),
    lang: str = typer.Option("es,en", "--lang", "-l", help="Subtitle languages (comma-separated)"),
    verbose: bool = typer.Option(False, "--verbose", help="Show detailed output"),
):
    """Download subtitles from YouTube."""
    output = Path(output).resolve()
    langs = [l.strip() for l in lang.split(",")]

    console.print(Panel.fit(
        f"[bold blue]ytrag[/] v{__version__}\nDownloading subtitles from: {url}",
        title="Download",
    ))

    # Use extracted callback factory
    on_subtitle_downloaded = create_subtitle_callback(
        output_dir=output,
        verbose=verbose,
        console=console
    )

    downloader = Downloader(output_dir=output, on_subtitle_downloaded=on_subtitle_downloaded)

    with console.status("[bold green]Connecting to YouTube..."):
        try:
            info = downloader.get_channel_info(url)
        except Exception as e:
            console.print(f"[red]Error:[/] Could not fetch info: {e}")
            raise typer.Exit(1)

    console.print(f"  Channel: {info['channel']}")
    console.print(f"  Videos: {info['video_count']}")

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  BarColumn(), TaskProgressColumn(), console=console) as progress:
        task = progress.add_task("Downloading...", total=None)
        stats = downloader.download(url, langs=langs)

    console.print("\n[green]Download complete![/]")
    console.print(f"  Output: {output}")


@app.command()
def clean(
    directory: Path = typer.Argument(".", help="Directory containing VTT files"),
):
    """Clean VTT files to markdown."""
    directory = Path(directory).resolve()

    console.print(Panel.fit(
        f"[bold blue]ytrag[/] v{__version__}\nCleaning VTT files in: {directory}",
        title="Clean",
    ))

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  console=console) as progress:
        task = progress.add_task("Processing VTT files...", total=None)
        stats = process_directory(directory)

    console.print("\n[green]Cleaning complete![/]")
    console.print(f"  Processed: {stats['processed']}")
    console.print(f"  Skipped: {stats['skipped']}")
    if stats['errors']:
        console.print(f"  [yellow]Errors: {stats['errors']}[/]")


@app.command()
def consolidate(
    directory: Path = typer.Argument(".", help="Directory containing _biblioteca/"),
    per_volume: int = typer.Option(100, "--per-volume", "-n", help="Transcripts per volume"),
):
    """Consolidate markdown files into volumes."""
    directory = Path(directory).resolve()

    console.print(Panel.fit(
        f"[bold blue]ytrag[/] v{__version__}\nConsolidating: {directory}",
        title="Consolidate",
    ))

    manifest = consolidate_all(directory, transcripts_per_volume=per_volume)

    console.print("\n[green]Consolidation complete![/]")
    for channel, data in manifest.get('channels', {}).items():
        console.print(f"  {channel}: {data['total_transcripciones']} -> {len(data['volumenes'])} volumes")
    console.print(f"\n  Output: {directory}/_exports/")


@app.command(name="all")
def all_pipeline(
    url: str = typer.Argument(..., help="YouTube URL"),
    output: Path = typer.Option(".", "--output", "-o", help="Output directory"),
    lang: str = typer.Option("es,en", "--lang", "-l", help="Subtitle languages"),
    per_volume: int = typer.Option(100, "--per-volume", "-n", help="Transcripts per volume"),
):
    """Full pipeline: download -> clean -> consolidate."""
    output = Path(output).resolve()
    langs = [l.strip() for l in lang.split(",")]

    console.print(Panel.fit(
        f"[bold blue]ytrag[/] v{__version__}\nFull pipeline for: {url}",
        title="ytrag",
    ))

    # Use extracted callback factory (non-verbose for pipeline)
    on_subtitle_downloaded = create_subtitle_callback(
        output_dir=output,
        verbose=False,
        console=None
    )

    downloader = Downloader(output_dir=output, on_subtitle_downloaded=on_subtitle_downloaded)

    with console.status("[bold green]Connecting to YouTube..."):
        try:
            info = downloader.get_channel_info(url)
        except Exception as e:
            console.print(f"[red]Error:[/] Could not fetch info: {e}")
            raise typer.Exit(1)

    console.print(f"  Channel: {info['channel']}")
    console.print(f"  Videos: {info['video_count']}")

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  BarColumn(), TaskProgressColumn(), console=console) as progress:
        task = progress.add_task("Downloading...", total=None)
        stats = downloader.download(url, langs=langs)

    console.print("\n[green]Download complete![/]")

    # Run consolidate
    manifest = consolidate_all(output, transcripts_per_volume=per_volume)

    console.print("\n[green]Consolidation complete![/]")
    for channel, data in manifest.get('channels', {}).items():
        console.print(f"  {channel}: {data['total_transcripciones']} -> {len(data['volumenes'])} volumes")

    console.print("\n[bold green]Pipeline complete![/]")


@app.command()
def status(
    directory: Path = typer.Argument(".", help="Directory to check"),
):
    """Show status of current directory."""
    directory = Path(directory).resolve()

    vtt_count = len(list(directory.rglob("*.vtt")))
    biblioteca = directory / "_biblioteca"
    md_count = len(list(biblioteca.rglob("*.md"))) if biblioteca.exists() else 0
    exports = directory / "_exports"
    vol_count = len(list(exports.glob("*.txt"))) if exports.exists() else 0

    console.print(Panel.fit(
        f"[bold blue]ytrag[/] Status\n\n"
        f"Directory: {directory}\n\n"
        f"VTT files: {vtt_count}\n"
        f"Cleaned (markdown): {md_count}\n"
        f"Volumes: {vol_count}",
        title="Status",
    ))


if __name__ == "__main__":
    app()
