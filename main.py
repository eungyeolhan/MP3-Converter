"""
YouTube → MP3 converter (GUI).

Requires:
  pip install yt-dlp imageio-ffmpeg
"""

from __future__ import annotations

import re
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import yt_dlp

OUTPUT_DIR = Path(__file__).resolve().parent / "downloads"
YOUTUBE_RE = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$",
    re.IGNORECASE,
)


def is_youtube_url(url: str) -> bool:
    return bool(YOUTUBE_RE.match(url.strip()))


def find_ffmpeg() -> str | None:
    system = shutil.which("ffmpeg")
    if system:
        return system
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def download_as_mp3(url: str, output_dir: Path = OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg not found. Install it (brew install ffmpeg) "
            "or: pip install imageio-ffmpeg"
        )

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": ffmpeg,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title") or "audio"
        filename = ydl.prepare_filename(info)
        mp3_path = Path(filename).with_suffix(".mp3")

    if not mp3_path.exists():
        mp3s = sorted(output_dir.glob("*.mp3"), key=lambda p: p.stat().st_mtime)
        if not mp3s:
            raise FileNotFoundError(f"MP3 was not created for: {title}")
        mp3_path = mp3s[-1]

    return mp3_path


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("YouTube → MP3")
        self.geometry("520x220")
        self.resizable(False, False)
        self.configure(bg="#1e1e1e")

        pad = {"padx": 20, "pady": 8}

        tk.Label(
            self,
            text="YouTube → MP3",
            font=("Helvetica", 18, "bold"),
            fg="#f5f5f5",
            bg="#1e1e1e",
        ).pack(anchor="w", **pad)

        tk.Label(
            self,
            text="Paste a YouTube link below",
            font=("Helvetica", 11),
            fg="#aaaaaa",
            bg="#1e1e1e",
        ).pack(anchor="w", padx=20)

        self.url_var = tk.StringVar()
        entry = tk.Entry(
            self,
            textvariable=self.url_var,
            font=("Helvetica", 12),
            bg="#2d2d2d",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#444444",
            highlightcolor="#6cb6ff",
        )
        entry.pack(fill="x", padx=20, pady=12, ipady=8)
        entry.focus_set()
        entry.bind("<Return>", lambda _e: self.start_convert())

        self.convert_btn = tk.Button(
            self,
            text="Convert to MP3",
            font=("Helvetica", 12, "bold"),
            bg="#2b7cff",
            fg="#ffffff",
            activebackground="#1f63d1",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            command=self.start_convert,
        )
        self.convert_btn.pack(padx=20, pady=4, ipadx=12, ipady=6)

        self.status_var = tk.StringVar(value=f"Files save to: {OUTPUT_DIR}")
        tk.Label(
            self,
            textvariable=self.status_var,
            font=("Helvetica", 10),
            fg="#888888",
            bg="#1e1e1e",
            wraplength=480,
            justify="left",
        ).pack(anchor="w", padx=20, pady=10)

        self._busy = False

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.convert_btn.configure(state="disabled" if busy else "normal")

    def start_convert(self) -> None:
        if self._busy:
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing link", "Paste a YouTube URL first.")
            return
        if not is_youtube_url(url):
            messagebox.showerror("Invalid link", "That doesn't look like a YouTube URL.")
            return

        self.set_busy(True)
        self.status_var.set("Downloading and converting…")
        threading.Thread(target=self._convert_worker, args=(url,), daemon=True).start()

    def _convert_worker(self, url: str) -> None:
        try:
            path = download_as_mp3(url)
        except Exception as e:
            self.after(0, self._on_error, str(e))
            return
        self.after(0, self._on_success, path)

    def _on_success(self, path: Path) -> None:
        self.set_busy(False)
        self.status_var.set(f"Saved: {path.name}")
        messagebox.showinfo("Done", f"MP3 saved to:\n{path}")

    def _on_error(self, message: str) -> None:
        self.set_busy(False)
        self.status_var.set("Conversion failed.")
        messagebox.showerror("Error", message)


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
