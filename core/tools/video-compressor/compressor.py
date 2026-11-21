#!/usr/bin/env python3
"""
Video Compressor
Watches a folder (default ~/Movies/video_compressor, or VIDEO_COMPRESSOR_DIR in
config/bench.env) for .mkv/.mov/.mp4 files and compresses
them with HandBrakeCLI (VideoToolbox hardware H.265). A recording is
considered complete when the file has not been modified for 60 seconds.

Any video file in the root of the watched folder is a candidate.
After successful compression:
  - compressed output → output/ (keeps original filename as .mp4)
  - original source   → originals/ (with _orig appended to stem)

No tracking state needed — moving the original out of the root folder
is what prevents reprocessing.

Status: writes .compressor_status.json for dashboard progress tracking.
        A background thread continuously scans for new files so the queue
        updates even while a compression is running.
"""

import json
import logging
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

BENCH = Path(os.environ.get("BENCH_ROOT") or Path(__file__).resolve().parents[3])


def bench_env(key: str, default: str) -> str:
    """KEY=value from config/bench.env (env var wins); ~ expanded."""
    val = os.environ.get(key)
    if val is None:
        try:
            for line in (BENCH / "config" / "bench.env").read_text().splitlines():
                if line.strip().startswith(key + "="):
                    val = line.split("=", 1)[1].strip().strip("'\"")
        except OSError:
            pass
    return os.path.expanduser(val or default)


WATCH_DIR     = Path(bench_env("VIDEO_COMPRESSOR_DIR", "~/Movies/video_compressor"))
HANDBRAKE     = shutil.which("HandBrakeCLI") or "/opt/homebrew/bin/HandBrakeCLI"
POLL_INTERVAL = 10   # seconds between queue scans
STABLE_AFTER  = 60   # seconds since last modification = recording finished
STATUS_FILE   = WATCH_DIR / ".compressor_status.json"
DEFAULT_QUALITY = 60   # HandBrake VT quality (lower = bigger/better, 60 ≈ CRF 28)
DEFAULT_AUDIO   = "128"  # kbps
EXTENSIONS    = (".mkv", ".mov", ".mp4")   # matched case-insensitively
OUTPUT_DIR    = "output"
ORIGINALS_DIR = "originals"

LOG_FILE = BENCH / "state" / "video-compressor" / "compressor.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    # File only: launchd may redirect stdout/stderr into LOG_FILE, and a
    # StreamHandler would then write every line to it twice.
    handlers=[logging.FileHandler(LOG_FILE)],
)

# Shared state between threads
_lock = threading.Lock()
_active_proc: Optional[subprocess.Popen] = None


# ── Status file (for dashboard) ───────────────────────────────────────────

def write_status(status: dict):
    STATUS_FILE.write_text(json.dumps(status, indent=2))


def read_status() -> dict:
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text())
        except Exception:
            pass
    return {"state": "idle", "current": None, "queue": [], "recent": []}


# ── File scanning ────────────────────────────────────────────────────────

def list_video_files() -> list[Path]:
    """List all video files in the root of WATCH_DIR (no subfolders)."""
    if not WATCH_DIR.exists():
        return []
    return sorted(
        f for f in WATCH_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in EXTENSIONS
    )


def in_use(src: Path) -> bool:
    """Another program was started on this file (the blurb pipeline's cleanup runs
    ffmpeg on the original by path for up to an hour). Moving it would break that run."""
    out = subprocess.run(["ps", "-axo", "command"], capture_output=True, text=True).stdout
    return any(str(src) in line for line in out.splitlines())


def current_path(src: Path, inode: int) -> Optional[Path]:
    """Where the source is now: renamed during compression keeps the same inode."""
    if src.exists():
        return src
    return next((f for f in list_video_files() if f.stat().st_ino == inode), None)


def archive(src: Path) -> None:
    dest = derive_archive_path(src)
    shutil.move(str(src), str(dest))
    logging.info("Archived: %s → originals/%s", src.name, dest.name)


