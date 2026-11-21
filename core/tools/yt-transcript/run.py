#!/usr/bin/env python3
"""
YouTube Transcript Fetcher
--------------------------
Fetches transcript/captions from a YouTube video and saves as plain text.
Output filename: YYMMDD-short-description.txt
Supports manual and auto-generated captions, with timestamp option.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
# Bench root: core/tools/yt-transcript/run.py -> ../../..  (env BENCH_ROOT wins).
# The venv lives in state/yt-transcript/venv (never in core/); built on first run.

BENCH = Path(os.environ.get("BENCH_ROOT") or Path(__file__).resolve().parents[3])
VENV = BENCH / "state" / "yt-transcript" / "venv"
PACKAGES = ["youtube-transcript-api", "yt-dlp[default]", "curl_cffi"]
OUTPUT_DIR = BENCH / "convos" / "yt-transcript"
LANGUAGES = ["en", "en-US", "en-GB"]
YT_DLP = VENV / "bin" / "yt-dlp"


def ensure_venv() -> None:
    """Re-run this script inside state/yt-transcript/venv, creating it if missing."""
    py = VENV / "bin" / "python"
    if Path(sys.prefix).resolve() == VENV.resolve():
        return
    if not py.exists():
        print(f"Creating {VENV} (one time)...", file=sys.stderr)
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        subprocess.run([str(py), "-m", "pip", "install", "-q", "--upgrade", "pip", *PACKAGES], check=True)
    os.execv(str(py), [str(py), str(Path(__file__).resolve()), *sys.argv[1:]])


if __name__ == "__main__":
    ensure_venv()

from youtube_transcript_api import YouTubeTranscriptApi  # noqa: E402

# ── Helpers ───────────────────────────────────────────────────────────────────

def extract_video_id(url_or_id: str) -> str:
    patterns = [
        r"(?:v=|/v/|youtu\.be/|/embed/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for pat in patterns:
        m = re.search(pat, url_or_id)
        if m:
            return m.group(1)
    return url_or_id


def slugify(text: str, max_len: int = 60) -> str:
    """Turn a title into a filename-safe slug."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    if len(text) > max_len:
        text = text[:max_len].rsplit("-", 1)[0]
    return text


def fetch_metadata(url: str) -> dict:
    """Fetch video title and upload date via yt-dlp."""
    result = subprocess.run(
        [str(YT_DLP), "--skip-download", "--print", "%(title)s|||%(upload_date)s", url],
        capture_output=True, text=True, timeout=30,
    )
    parts = result.stdout.strip().split("|||")
    title = parts[0] if len(parts) >= 1 else "untitled"
    upload_date = parts[1] if len(parts) >= 2 else "19700101"
    # upload_date is YYYYMMDD → we want YYMMDD
    yymmdd = upload_date[2:]
    return {"title": title, "upload_date": yymmdd}


def format_timestamp(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def fetch_transcript(video_id: str, timestamps: bool = False) -> str:
    ytt = YouTubeTranscriptApi()
    transcript = ytt.fetch(video_id, languages=LANGUAGES)

    lines = []
    for entry in transcript:
        if timestamps:
            ts = format_timestamp(entry.start)
            lines.append(f"[{ts}] {entry.text}")
        else:
            lines.append(entry.text)

    return "\n".join(lines)


def build_filename(metadata: dict) -> str:
    """Build YYMMDD-short-description.txt filename."""
    slug = slugify(metadata["title"])
    return f"{metadata['upload_date']}-{slug}.txt"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: run.py <youtube-url-or-id> [--timestamps] [--output FILE]")
        sys.exit(1)

    url = sys.argv[1]
    timestamps = "--timestamps" in sys.argv

    # Parse --output
    output_file = None
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]

    video_id = extract_video_id(url)
    print(f"Fetching metadata for video: {video_id}")
    metadata = fetch_metadata(url)
    print(f"Title: {metadata['title']}")

    print("Fetching transcript...")
    text = fetch_transcript(video_id, timestamps=timestamps)

    if output_file:
        out = Path(output_file)
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTPUT_DIR / build_filename(metadata)

    out.write_text(text, encoding="utf-8")
    print(f"Saved to {out} ({len(text)} chars, {text.count(chr(10))+1} lines)")


if __name__ == "__main__":
    main()
