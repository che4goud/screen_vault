"""
routes/search.py — GET /search endpoint.

Queries the FTS5 index and returns ranked, paginated results.
"""

from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import JSONResponse

from database import db
from routes.ingest import _get_user_id

router = APIRouter()


@router.get("/screenshots")
def get_all_screenshots(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user_id: str = Depends(_get_user_id),
):
    """Return all screenshots for the user, newest first. Used for the front page grid."""
    offset = (page - 1) * per_page

    with db() as conn:
        rows = conn.execute(
            """
            SELECT id, filename, filepath, thumbnail, captured_at, description, tags
            FROM screenshots
            WHERE user_id = ?
              AND status = 'done'
            ORDER BY captured_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, per_page, offset),
        ).fetchall()

        total = conn.execute(
            "SELECT COUNT(*) FROM screenshots WHERE user_id = ? AND status = 'done'",
            (user_id,),
        ).fetchone()[0]

    return JSONResponse(content={
        "query": "",
        "total": total,
        "page": page,
        "per_page": per_page,
        "results": [dict(row) for row in rows],
    })


@router.get("/search")
def search_screenshots(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user_id: str = Depends(_get_user_id),
):
    offset = (page - 1) * per_page

    with db() as conn:
        # BM25 ranking — lower score = more relevant in SQLite FTS5
        rows = conn.execute(
            """
            SELECT
                s.id,
                s.filename,
                s.thumbnail,
                s.captured_at,
                s.description,
                s.tags,
                snippet(screenshots_fts, 0, '<b>', '</b>', '...', 20) AS snippet,
                bm25(screenshots_fts) AS rank
            FROM screenshots_fts
            JOIN screenshots s ON s.id = screenshots_fts.rowid
            WHERE screenshots_fts MATCH ?
              AND s.user_id = ?
            ORDER BY rank
            LIMIT ? OFFSET ?
            """,
            (q, user_id, per_page, offset),
        ).fetchall()

        total = conn.execute(
            """
            SELECT COUNT(*) FROM screenshots_fts
            JOIN screenshots s ON s.id = screenshots_fts.rowid
            WHERE screenshots_fts MATCH ?
              AND s.user_id = ?
            """,
            (q, user_id),
        ).fetchone()[0]

    results = [dict(row) for row in rows]
    return JSONResponse(content={
        "query": q,
        "total": total,
        "page": page,
        "per_page": per_page,
        "results": results,
    })