# ── Output naming ─────────────────────────────────────────────────────────

def derive_output_path(src: Path) -> Path:
    """Output keeps the original filename but always as .mp4 in output/."""
    out_dir = src.parent / OUTPUT_DIR
    out_dir.mkdir(exist_ok=True)
    out = out_dir / (src.stem + ".mp4")

    counter = 1
    while out.exists():
        out = out_dir / f"{src.stem}_{counter}.mp4"
        counter += 1

    return out


def derive_archive_path(src: Path) -> Path:
    """Original gets _orig appended to stem, keeps its extension, in originals/."""
    orig_dir = src.parent / ORIGINALS_DIR
    orig_dir.mkdir(exist_ok=True)
    dest = orig_dir / f"{src.stem}_orig{src.suffix}"

    counter = 1
    while dest.exists():
        dest = orig_dir / f"{src.stem}_orig_{counter}{src.suffix}"
        counter += 1

    return dest


# ── Queue scanner (background thread) ───────────────────────────────────

def scan_queue():
    """Scan WATCH_DIR and update the queue in the status file."""
    ready = []
    recording = []
    for src in list_video_files():
        if (time.time() - src.stat().st_mtime) > STABLE_AFTER:
            ready.append(src.name)
        else:
            recording.append(src.name)

    queue = ready + [f"{n} (recording)" for n in recording]

    status = read_status()
    status["queue"] = queue
    write_status(status)


def queue_scanner_loop():
    """Background thread that continuously scans for new files."""
    while True:
        try:
            scan_queue()
        except Exception as exc:
            logging.error("Queue scan error: %s", exc)
        time.sleep(POLL_INTERVAL)


# ── Error reporting ──────────────────────────────────────────────────────

def _report_error(status: dict, src_name: str, message: str):
    """Write an error to the status file so the dashboard can display it."""
    errors = status.setdefault("errors", [])
    errors.insert(0, {
        "src": src_name,
        "error": message,
        "time": datetime.now().isoformat(timespec="seconds"),
    })
    status["errors"] = errors[:10]
    status["state"] = "idle"
    status["current"] = None
    write_status(status)


# ── Compression with progress ────────────────────────────────────────────

