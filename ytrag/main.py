# ytrag/main.py
"""ytrag CLI - YouTube transcripts to RAG-ready volumes."""

import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn, TimeRemainingColumn
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


def _first_positive_int(*values) -> Optional[int]:
    """Return the first value that can be treated as a positive integer."""
    for value in values:
        if value is None:
            continue
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number > 0:
            return number
    return None


def extract_download_progress(data: dict, fallback_total: Optional[int] = None) -> tuple[Optional[int], Optional[int]]:
    """Extract current playlist position and total from a yt-dlp progress hook."""
    info_dict = data.get('info_dict') or {}
    current = _first_positive_int(
        data.get('playlist_index'),
        info_dict.get('playlist_index'),
    )
    total = _first_positive_int(
        data.get('playlist_count'),
        data.get('n_entries'),
        info_dict.get('playlist_count'),
        info_dict.get('n_entries'),
        fallback_total,
    )
    return current, total


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
    sleep_requests: float = typer.Option(0.75, "--sleep-requests", help="Seconds to sleep between YouTube extraction requests"),
    sleep_interval: float = typer.Option(10, "--sleep-interval", help="Minimum seconds to sleep before each video"),
    max_sleep_interval: float = typer.Option(20, "--max-sleep-interval", help="Maximum seconds to sleep before each video"),
    sleep_subtitles: float = typer.Option(5, "--sleep-subtitles", help="Seconds to sleep before each subtitle download"),
    stop_after_errors: int = typer.Option(3, "--stop-after-errors", help="Stop playlist after this many consecutive failures"),
    rate_limit_retries: int = typer.Option(6, "--rate-limit-retries", help="Extractor retries when YouTube rate-limits the session"),
    rate_limit_retry_sleep: float = typer.Option(300, "--rate-limit-retry-sleep", help="Base seconds for exponential rate-limit retry backoff"),
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
    progress_total = info.get('video_count') or None
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("ETA:"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading subtitles...", total=progress_total)

        def progress_hook(data: dict) -> None:
            current, total = extract_download_progress(data, fallback_total=progress_total)
            update = {}
            if total is not None:
                update['total'] = total
            if current is not None:
                update['completed'] = min(current, total) if total is not None else current
            if update:
                progress.update(task, **update)

        temp_dir, download_stats = downloader.download_to_temp(
            url,
            langs=langs,
            archive_path=archive_path,
            progress_hooks=[progress_hook],
            sleep_requests=sleep_requests,
            sleep_interval=sleep_interval,
            max_sleep_interval=max_sleep_interval,
            sleep_subtitles=sleep_subtitles,
            skip_playlist_after_errors=stop_after_errors,
            extractor_retries=rate_limit_retries,
            extractor_retry_sleep=rate_limit_retry_sleep,
        )

    try:
        if download_stats['downloaded']:
            console.print(f"  Downloaded: {download_stats['downloaded']} subtitle files")
        if download_stats['errors']:
            console.print(f"  [yellow]Download errors: {download_stats['errors']}[/]")
        if download_stats['failed_videos']:
            failed_sample = ", ".join(download_stats['failed_videos'][:5])
            console.print(f"  [yellow]Failed video IDs: {failed_sample}[/]")
        if download_stats['rate_limited']:
            console.print(
                "  [yellow]YouTube rate-limited this session. Failed videos were not added "
                "to the archive; rerun the same command later to retry them.[/]"
            )

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
