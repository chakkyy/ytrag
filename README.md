# ytrag

YouTube transcripts → RAG-ready volumes.

Download YouTube subtitles and consolidate them into LLM-ready volumes.

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

```bash
# Process a YouTube channel
ytrag all "https://youtube.com/@ChannelName"

# Process a single video
ytrag all "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Process a playlist
ytrag all "https://www.youtube.com/playlist?list=PLxxxxxxx"
```

### Options

```bash
# Specify languages (default: auto-detect from video)
ytrag all "https://..." --lang es,en,pt

# Custom output directory
ytrag all "https://..." --output ./my-transcripts

# Target a source limit for NotebookLM (default: 50, Plus can use 100)
ytrag all "https://..." --target-volumes 100

# Advanced override: fixed transcripts per volume
ytrag all "https://..." --per-volume 50

# Prefer a language for download and deduplication
ytrag all "https://..." --lang es

# Rebuild outputs from an existing folder of .vtt subtitle files
ytrag rebuild "./ChannelName" "Channel Name" --target-volumes 100

# Slow down large channel downloads to avoid YouTube rate limits
ytrag all "https://..." --sleep-interval 15 --max-sleep-interval 30

# Check status of current directory
ytrag status

# Show version
ytrag --version
```

## Output Structure

After running `ytrag all`, your directory will look like:

```
./
└── ytrag-ChannelName/
    ├── raw-subtitles/             # Downloaded .vtt subtitle files
    ├── clean-transcripts/         # One cleaned .md transcript per video
    ├── rag-volumes/               # NotebookLM/RAG-ready volumes only
    │   ├── ChannelName_Vol01.txt
    │   └── ChannelName_Vol02.txt
    ├── manifest.json              # Metadata
    └── .ytrag_archive             # Resume tracking
```

Each volume contains cleaned, consolidated transcripts ready for use with LLMs and RAG systems.

`raw-subtitles/` is only created when `--keep-raw` is used. By default ytrag keeps the cleaned transcripts and RAG-ready volumes.

## Features

- **Simple**: One command does everything
- **Auto language detection**: Defaults to video's original language
- **Resume support**: Re-run to continue where you left off
- **Clear progress**: Shows current/total videos and ETA while downloading large channels
- **Accurate channel counts**: Channel root URLs automatically target the Videos tab
- **NotebookLM-friendly volumes**: Smaller default volumes and a dedicated `rag-volumes` folder
- **Citable source markers**: Repeats video/date markers throughout transcripts so NotebookLM hovers show useful context
- **Language-aware deduplication**: Honors `--lang`, otherwise prefers the majority subtitle language
- **Smart deduplication**: Skips regional variants (en-US if en exists)
- **Adaptive rate limiting**: Automatically handles YouTube rate limits
- **Clean output**: No intermediate files, just the volumes you need

## Requirements

- Python 3.10+

## Troubleshooting

### "No subtitles found"

Some videos don't have subtitles enabled. Try:

- Using `--lang` with different language codes
- Auto-generated subtitles are downloaded by default

### Rate limiting errors

YouTube may rate-limit large channel downloads. ytrag uses conservative delays by default and retries extractor failures with exponential backoff. If YouTube still rate-limits the session, failed videos are not added to `.ytrag_archive`; run the same command again later and ytrag will retry the missing videos.

Useful controls:

```bash
ytrag all "https://..." \
  --sleep-interval 15 \
  --max-sleep-interval 30 \
  --stop-after-errors 3
```

## License

MIT
