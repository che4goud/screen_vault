"""
routes/search.py — GET /search (hybrid) and GET /screenshots endpoints.

Search uses a three-layer hybrid approach:
  1. Semantic:  cosine similarity over gemini-embedding-2-preview embeddings
  2. Keyword:   FTS5 BM25 over description, ocr_text, and tags
  3. Fusion:    Reciprocal Rank Fusion merges both ranked lists
  4. Summary:   Gemini 2.0 Flash generates a 1-2 sentence natural-language
                summary of the top results, shown above the grid in the UI.
"""

import json
import os

import numpy as np
from google import genai
from google.genai import types as genai_types
from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.responses import JSONResponse

from database import db
from routes.ingest import _get_user_id

router = APIRouter()

EMBED_MODEL = "models/gemini-embedding-2-preview"
SUMMARY_MODEL = "gemini-2.5-flash"
MIN_SCORE = 0.40   # minimum cosine similarity to include in semantic results
RRF_K = 60         # reciprocal rank fusion constant


# ── Embedding ──────────────────────────────────────────────────────────────────

def _embed_query(query: str) -> list[float]:
    """Embed a search query using gemini-embedding-2-preview."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY is not set")
    client = genai.Client(api_key=api_key)
    result = client.models.embed_content(
        model=EMBED_MODEL,
        contents=query,
        config=genai_types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
    )
    return result.embeddings[0].values


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length float vectors."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    return float(np.dot(va, vb) / (na * nb)) if na and nb else 0.0


# ── Search signals ─────────────────────────────────────────────────────────────

def _semantic_search(query_vec: list[float], user_id: str) -> list[tuple[float, dict]]:
    """
    Score all embedded screenshots by cosine similarity.
    Returns (score, item_dict) pairs sorted descending, filtered by MIN_SCORE.
    """
    with db() as conn:
        rows = conn.execute(
            """
            SELECT id, filename, filepath, thumbnail, captured_at,
                   description, tags, embedding
            FROM screenshots
            WHERE user_id = ? AND status = 'done' AND embedding IS NOT NULL
            """,
            (user_id,),
        ).fetchall()

    scored = []
    for row in rows:
        try:
            vec = json.loads(row["embedding"])
        except (TypeError, json.JSONDecodeError):
            continue
        s = _cosine_similarity(query_vec, vec)
        if s < MIN_SCORE:
            continue
        scored.append((s, {
            "id": row["id"],
            "filename": row["filename"],
            "filepath": row["filepath"],
            "thumbnail": row["thumbnail"],
            "captured_at": row["captured_at"],
            "description": row["description"],
            "tags": row["tags"],
            "score": round(s, 4),
        }))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def _fts_search(query: str, user_id: str, limit: int = 50) -> list[dict]:
    """
    BM25 full-text search over the screenshots_fts virtual table
    (columns: description, ocr_text, tags — kept in sync by DB triggers).
    Returns items ordered by FTS5 rank (best first).
    Degrades gracefully to [] on FTS5 parse errors (e.g. special characters).
    """
    safe_q = '"' + query.replace('"', '""') + '"'
    try:
        with db() as conn:
            fts_rows = conn.execute(
                "SELECT rowid, rank FROM screenshots_fts WHERE screenshots_fts MATCH ?",
                (safe_q,),
            ).fetchall()

        if not fts_rows:
            return []

        by_id = {r["rowid"]: r["rank"] for r in fts_rows}
        placeholders = ",".join("?" * len(by_id))

        with db() as conn:
            rows = conn.execute(
                f"""
                SELECT id, filename, filepath, thumbnail, captured_at, description, tags
                FROM screenshots
                WHERE user_id = ? AND status = 'done' AND id IN ({placeholders})
                """,
                (user_id, *by_id.keys()),
            ).fetchall()

        result = [dict(r) for r in rows]
        result.sort(key=lambda r: by_id.get(r["id"], 0))  # lower rank = better in FTS5
        return result[:limit]

    except Exception:
        return []


# ── Fusion ─────────────────────────────────────────────────────────────────────

def _rrf_merge(
    semantic: list[tuple[float, dict]],
    keyword: list[dict],
) -> list[dict]:
    """
    Reciprocal Rank Fusion: each list contributes 1/(RRF_K + rank) to a shared
    score per item. Results appearing in both lists rank higher than those in one.
    """
    rrf: dict[int, float] = {}
    items: dict[int, dict] = {}

    for rank, (_, item) in enumerate(semantic):
        rrf[item["id"]] = rrf.get(item["id"], 0.0) + 1.0 / (RRF_K + rank + 1)
        items[item["id"]] = item

    for rank, item in enumerate(keyword):
        rrf[item["id"]] = rrf.get(item["id"], 0.0) + 1.0 / (RRF_K + rank + 1)
        if item["id"] not in items:
            item.setdefault("score", None)
            items[item["id"]] = item

    return sorted(items.values(), key=lambda x: rrf.get(x["id"], 0.0), reverse=True)


# ── LLM Summary ────────────────────────────────────────────────────────────────

def _generate_summary(query: str, results: list[dict]) -> str:
    """
    Ask Gemini 2.0 Flash to produce a 1-2 sentence natural-language summary
    of the top results in context of the user's query.
    Returns "" on any failure — summary is always optional.
    """
    if not results:
        return ""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return ""

    snippets = "\n".join(
        f"{i + 1}. {r.get('description') or 'No description'}"
        for i, r in enumerate(results[:8])
    )
    prompt = (
        f'User searched for: "{query}"\n\nTop results:\n{snippets}\n\n'
        "In 1–2 sentences, summarise what was found. "
        "Be specific — mention names, topics, or visible details. "
        "Do not use the words 'screenshot', 'result', or 'image'."
    )
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=SUMMARY_MODEL,
            contents=prompt,
        )
        return response.text.strip()
    except Exception:
        return ""


# ── Routes ─────────────────────────────────────────────────────────────────────

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
    """
    Hybrid search: Reciprocal Rank Fusion of
      - semantic cosine similarity (Gemini embeddings, MIN_SCORE filtered)
      - keyword BM25 (FTS5 over description, ocr_text, tags)
    Plus an LLM-generated summary of the top results.
    """
    # 1. Embed the query for semantic search
    try:
        query_vec = _embed_query(q)
    except EnvironmentError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Embedding service unavailable: {e.__class__.__name__}",
        )

    # 2. Run both search signals
    semantic = _semantic_search(query_vec, user_id)
    keyword = _fts_search(q, user_id)

    # 3. Fuse via Reciprocal Rank Fusion
    merged = _rrf_merge(semantic, keyword)

    if not merged:
        return JSONResponse(content={
            "query": q,
            "total": 0,
            "page": page,
            "per_page": per_page,
            "results": [],
            "summary": "",
        })

    # 4. LLM summary of top results
    summary = _generate_summary(q, merged[:8])

    # 5. Paginate
    offset = (page - 1) * per_page
    return JSONResponse(content={
        "query": q,
        "total": len(merged),
        "page": page,
        "per_page": per_page,
        "results": merged[offset: offset + per_page],
        "summary": summary,
    })