def compress(src: Path, out: Path, quality: int, audio_br: str) -> bool:
    global _active_proc
    logging.info("Compressing: %s → %s (VT quality %d)", src.name, out.name, quality)

    # Update status: compressing
    status = read_status()
    status["state"] = "compressing"
    status["current"] = {
        "src": src.name,
        "out": out.name,
        "quality": quality,
        "progress": 0,
        "started": datetime.now().isoformat(timespec="seconds"),
    }
    write_status(status)

    inode = src.stat().st_ino
    # Copy source to temp dir to work around macOS privacy restrictions
    # on ~/Movies (HandBrakeCLI may lack Full Disk Access).
    tmp_dir = tempfile.mkdtemp(prefix="compressor_")
    tmp_src = Path(tmp_dir) / src.name
    # Output goes in a subdirectory to avoid collision when src is already .mp4
    tmp_out_dir = Path(tmp_dir) / "out"
    tmp_out_dir.mkdir()
    tmp_out = tmp_out_dir / out.name
    try:
        shutil.copy2(src, tmp_src)
    except OSError as exc:
        logging.error("Failed to copy %s to temp: %s", src.name, exc)
        _report_error(status, src.name, f"Copy failed: {exc}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False

    proc = subprocess.Popen(
        [
            HANDBRAKE,
            "-i", str(tmp_src),
            "-o", str(tmp_out),
            "-e", "vt_h265",
            "-q", str(quality),
            "--encoder-preset", "speed",
            "-B", audio_br,
            "-E", "aac",
            "-f", "av_mp4",
            "--multi-pass",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    # Store PID for dashboard stop button
    with _lock:
        _active_proc = proc
    status["current"]["pid"] = proc.pid
    write_status(status)

    # HandBrake prints progress like: "Encoding: task 1 of 2, 45.23 %"
    progress_re = re.compile(r"(\d+\.\d+)\s*%")
    for line in proc.stdout:
        m = progress_re.search(line)
        if m:
            progress = min(100.0, float(m.group(1)))
            status["current"]["progress"] = round(progress, 1)
            write_status(status)

    proc.wait()

    with _lock:
        _active_proc = None

    cancelled = proc.returncode != 0 and proc.returncode < 0
    if cancelled:
        logging.info("Cancelled: %s", src.name)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        status = read_status()
        status["state"] = "idle"
        status["current"] = None
        write_status(status)
        return False

    status = read_status()
    if proc.returncode == 0 and tmp_out.exists() and tmp_out.stat().st_size > 0:
        # Renamed while compressing (0079, 261113): follow the file, name the output after it
        moved = current_path(src, inode)
        if moved and moved != src:
            renamed = derive_output_path(moved)
            logging.info("Renamed during compression: %s → %s", src.name, moved.name)
            src, out = moved, renamed
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(tmp_out), str(out))
        logging.info("Done: %s → %s", src.name, out.name)
        if moved is None:
            logging.warning("Source %s is gone; nothing to archive", src.name)
        elif in_use(src):
            logging.info("%s is in use by another program; archived once it is free", src.name)
        else:
            try:
                archive(src)
            except OSError as exc:
                logging.warning("Compressed OK but failed to archive %s: %s", src.name, exc)
        recent_entry = {
            "src": src.name,
            "out": out.name,
            "finished": datetime.now().isoformat(timespec="seconds"),
        }
        status.setdefault("recent", []).insert(0, recent_entry)
        status["recent"] = status["recent"][:10]
    else:
        err_msg = f"exit {proc.returncode}, no output produced"
        logging.error("Failed on %s (%s)", src.name, err_msg)
        _report_error(status, src.name, err_msg)
        if out.exists():
            out.unlink()

    shutil.rmtree(tmp_dir, ignore_errors=True)

    status["state"] = "idle"
    status["current"] = None
    write_status(status)

    return proc.returncode == 0 and out.exists()


# ── Main processing loop ────────────────────────────────────────────────

def process_loop():
    """Main loop: pick ready files from WATCH_DIR and compress them one by one."""
    while True:
        next_src = None
        for src in list_video_files():
            if (time.time() - src.stat().st_mtime) <= STABLE_AFTER:
                continue
            done = src.parent / OUTPUT_DIR / (src.stem + ".mp4")
            if done.exists() and done.stat().st_mtime > src.stat().st_mtime:
                # Already compressed; it stayed because it was in use. Archive once free.
                if in_use(src):
                    continue
                try:
                    archive(src)
                except OSError as exc:
                    logging.warning("Failed to archive %s: %s", src.name, exc)
                continue
            next_src = src
            break

        if next_src is None:
            time.sleep(POLL_INTERVAL)
            continue

        out = derive_output_path(next_src)
        compress(next_src, out, DEFAULT_QUALITY, DEFAULT_AUDIO)


# ── Signal handler for dashboard stop ────────────────────────────────────

def handle_stop(signum, frame):
    """Forward signal to the active HandBrake process."""
    with _lock:
        proc = _active_proc
    if proc and proc.poll() is None:
        proc.terminate()


if __name__ == "__main__":
    signal.signal(signal.SIGUSR1, handle_stop)

    logging.info("Video compressor started — watching %s every %ds", WATCH_DIR, POLL_INTERVAL)
    write_status({"state": "idle", "current": None, "queue": [], "recent": []})

    # Start background queue scanner
    scanner = threading.Thread(target=queue_scanner_loop, daemon=True)
    scanner.start()

    try:
        process_loop()
    except KeyboardInterrupt:
        logging.info("Compressor stopped.")
