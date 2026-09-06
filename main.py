from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download audio from a YouTube URL and save it as MP3."
    )
    parser.add_argument("url", nargs="?", help="YouTube video URL")
    return parser.parse_args()


def get_url_from_user(args: argparse.Namespace) -> str:
    url = (args.url or "").strip()
    if not url:
        url = input("Enter YouTube URL: ").strip()
    if not url:
        raise ValueError("URL cannot be empty.")
    if "youtube.com" not in url and "youtu.be" not in url:
        raise ValueError("Please provide a valid YouTube URL.")
    return url


def ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise EnvironmentError(
            "ffmpeg is not installed or not in PATH. "
            "Please install ffmpeg before running this tool."
        )


def download_mp3(url: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def main() -> int:
    try:
        args = parse_args()
        url = get_url_from_user(args)
        ensure_ffmpeg_available()

        output_dir = Path(__file__).resolve().parent / "downloads"
        download_mp3(url, output_dir)
        print(f"Done! MP3 saved in: {output_dir}")
        return 0
    except ValueError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
    except EnvironmentError as exc:
        print(f"Environment error: {exc}", file=sys.stderr)
    except DownloadError as exc:
        print(f"Download/conversion failed: {exc}", file=sys.stderr)
    except Exception as exc:  # pragma: no cover - fallback for unexpected errors
        print(f"Unexpected error: {exc}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
