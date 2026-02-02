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

# Adjust transcripts per volume (default: 100)
ytrag all "https://..." --per-volume 50

# Check status of current directory
ytrag status

# Show version
ytrag --version
```

## Output Structure

After running `ytrag all`, your directory will look like:

```
./
└── ChannelName/
    ├── ChannelName_Vol01.txt      # LLM-ready volume
    ├── ChannelName_Vol02.txt
    ├── manifest.json              # Metadata
    └── .ytrag_archive             # Resume tracking
```

Each volume contains cleaned, consolidated transcripts ready for use with LLMs and RAG systems.

## Features

- **Simple**: One command does everything
- **Auto language detection**: Defaults to video's original language
- **Resume support**: Re-run to continue where you left off
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

YouTube may rate-limit downloads. ytrag handles this automatically with exponential backoff, but for large channels you may need to wait or run again later.

## License

MIT
