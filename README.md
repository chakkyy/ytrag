# ytrag

YouTube transcripts → RAG-ready volumes.

Download YouTube subtitles, clean them to markdown, and consolidate them into LLM-ready volumes.

## Quick Start

```bash
# Install from PyPI
pipx install ytrag

# Download and process a YouTube channel
ytrag all "https://youtube.com/@ChannelName"
```

That's it! The transcripts will be cleaned and organized into volumes ready for use with LLMs.

## Installation

### With pipx (recommended)

```bash
pipx install ytrag
```

### With pip

```bash
pip install ytrag
```

### From Source

```bash
git clone https://github.com/chakkyy/ytrag.git
cd ytrag
pip install .
```

## Usage

### Full Pipeline (recommended)

Process an entire YouTube channel in one command:

```bash
ytrag all "https://youtube.com/@ChannelName"
```

This will:

1. Download all available subtitles
2. Clean VTT files to readable markdown
3. Consolidate into LLM-ready volumes

### Individual Commands

Run each step separately if needed:

```bash
# Download subtitles only
ytrag download "https://youtube.com/@ChannelName"

# Clean VTT files to markdown
ytrag clean

# Consolidate to volumes
ytrag consolidate
```

### Command Options

```bash
# Specify languages (default: es,en)
ytrag all "https://..." --lang es,en,pt

# Custom output directory
ytrag all "https://..." --output ./my-transcripts

# Adjust transcripts per volume (default: 100)
ytrag all "https://..." --per-volume 50

# Check status of current directory
ytrag status

# Show version
ytrag --version

# Show all commands and options
ytrag --help
```

### Programmatic Usage

You can also use ytrag as a Python library:

```python
from pathlib import Path
from ytrag.downloader import Downloader
from ytrag.utils import create_subtitle_callback

# Setup output directory
output_dir = Path("./transcripts")

# Create callback to clean subtitles as they download
callback = create_subtitle_callback(output_dir, verbose=True)

# Initialize downloader
downloader = Downloader(output_dir, on_subtitle_downloaded=callback)

# Download subtitles
stats = downloader.download("https://youtube.com/@ChannelName", langs=["en", "es"])
print(f"Downloaded: {stats['downloaded']}, Errors: {stats['errors']}")
```

For consolidation:

```python
from ytrag.consolidator import consolidate_all

# Consolidate cleaned transcripts into volumes
manifest = consolidate_all(
    base_dir=".",  # Directory containing _biblioteca/
    transcripts_per_volume=100
)
print(f"Processed channels: {list(manifest['channels'].keys())}")
```

## Output Structure

After running `ytrag all`, your directory will look like:

```
./
├── ChannelName/                    # Raw VTT files
│   ├── 20230101_Video Title.en.vtt
│   └── ...
├── _biblioteca/                    # Cleaned markdown
│   └── ChannelName/
│       └── 20230101_Video Title [EN].md
├── _exports/                       # LLM-ready volumes
│   ├── ChannelName_Vol01.txt
│   ├── ChannelName_Vol02.txt
│   └── manifest.json
└── .ytrag_archive.txt              # Resume tracking
```

### What Each Folder Contains

| Folder | Purpose |
|--------|---------|
| `ChannelName/` | Raw subtitle files (VTT format) |
| `_biblioteca/` | Individual cleaned transcripts (Markdown) |
| `_exports/` | Consolidated volumes ready for LLMs |

## Examples

### Process a Single Video

```bash
ytrag all "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### Process a Playlist

```bash
ytrag all "https://www.youtube.com/playlist?list=PLxxxxxxx"
```

### Process a Channel

```bash
ytrag all "https://youtube.com/@ChannelName"
```

### Spanish-Only Transcripts

```bash
ytrag all "https://youtube.com/@ChannelName" --lang es
```

## Features

- **Stream processing**: Files are cleaned as they download
- **Adaptive rate limiting**: Automatically handles YouTube rate limits
- **Resume support**: Re-run to continue where you left off
- **Smart deduplication**: Skips regional variants (en-US if en exists)
- **Subtitle priority**: Prefers manual > auto-original > skips translated

## Requirements

- Python 3.10+

## Troubleshooting

### "No subtitles found"

Some videos don't have subtitles enabled. Try:

- Using `--lang` with different language codes
- Using auto-generated subtitles (these are downloaded by default)

### Rate limiting errors

YouTube may rate-limit downloads. ytrag handles this automatically with exponential backoff, but for large channels you may need to wait or run again later.

## License

MIT
