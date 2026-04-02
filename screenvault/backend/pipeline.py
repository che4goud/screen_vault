"""
pipeline.py — Core processing pipeline for a single screenshot.

Steps:
  1. Copy original to vault storage
  2. Generate thumbnail
  3. Run OCR via Apple Vision (ocrmac)
  4. Generate description via Gemini 2.0 Flash (vision)
  5. Generate tags via Gemini 2.0 Flash
  6. Generate embedding via text-embedding-004
  7. Persist everything to SQLite
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types as genai_types
from PIL import Image

from database import db

STORAGE_DIR = os.path.expanduser(os.getenv("STORAGE_DIR", "~/.screenvault"))
ORIGINALS_DIR = os.path.join(STORAGE_DIR, "originals")
THUMBNAILS_DIR = os.path.join(STORAGE_DIR, "thumbnails")
DOCS_DIR = os.path.join(STORAGE_DIR, "documents")
THUMBNAIL_SIZE = (400, 400)
MAX_EXTRACT_CHARS = 8000

GEMINI_MODEL = "gemini-2.5-flash"
EMBED_MODEL = "models/gemini-embedding-2-preview"
MAX_EMBED_CHARS = 4000

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


def copy_to_vault(src_path: str, dest_name: str = None) -> str:
    """Copy the original screenshot into the vault and return the new path."""
    _ensure_dirs()
    filename = dest_name or Path(src_path).name
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


# ── Gemini description ─────────────────────────────────────────────────────────

def generate_description(image_path: str) -> str:
    """Send the image to Gemini 2.0 Flash and return a plain-text description."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY is not set")

    ext = Path(image_path).suffix.lower()
    mime_type = "image/png" if ext == ".png" else "image/jpeg"

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            DESCRIPTION_PROMPT,
        ],
    )
    return response.text.strip()


# ── Auto-tagging ───────────────────────────────────────────────────────────────

def generate_tags(description: str, ocr_text: str) -> list[str]:
    """
    Ask Gemini to suggest 3-5 short tags based on the description and OCR text.
    Returns a list of lowercase tag strings.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return []

    client = genai.Client(api_key=api_key)
    prompt = (
        f"Description: {description}\n\nOCR text: {ocr_text[:500]}\n\n"
        "Based on the above, suggest 3-5 concise lowercase tags "
        "(e.g. invoice, zoom-call, figma, finance, email). "
        "Return only a JSON array of strings, nothing else."
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    try:
        text = response.text.strip()
        # Strip markdown fences if present (gemini-2.5-flash wraps JSON in ```json ... ```)
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        tags = json.loads(text.strip())
        return [str(t).lower() for t in tags if isinstance(t, str)]
    except Exception:
        return []


# ── Embedding ──────────────────────────────────────────────────────────────────

def generate_embedding(ocr_text: str, description: str) -> list[float] | None:
    """
    Embed the combined OCR text and description using text-embedding-004 (768-dim).
    Returns None if the API is unavailable or the text is empty.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    combined = f"{ocr_text} {description}".strip()[:MAX_EMBED_CHARS]
    if not combined:
        return None

    try:
        client = genai.Client(api_key=api_key)
        result = client.models.embed_content(
            model=EMBED_MODEL,
            contents=combined,
            config=genai_types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
        )
        return result.embeddings[0].values
    except Exception as e:
        print(f"[pipeline] Embedding failed: {e.__class__.__name__}: {e}")
        return None


# ── Main entry point ───────────────────────────────────────────────────────────

def process_screenshot(user_id: str, src_path: str, original_filename: str = None) -> dict:
    """
    Full pipeline for one screenshot. Returns a dict with all stored fields.

    Raises on hard failures (missing file, bad API key).
    Soft failures (OCR, tags) are caught and stored as empty values.
    """
    if not os.path.exists(src_path):
        raise FileNotFoundError(f"Screenshot not found: {src_path}")

    filename = original_filename or Path(src_path).name
    print(f"[pipeline] Processing {filename}")

    # 1. Copy to vault (preserve original filename if provided)
    vault_path = copy_to_vault(src_path, dest_name=filename)
    print(f"[pipeline] Copied to {vault_path}")

    # 2. Thumbnail
    thumb_path = generate_thumbnail(vault_path)
    print(f"[pipeline] Thumbnail at {thumb_path}")

    # 3. OCR
    ocr_text = extract_text(vault_path)
    print(f"[pipeline] OCR extracted {len(ocr_text)} chars")

    # 4. Gemini description (graceful fallback if API unavailable)
    try:
        description = generate_description(vault_path)
        print(f"[pipeline] Description: {description[:80]}...")
    except Exception as e:
        print(f"[pipeline] Gemini unavailable ({e.__class__.__name__}), using OCR text as description")
        description = ocr_text[:300] if ocr_text else f"Screenshot from {filename}"

    # 5. Tags
    try:
        tags = generate_tags(description, ocr_text)
    except Exception:
        tags = []
    print(f"[pipeline] Tags: {tags}")

    # 6. Embedding
    embedding = generate_embedding(ocr_text, description)
    embedding_json = json.dumps(embedding) if embedding is not None else None
    print(f"[pipeline] Embedding: {'ok (' + str(len(embedding)) + '-dim)' if embedding else 'unavailable'}")

    # 7. Persist to database
    captured_at = _parse_mac_timestamp(filename)

    with db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO screenshots
                (user_id, filename, filepath, thumbnail, captured_at,
                 ocr_text, description, tags, embedding, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'done')
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
                embedding_json,
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


