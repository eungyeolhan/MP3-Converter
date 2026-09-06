"""
YouTube / TikTok / Instagram -> MP3 converter (GUI).

yt-dlp natively supports TikTok and Instagram URLs (public posts/reels),
so no extra dependency is needed beyond what YouTube already required.

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
from tkinter import messagebox

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

# ---------------------------------------------------------------------------
# Night sky / dark-mode color palette
# ---------------------------------------------------------------------------
BG_DEEP = "#0b0b1f"        # deep midnight indigo, main background
BG_PANEL = "#12123a"       # slightly lighter panel background
STAR_COLOR = "#1c1c4a"     # background glyphs - subtle, close to BG_DEEP
ACCENT = "#c9b8ff"         # soft moonlight lavender accent
ACCENT_DARK = "#a68fe0"    # pressed/darker accent
TEXT_MAIN = "#f2f0ff"      # near-white with a cool tint
TEXT_MUTED = "#8b87b3"     # muted periwinkle-gray for secondary text
ENTRY_BG = "#181840"       # input field background
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

    if COOKIES_FROM_BROWSER:
        ydl_opts["cookiesfrombrowser"] = (COOKIES_FROM_BROWSER,)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title") or "audio"
            filename = ydl.prepare_filename(info)
            mp3_path = Path(filename).with_suffix(".mp3")
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

    if not mp3_path.exists():
        mp3s = sorted(output_dir.glob("*.mp3"), key=lambda p: p.stat().st_mtime)
        if not mp3s:
            raise FileNotFoundError(f"MP3 was not created for: {title}")
        mp3_path = mp3s[-1]

    return mp3_path


class App(tk.Tk):
    WIDTH = 560
    HEIGHT = 320

    def __init__(self) -> None:
        super().__init__()
        self.title("Video -> MP3")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.resizable(False, False)
        self.configure(bg=BG_DEEP)

        # ---- background canvas with giant faint star/moon glyphs --------
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

        # ---- foreground content, placed on top of the canvas ------------
        pad = {"padx": 24, "pady": 6}

        title_lbl = tk.Label(
            self,
            text="Video \u2192 MP3",
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
        self.bg_canvas.create_window(24, 142, anchor="nw", window=self.convert_btn, height=38, width=160)

        self.status_var = tk.StringVar(value=f"Files save to: {OUTPUT_DIR}")
        status_lbl = tk.Label(
            self,
            textvariable=self.status_var,
            font=("Helvetica", 10),
            fg=TEXT_MUTED,
            bg=BG_DEEP,
            wraplength=self.WIDTH - 48,
            justify="left",
        )
        self.bg_canvas.create_window(24, 200, anchor="nw", window=status_lbl)

        self._busy = False

    # ------------------------------------------------------------------
    def _draw_background_stars(self) -> None:
        """Scatter large, low-contrast star/moon glyphs behind the UI."""
        placements = [
            (self.WIDTH - 70, 40, 46),
            (60, 260, 60),
            (self.WIDTH - 110, 230, 70),
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
        # keep decorative glyphs behind everything drawn afterwards
        self.bg_canvas.tag_lower("all")

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.convert_btn.configure(state="disabled" if busy else "normal")

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

        self.set_busy(True)
        self.status_var.set("Downloading and converting...")
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