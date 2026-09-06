"""
YouTube / TikTok / Instagram converter (GUI).

Supports MP3, WAV, FLAC, M4A, Opus, MP4, WEBM, and MKV.

Requires:
  pip install yt-dlp imageio-ffmpeg
"""

from __future__ import annotations

import random
import re
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import yt_dlp

OUTPUT_DIR = Path(__file__).resolve().parent / "downloads"

# Some Instagram (and occasionally TikTok) content requires being logged in.
# Set this to the browser you're logged into on this machine, e.g.:
#   "chrome", "firefox", "edge", "brave", "safari", "opera", "vivaldi"
# Set it to None to disable and download without cookies.
COOKIES_FROM_BROWSER: str | None = "chrome"

SUPPORTED_URL_RE = re.compile(
    r"^(https?://)?(www\.|vm\.|vt\.)?"
    r"(youtube\.com|youtu\.be|tiktok\.com|instagram\.com)/.+$",
    re.IGNORECASE,
)

# label -> (kind, extension, yt-dlp preferredcodec or None for video)
# kind is "audio" or "video"
FORMATS: dict[str, tuple[str, str, str | None]] = {
    "MP3 (audio)": ("audio", "mp3", "mp3"),
    "WAV (audio)": ("audio", "wav", "wav"),
    "FLAC (audio)": ("audio", "flac", "flac"),
    "M4A (audio)": ("audio", "m4a", "m4a"),
    "Opus (audio)": ("audio", "opus", "opus"),
    "MP4 (video)": ("video", "mp4", None),
    "WEBM (video)": ("video", "webm", None),
    "MKV (video)": ("video", "mkv", None),
}

# ---------------------------------------------------------------------------
# Night sky / dark-mode color palette
# ---------------------------------------------------------------------------
BG_DEEP = "#0b0b1f"
BG_PANEL = "#12123a"
STAR_COLOR = "#1c1c4a"
ACCENT = "#c9b8ff"
ACCENT_DARK = "#a68fe0"
TEXT_MAIN = "#f2f0ff"
TEXT_MUTED = "#8b87b3"
ENTRY_BG = "#181840"
BORDER = "#2c2c5c"

STAR_GLYPHS = ["\u2727\u02d6\u00b0.", "\u23fe\u22c6.\u02da", "\u27e1"]


def is_supported_url(url: str) -> bool:
    return bool(SUPPORTED_URL_RE.match(url.strip()))


def find_ffmpeg() -> str | None:
    system = shutil.which("ffmpeg")
    if system:
        return system
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def build_ydl_opts(format_label: str, output_dir: Path, ffmpeg: str) -> dict:
    kind, ext, codec = FORMATS[format_label]
    outtmpl = str(output_dir / "%(title)s.%(ext)s")

    if kind == "audio":
        return {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "ffmpeg_location": ffmpeg,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": codec,
                    "preferredquality": "192",
                }
            ],
        }

    # Video: prefer best merged stream, remux/convert to chosen container
    if ext == "mp4":
        fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
        merge = "mp4"
    elif ext == "webm":
        fmt = "bestvideo[ext=webm]+bestaudio[ext=webm]/bestvideo+bestaudio/best"
        merge = "webm"
    else:  # mkv
        fmt = "bestvideo+bestaudio/best"
        merge = "mkv"

    return {
        "format": fmt,
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": ffmpeg,
        "merge_output_format": merge,
    }


def download_media(url: str, format_label: str, output_dir: Path = OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg not found. Install it (brew install ffmpeg) "
            "or: pip install imageio-ffmpeg"
        )

    kind, ext, _codec = FORMATS[format_label]
    ydl_opts = build_ydl_opts(format_label, output_dir, ffmpeg)

    if COOKIES_FROM_BROWSER:
        ydl_opts["cookiesfrombrowser"] = (COOKIES_FROM_BROWSER,)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title") or "media"
            filename = ydl.prepare_filename(info)
            result_path = Path(filename).with_suffix(f".{ext}")
    except yt_dlp.utils.DownloadError as e:
        message = str(e)
        if "login" in message.lower() or "rate-limit" in message.lower():
            raise RuntimeError(
                "This content needs a login (common for Instagram). "
                f"Make sure you're logged into Instagram in {COOKIES_FROM_BROWSER or 'a browser'} "
                "on this computer, then close the browser fully and try again "
                "(browsers can lock the cookie file while running)."
            ) from e
        raise

    if not result_path.exists():
        matches = sorted(output_dir.glob(f"*.{ext}"), key=lambda p: p.stat().st_mtime)
        if not matches:
            # Video merges sometimes keep a different intermediate extension
            recent = sorted(output_dir.iterdir(), key=lambda p: p.stat().st_mtime)
            recent = [p for p in recent if p.is_file()]
            if recent:
                return recent[-1]
            raise FileNotFoundError(f"{ext.upper()} was not created for: {title}")
        result_path = matches[-1]

    return result_path


