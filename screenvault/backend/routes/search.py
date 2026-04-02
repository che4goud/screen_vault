"""
routes/search.py — GET /search, GET /summary, GET /screenshots endpoints.

Search uses a three-layer hybrid approach:
  1. Semantic:  cosine similarity over gemini-embedding-2-preview embeddings
  2. Keyword:   FTS5 BM25 over description, ocr_text, and tags
  3. Fusion:    Reciprocal Rank Fusion merges both ranked lists

Summary is decoupled into GET /summary so search results are returned
immediately without waiting for the LLM call.

Performance caches (module-level, in-process):
  _query_cache       — maps query text → embedding vector (max 200 entries)
  _screenshot_cache  — maps user_id → pre-parsed screenshot rows with numpy vecs
                       Invalidated by invalidate_screenshot_cache() after ingestion.
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

# ── In-memory caches ───────────────────────────────────────────────────────────

_query_cache: dict[str, list[float]] = {}
_QUERY_CACHE_MAX = 200

# user_id → list of dicts with keys: id, filename, filepath, thumbnail,
#           captured_at, description, tags, vec (np.ndarray float32)
_screenshot_cache: dict[str, list[dict]] = {}


def invalidate_screenshot_cache(user_id: str) -> None:
    """Drop cached screenshot embeddings for a user. Called after ingestion completes."""
    _screenshot_cache.pop(user_id, None)


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


def _embed_query_cached(query: str) -> list[float]:
    """Embed a query, returning a cached vector if available."""
    if query in _query_cache:
        return _query_cache[query]
    vec = _embed_query(query)
    if len(_query_cache) >= _QUERY_CACHE_MAX:
        # Drop oldest entry (insertion-ordered dict since Python 3.7)
        _query_cache.pop(next(iter(_query_cache)))
    _query_cache[query] = vec
    return vec


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length float vectors."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    return float(np.dot(va, vb) / (na * nb)) if na and nb else 0.0


# ── Screenshot embedding cache ─────────────────────────────────────────────────

def _get_cached_screenshots(user_id: str) -> list[dict]:
    """
    Return pre-parsed screenshot rows for the user with numpy vecs attached.
    Loads from DB on first call; subsequent calls return the in-memory cache.
    """
    if user_id in _screenshot_cache:
        return _screenshot_cache[user_id]

    with db() as conn:
        rows = conn.execute(
            """
            SELECT id, filename, filepath, thumbnail, captured_at,
                   description, tags, embedding, type, page_count
            FROM screenshots
            WHERE user_id = ? AND status = 'done' AND embedding IS NOT NULL
            """,
            (user_id,),
        ).fetchall()

    parsed = []
    for row in rows:
        try:
            vec = np.array(json.loads(row["embedding"]), dtype=np.float32)
        except (TypeError, json.JSONDecodeError):
            continue
        parsed.append({
            "id": row["id"],
            "filename": row["filename"],
            "filepath": row["filepath"],
            "thumbnail": row["thumbnail"],
            "captured_at": row["captured_at"],
            "description": row["description"],
            "tags": row["tags"],
            "type": row["type"] if "type" in row.keys() else "screenshot",
            "page_count": row["page_count"] if "page_count" in row.keys() else None,
            "vec": vec,
        })

    _screenshot_cache[user_id] = parsed
    return parsed


# ── Search signals ─────────────────────────────────────────────────────────────

def _semantic_search(query_vec: list[float], user_id: str) -> list[tuple[float, dict]]:
    """
    Score all embedded screenshots by cosine similarity using the in-memory cache.
    Returns (score, item_dict) pairs sorted descending, filtered by MIN_SCORE.
    """
    screenshots = _get_cached_screenshots(user_id)
    qv = np.array(query_vec, dtype=np.float32)
    qn = np.linalg.norm(qv)

    scored = []
    for item in screenshots:
        vb = item["vec"]
        nb = np.linalg.norm(vb)
        s = float(np.dot(qv, vb) / (qn * nb)) if qn and nb else 0.0
        if s < MIN_SCORE:
            continue
        scored.append((s, {
            "id": item["id"],
            "filename": item["filename"],
            "filepath": item["filepath"],
            "thumbnail": item["thumbnail"],
            "captured_at": item["captured_at"],
            "description": item["description"],
            "tags": item["tags"],
            "type": item.get("type", "screenshot"),
            "page_count": item.get("page_count"),
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
    Ask Gemini Flash to produce a 1-2 sentence natural-language summary
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
            SELECT id, filename, filepath, thumbnail, captured_at, description, tags,
                   type, page_count
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
    Hybrid search: Reciprocal Rank Fusion of semantic + keyword results.
    Returns results immediately — summary is fetched separately via GET /summary.
    """
    # 1. Embed the query (cached)
    try:
        query_vec = _embed_query_cached(q)
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
        })

    # 4. Paginate and return — no summary here
    offset = (page - 1) * per_page
    return JSONResponse(content={
        "query": q,
        "total": len(merged),
        "page": page,
        "per_page": per_page,
        "results": merged[offset: offset + per_page],
    })


@router.get("/summary")
def get_summary(
    q: str = Query(..., min_length=1, description="Search query to summarise"),
    user_id: str = Depends(_get_user_id),
):
    """
    Generate an LLM summary of top search results for query q.
    Called by the frontend in parallel with GET /search so results
    are never blocked by the summary generation time.
    """
    try:
        query_vec = _embed_query_cached(q)
    except Exception:
        return JSONResponse(content={"summary": ""})

    semantic = _semantic_search(query_vec, user_id)
    keyword = _fts_search(q, user_id)
    merged = _rrf_merge(semantic, keyword)

    summary = _generate_summary(q, merged[:8])
    return JSONResponse(content={"summary": summary})