# ── Document pipeline ──────────────────────────────────────────────────────────

DOCUMENT_DESCRIPTION_PROMPT = (
    "You are given extracted text from a document. "
    "Summarise it in 2-3 sentences covering: document type, main topic, "
    "and any key facts, names, dates, or amounts present. "
    "Be specific and factual — this summary will be used for search."
)


def _ensure_docs_dir():
    os.makedirs(DOCS_DIR, exist_ok=True)


def copy_document_to_vault(src_path: str, dest_name: str = None) -> str:
    """Copy the original document into vault/documents/ and return the new path."""
    _ensure_docs_dir()
    filename = dest_name or Path(src_path).name
    dest = os.path.join(DOCS_DIR, filename)
    if os.path.exists(dest):
        stem = Path(filename).stem
        ext = Path(filename).suffix
        dest = os.path.join(DOCS_DIR, f"{stem}_{int(datetime.now().timestamp())}{ext}")
    shutil.copy2(src_path, dest)
    return dest


def generate_document_description(extracted_text: str) -> str:
    """Text-only Gemini call to summarise extracted document content."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY is not set")
    client = genai.Client(api_key=api_key)
    prompt = f"{DOCUMENT_DESCRIPTION_PROMPT}\n\nDocument text:\n{extracted_text[:MAX_EXTRACT_CHARS]}"
    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return response.text.strip()


def process_document(user_id: str, src_path: str, original_filename: str = None) -> dict:
    """
    Full pipeline for one document (PDF/DOCX/XLSX/PPTX).

    Steps:
      1. Copy to vault/documents/
      2. Extract text via document_extractor
      3. Generate description (text-only Gemini call, no vision)
      4. Generate tags (reuses existing generate_tags)
      5. Generate embedding (reuses existing generate_embedding)
      6. Persist with type='document', thumbnail=NULL
    """
    if not os.path.exists(src_path):
        raise FileNotFoundError(f"Document not found: {src_path}")

    from document_extractor import extract_document

    filename = original_filename or Path(src_path).name
    ext = Path(filename).suffix.lower()
    print(f"[pipeline] Processing document: {filename}")

    # 1. Copy to vault
    vault_path = copy_document_to_vault(src_path, dest_name=filename)
    print(f"[pipeline] Document copied to {vault_path}")

    # 2. Extract text
    extracted_text, page_count = extract_document(vault_path)
    print(f"[pipeline] Extracted {len(extracted_text)} chars, {page_count} pages/sheets")

    # 3. Description
    try:
        if extracted_text.strip():
            description = generate_document_description(extracted_text)
        else:
            description = f"{ext.upper().lstrip('.')} document: {filename}"
        print(f"[pipeline] Description: {description[:80]}...")
    except Exception as e:
        print(f"[pipeline] Description failed ({e.__class__.__name__}), using filename")
        description = f"{ext.upper().lstrip('.')} document: {filename}"

    # 4. Tags (reuse existing function)
    try:
        tags = generate_tags(description, extracted_text[:500])
    except Exception:
        tags = []
    print(f"[pipeline] Tags: {tags}")

    # 5. Embedding (reuse existing function)
    embedding = generate_embedding(extracted_text, description)
    embedding_json = json.dumps(embedding) if embedding is not None else None
    print(f"[pipeline] Embedding: {'ok (' + str(len(embedding)) + '-dim)' if embedding else 'unavailable'}")

    # 6. Persist — thumbnail NULL, type='document'
    with db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO screenshots
                (user_id, filename, filepath, thumbnail, captured_at,
                 ocr_text, description, tags, embedding, status, type, page_count)
            VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, 'done', 'document', ?)
            """,
            (
                user_id,
                filename,
                vault_path,
                datetime.now().isoformat(),
                extracted_text,
                description,
                json.dumps(tags),
                embedding_json,
                page_count,
            ),
        )
        doc_id = cursor.lastrowid

    print(f"[pipeline] Saved document id={doc_id}")
    return {
        "id": doc_id,
        "filename": filename,
        "filepath": vault_path,
        "thumbnail": None,
        "captured_at": datetime.now().isoformat(),
        "ocr_text": extracted_text,
        "description": description,
        "tags": tags,
        "type": "document",
        "page_count": page_count,
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
