"""
watcher.py — Mac agent that watches for new screenshots and uploads them.

Run with:
    python watcher.py

Watches the configured screenshots folder (default: ~/Desktop) and uploads
any new PNG/JPEG files matching the macOS screenshot naming pattern to the
ScreenVault backend for processing.
"""

import os
import re
import time
import requests
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ── Config (override via environment variables) ────────────────────────────────

WATCH_DIR = os.getenv("WATCH_DIR", os.path.expanduser("~/Desktop"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
USER_ID = os.getenv("SCREENVAULT_USER_ID", "")
UPLOAD_TIMEOUT = int(os.getenv("UPLOAD_TIMEOUT", "30"))

# macOS screenshot filename pattern: 'Screenshot 2024-03-15 at 10.30.45 AM.png'
SCREENSHOT_PATTERN = re.compile(
    r"^Screenshot \d{4}-\d{2}-\d{2} at \d+\.\d+\.\d+ (AM|PM)\.(png|jpg|jpeg)$",
    re.IGNORECASE,
)


def is_screenshot(filename: str) -> bool:
    return bool(SCREENSHOT_PATTERN.match(filename))


def upload(filepath: str):
    """Upload a screenshot file to the backend /ingest endpoint."""
    filename = Path(filepath).name
    print(f"[watcher] Uploading {filename}...")

    try:
        with open(filepath, "rb") as f:
            response = requests.post(
                f"{BACKEND_URL}/ingest",
                files={"file": (filename, f, _mime_type(filepath))},
                headers={"X-User-Id": USER_ID},
                timeout=UPLOAD_TIMEOUT,
            )
        if response.status_code == 202:
            data = response.json()
            print(f"[watcher] Queued — queue size: {data.get('queue_size', '?')}")
        else:
            print(f"[watcher] Upload failed: {response.status_code} {response.text}")
    except requests.ConnectionError:
        print(f"[watcher] Cannot reach backend at {BACKEND_URL}. Is it running?")
    except Exception as e:
        print(f"[watcher] Upload error: {e}")


def _mime_type(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    return "image/png" if ext == ".png" else "image/jpeg"


class ScreenshotHandler(FileSystemEventHandler):
    """Watchdog event handler — fires when files are created in the watch dir."""

    def on_created(self, event):
        if event.is_directory:
            return
        filepath = event.src_path
        filename = Path(filepath).name

        if not is_screenshot(filename):
            return

        # Small delay to ensure macOS has finished writing the file
        time.sleep(0.5)

        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            upload(filepath)


def start():
    if not USER_ID:
        print("[watcher] ERROR: SCREENVAULT_USER_ID is not set. Run 'screenvault login' first.")
        return

    print(f"[watcher] Watching {WATCH_DIR}")
    print(f"[watcher] Backend: {BACKEND_URL}")
    print(f"[watcher] User: {USER_ID}")
    print("[watcher] Press Ctrl+C to stop\n")

    handler = ScreenshotHandler()
    observer = Observer()
    observer.schedule(handler, WATCH_DIR, recursive=False)
    observer.start()

    try:
        while observer.is_alive():
            observer.join(timeout=1)
    except KeyboardInterrupt:
        print("\n[watcher] Stopping...")
        observer.stop()
    observer.join()
    print("[watcher] Stopped")


if __name__ == "__main__":
    start()