class App(tk.Tk):
    WIDTH = 560
    HEIGHT = 460

    def __init__(self) -> None:
        super().__init__()
        self.title("Video Converter")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.resizable(False, False)
        self.configure(bg=BG_DEEP)

        self.bg_canvas = tk.Canvas(
            self,
            width=self.WIDTH,
            height=self.HEIGHT,
            bg=BG_DEEP,
            highlightthickness=0,
            bd=0,
        )
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._draw_background_stars()

        title_lbl = tk.Label(
            self,
            text="Video Converter",
            font=("Helvetica", 20, "bold"),
            fg=TEXT_MAIN,
            bg=BG_DEEP,
        )
        self.bg_canvas.create_window(24, 22, anchor="nw", window=title_lbl)

        subtitle_lbl = tk.Label(
            self,
            text="Paste a YouTube, TikTok, or Instagram link below",
            font=("Helvetica", 11),
            fg=TEXT_MUTED,
            bg=BG_DEEP,
        )
        self.bg_canvas.create_window(24, 58, anchor="nw", window=subtitle_lbl)

        self.url_var = tk.StringVar()
        entry = tk.Entry(
            self,
            textvariable=self.url_var,
            font=("Helvetica", 12),
            bg=ENTRY_BG,
            fg=TEXT_MAIN,
            insertbackground=ACCENT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            width=42,
        )
        self.bg_canvas.create_window(24, 90, anchor="nw", window=entry, height=38)
        entry.focus_set()
        entry.bind("<Return>", lambda _e: self.start_convert())

        format_lbl = tk.Label(
            self,
            text="Format",
            font=("Helvetica", 11),
            fg=TEXT_MUTED,
            bg=BG_DEEP,
        )
        self.bg_canvas.create_window(24, 142, anchor="nw", window=format_lbl)

        self.format_var = tk.StringVar(value="MP3 (audio)")
        self._style_combobox()
        format_box = ttk.Combobox(
            self,
            textvariable=self.format_var,
            values=list(FORMATS.keys()),
            state="readonly",
            style="Dark.TCombobox",
            font=("Helvetica", 12),
            width=22,
        )
        self.bg_canvas.create_window(24, 168, anchor="nw", window=format_box, height=32)
        format_box.bind("<<ComboboxSelected>>", self._on_format_change)

        save_lbl = tk.Label(
            self,
            text="Save to",
            font=("Helvetica", 11),
            fg=TEXT_MUTED,
            bg=BG_DEEP,
        )
        self.bg_canvas.create_window(24, 214, anchor="nw", window=save_lbl)

        self.save_dir_var = tk.StringVar(value=str(OUTPUT_DIR))
        save_entry = tk.Entry(
            self,
            textvariable=self.save_dir_var,
            font=("Helvetica", 11),
            bg=ENTRY_BG,
            fg=TEXT_MAIN,
            insertbackground=ACCENT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            width=32,
        )
        self.bg_canvas.create_window(24, 240, anchor="nw", window=save_entry, height=34)

        browse_btn = tk.Button(
            self,
            text="Browse…",
            font=("Helvetica", 11),
            bg=ENTRY_BG,
            fg=ACCENT,
            activebackground=BORDER,
            activeforeground=TEXT_MAIN,
            relief="flat",
            cursor="hand2",
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            command=self.browse_save_dir,
        )
        self.bg_canvas.create_window(
            420, 240, anchor="nw", window=browse_btn, height=34, width=100
        )
        self.browse_btn = browse_btn

        self.convert_btn = tk.Button(
            self,
            text="Convert to MP3",
            font=("Helvetica", 12, "bold"),
            bg=ACCENT,
            fg="#06181f",
            activebackground=ACCENT_DARK,
            activeforeground="#06181f",
            relief="flat",
            cursor="hand2",
            bd=0,
            command=self.start_convert,
        )
        self.bg_canvas.create_window(
            24, 296, anchor="nw", window=self.convert_btn, height=38, width=180
        )

        self.status_var = tk.StringVar(value="Ready")
        status_lbl = tk.Label(
            self,
            textvariable=self.status_var,
            font=("Helvetica", 10),
            fg=TEXT_MUTED,
            bg=BG_DEEP,
            wraplength=self.WIDTH - 48,
            justify="left",
        )
        self.bg_canvas.create_window(24, 356, anchor="nw", window=status_lbl)

        self._busy = False

    def _style_combobox(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Dark.TCombobox",
            fieldbackground=ENTRY_BG,
            background=ENTRY_BG,
            foreground=TEXT_MAIN,
            arrowcolor=ACCENT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            insertcolor=ACCENT,
            selectbackground=ACCENT_DARK,
            selectforeground=TEXT_MAIN,
            padding=6,
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", ENTRY_BG)],
            foreground=[("readonly", TEXT_MAIN)],
            background=[("readonly", ENTRY_BG)],
        )

    def _on_format_change(self, _event=None) -> None:
        label = self.format_var.get()
        _kind, ext, _codec = FORMATS[label]
        self.convert_btn.configure(text=f"Convert to {ext.upper()}")

    def browse_save_dir(self) -> None:
        current = self.save_dir_var.get().strip() or str(OUTPUT_DIR)
        chosen = filedialog.askdirectory(
            title="Choose save folder",
            initialdir=current if Path(current).is_dir() else str(Path.home()),
        )
        if chosen:
            self.save_dir_var.set(chosen)

    def _draw_background_stars(self) -> None:
        placements = [
            (self.WIDTH - 70, 40, 46),
            (60, 380, 60),
            (self.WIDTH - 110, 350, 70),
            (self.WIDTH // 2 + 50, 130, 80),
            (10, 95, 44),
        ]
        random.seed(3005)
        for x, y, size in placements:
            glyph = random.choice(STAR_GLYPHS)
            self.bg_canvas.create_text(
                x,
                y,
                text=glyph,
                font=("Segoe UI Symbol", size),
                fill=STAR_COLOR,
                anchor="center",
            )
        self.bg_canvas.tag_lower("all")

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        self.convert_btn.configure(state=state)
        self.browse_btn.configure(state=state)

    def start_convert(self) -> None:
        if self._busy:
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing link", "Paste a video URL first.")
            return
        if not is_supported_url(url):
            messagebox.showerror(
                "Invalid link",
                "That doesn't look like a YouTube, TikTok, or Instagram URL.",
            )
            return

        format_label = self.format_var.get()
        if format_label not in FORMATS:
            messagebox.showerror("Invalid format", "Pick a format from the list.")
            return

        save_dir = Path(self.save_dir_var.get().strip() or str(OUTPUT_DIR)).expanduser()
        try:
            save_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Invalid folder", f"Can't use that save folder:\n{e}")
            return

        _kind, ext, _codec = FORMATS[format_label]
        self.set_busy(True)
        self.status_var.set(f"Downloading and converting to {ext.upper()}...")
        threading.Thread(
            target=self._convert_worker,
            args=(url, format_label, save_dir),
            daemon=True,
        ).start()

    def _convert_worker(
        self, url: str, format_label: str, output_dir: Path
    ) -> None:
        try:
            path = download_media(url, format_label, output_dir)
        except Exception as e:
            self.after(0, self._on_error, str(e))
            return
        self.after(0, self._on_success, path)

    def _on_success(self, path: Path) -> None:
        self.set_busy(False)
        self.status_var.set(f"Saved: {path.name}")
        messagebox.showinfo("Done", f"Saved to:\n{path}")

    def _on_error(self, message: str) -> None:
        self.set_busy(False)
        self.status_var.set("Conversion failed.")
        messagebox.showerror("Error", message)


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
