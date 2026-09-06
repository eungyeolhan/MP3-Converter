# YouTube-to-MP3

A simple Python CLI tool to download audio from a YouTube video and save it as an MP3 file.

## Prerequisites

- Python 3.9+
- `ffmpeg` installed and available in your `PATH`
  - macOS (Homebrew): `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt update && sudo apt install -y ffmpeg`
  - Windows (winget): `winget install ffmpeg`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

Run with a URL argument:

```bash
python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Or run without an argument and enter the URL interactively:

```bash
python main.py
```

Output MP3 files are saved in `downloads/` (created automatically if missing).

## Notes

- The tool validates empty/invalid YouTube URLs.
- If `ffmpeg` is missing, the tool prints a clear error message.
- Download or conversion problems are handled with friendly error output.
