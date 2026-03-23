"""
routes/ingest.py — POST /ingest endpoint.

Receives a screenshot file upload from the Mac agent,
validates it, and enqueues it for async processing.
"""

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, Header, HTTPException, Depends
from fastapi.responses import JSONResponse

from worker import get_queue, Job
from database import db

router = APIRouter()

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def _get_user_id(x_user_id: str = Header(...)) -> str:
    """
    Minimal auth for Phase 1 — expects X-User-Id header.
    Phase 3 will replace this with proper JWT validation.
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")

    with db() as conn:
        user = conn.execute(
            "SELECT id FROM users WHERE id = ?", (x_user_id,)
        ).fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="Unknown user")

    return x_user_id


@router.post("/ingest")
async def ingest_screenshot(
    file: UploadFile = File(...),
    user_id: str = Depends(_get_user_id),
):
    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Must be PNG or JPEG."
        )

    # Read and validate file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {MAX_FILE_SIZE_MB}MB limit"
        )

    # Save to a temp file — the worker will copy it to the vault
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    try:
        tmp.write(contents)
        tmp.flush()
        tmp_path = tmp.name
    finally:
        tmp.close()

    # Enqueue for async processing
    queue = get_queue()
    job = Job(user_id=user_id, src_path=tmp_path)
    await queue.enqueue(job)

    return JSONResponse(
        status_code=202,
        content={
            "status": "queued",
            "filename": file.filename,
            "queue_size": queue.stats["queued"],
            "message": "Screenshot received and queued for processing",
        },
    )


@router.get("/ingest/status")
async def queue_status(user_id: str = Depends(_get_user_id)):
    """Returns current queue stats — useful for the Mac agent status bar."""
    queue = get_queue()
    return queue.stats
