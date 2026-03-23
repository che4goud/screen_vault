"""
pipeline.py — Core processing pipeline for a single screenshot.

Steps:
  1. Copy original to vault storage
  2. Generate thumbnail
  3. Run OCR via Apple Vision (ocrmac)
  4. Generate description via Claude API
  5. Persist everything to SQLite
"""

import os
import shutil
import json
import base64
from datetime import datetime
from pathlib import Path

import anthropic
from PIL import Image

from database import db

STORAGE_DIR = os.getenv("STORAGE_DIR", os.path.expanduser("~/.screenvault"))
ORIGINALS_DIR = os.path.join(STORAGE_DIR, "originals")
THUMBNAILS_DIR = os.path.join(STORAGE_DIR, "thumbnails")
THUMBNAIL_SIZE = (400, 400)

CLAUDE_MODEL = "claude-sonnet-4-6"
DESCRIPTION_PROMPT = (
    "Describe this screenshot concisely in 2-3 sentences. Include: "
    "what application or website is visible, what the content is about, "
    "and any key information (names, dates, amounts, topics) present. "
    "Be specific and factual — this description will be used for search."
)


# ── Storage helpers ────────────────────────────────────────────────────────────

def _ensure_dirs():
    os.makedirs(ORIGINALS_DIR, exist_ok=True)
    os.makedirs(THUMBNAILS_DIR, exist_ok=True)


def copy_to_vault(src_path: str) -> str:
    """Copy the original screenshot into the vault and return the new path."""
    _ensure_dirs()
    filename = Path(src_path).name
    dest = os.path.join(ORIGINALS_DIR, filename)
    # Avoid overwriting if a file with the same name already exists
    if os.path.exists(dest):
        stem = Path(filename).stem
        ext = Path(filename).suffix
        dest = os.path.join(ORIGINALS_DIR, f"{stem}_{int(datetime.now().timestamp())}{ext}")
    shutil.copy2(src_path, dest)
    return dest


def generate_thumbnail(image_path: str) -> str:
    """Create a resized thumbnail and return its path."""
    _ensure_dirs()
    filename = Path(image_path).stem + "_thumb.jpg"
    thumb_path = os.path.join(THUMBNAILS_DIR, filename)
    with Image.open(image_path) as img:
        img.thumbnail(THUMBNAIL_SIZE)
        img.convert("RGB").save(thumb_path, "JPEG", quality=75)
    return thumb_path


# ── OCR ────────────────────────────────────────────────────────────────────────

def extract_text(image_path: str) -> str:
    """
    Extract text using Apple Vision via ocrmac.
    Falls back to an empty string if ocrmac is unavailable (non-Mac environments).
    """
    try:
        from ocrmac import OCR
        results = OCR(image_path).recognize()
        # results is a list of (text, confidence, bounding_box) tuples
        lines = [r[0] for r in results if r[1] > 0.5]
        return "\n".join(lines)
    except ImportError:
        print("[pipeline] ocrmac not available — skipping OCR")
        return ""
    except Exception as e:
        print(f"[pipeline] OCR failed: {e}")
        return ""


# ── Claude description ─────────────────────────────────────────────────────────

def generate_description(image_path: str) -> str:
    """Send the image to Claude and return a plain-text description."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set")

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    # Detect media type from extension
    ext = Path(image_path).suffix.lower()
    media_type = "image/png" if ext == ".png" else "image/jpeg"

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": DESCRIPTION_PROMPT},
                ],
            }
        ],
    )
    return message.content[0].text.strip()


# ── Auto-tagging ───────────────────────────────────────────────────────────────

def generate_tags(description: str, ocr_text: str) -> list[str]:
    """
    Ask Claude to suggest 3-5 short tags based on the description and OCR text.
    Returns a list of lowercase tag strings.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return []

    combined = f"Description: {description}\n\nOCR text: {ocr_text[:500]}"
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=64,
        messages=[
            {
                "role": "user",
                "content": (
                    f"{combined}\n\n"
                    "Based on the above, suggest 3-5 concise lowercase tags "
                    "(e.g. invoice, zoom-call, figma, finance, email). "
                    "Return only a JSON array of strings, nothing else."
                ),
            }
        ],
    )
    try:
        tags = json.loads(message.content[0].text.strip())
        return [str(t).lower() for t in tags if isinstance(t, str)]
    except Exception:
        return []


# ── Main entry point ───────────────────────────────────────────────────────────

def process_screenshot(user_id: str, src_path: str) -> dict:
    """
    Full pipeline for one screenshot. Returns a dict with all stored fields.

    Raises on hard failures (missing file, bad API key).
    Soft failures (OCR, tags) are caught and stored as empty values.
    """
    if not os.path.exists(src_path):
        raise FileNotFoundError(f"Screenshot not found: {src_path}")

    filename = Path(src_path).name
    print(f"[pipeline] Processing {filename}")

    # 1. Copy to vault
    vault_path = copy_to_vault(src_path)
    print(f"[pipeline] Copied to {vault_path}")

    # 2. Thumbnail
    thumb_path = generate_thumbnail(vault_path)
    print(f"[pipeline] Thumbnail at {thumb_path}")

    # 3. OCR
    ocr_text = extract_text(vault_path)
    print(f"[pipeline] OCR extracted {len(ocr_text)} chars")

    # 4. Claude description
    description = generate_description(vault_path)
    print(f"[pipeline] Description: {description[:80]}...")

    # 5. Tags
    tags = generate_tags(description, ocr_text)
    print(f"[pipeline] Tags: {tags}")

    # 6. Persist to database
    captured_at = _parse_mac_timestamp(filename)

    with db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO screenshots
                (user_id, filename, filepath, thumbnail, captured_at,
                 ocr_text, description, tags, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'done')
            """,
            (
                user_id,
                filename,
                vault_path,
                thumb_path,
                captured_at,
                ocr_text,
                description,
                json.dumps(tags),
            ),
        )
        screenshot_id = cursor.lastrowid

    print(f"[pipeline] Saved screenshot id={screenshot_id}")
    return {
        "id": screenshot_id,
        "filename": filename,
        "filepath": vault_path,
        "thumbnail": thumb_path,
        "captured_at": captured_at,
        "ocr_text": ocr_text,
        "description": description,
        "tags": tags,
        "status": "done",
    }


def _parse_mac_timestamp(filename: str) -> str:
    """
    Extract the datetime from a macOS screenshot filename.
    Pattern: 'Screenshot 2024-03-15 at 10.30.45 AM.png'
    Falls back to current time if parsing fails.
    """
    try:
        # Remove prefix and extension
        stem = Path(filename).stem  # e.g. 'Screenshot 2024-03-15 at 10.30.45 AM'
        date_part = stem.replace("Screenshot ", "")  # '2024-03-15 at 10.30.45 AM'
        dt = datetime.strptime(date_part, "%Y-%m-%d at %I.%M.%S %p")
        return dt.isoformat()
    except Exception:
        return datetime.now().isoformat()
