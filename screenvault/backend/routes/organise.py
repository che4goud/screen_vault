"""
routes/organise.py — GET /organise

Clusters the user's screenshot library by semantic similarity using
k-means over the stored embeddings, then names each cluster with Gemini.

Number of clusters: max(2, min(8, n_screenshots // 5))
Clustering: pure-numpy k-means (no sklearn dependency)
Naming: Gemini 2.5 Flash given the top descriptions per cluster
"""

import os
import numpy as np
from google import genai
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from routes.ingest import _get_user_id
from routes.search import _get_cached_screenshots

router = APIRouter()

SUMMARY_MODEL = "gemini-2.5-flash"


# ── K-means ────────────────────────────────────────────────────────────────────

def _kmeans(vecs: np.ndarray, k: int, iterations: int = 25) -> np.ndarray:
    """Simple numpy k-means. Returns integer label array of length len(vecs)."""
    rng = np.random.default_rng(seed=42)
    centroids = vecs[rng.choice(len(vecs), k, replace=False)]

    labels = np.zeros(len(vecs), dtype=int)
    for _ in range(iterations):
        # Assign: squared euclidean distance to each centroid
        diffs = vecs[:, None, :] - centroids[None, :, :]      # (n, k, d)
        dists = (diffs ** 2).sum(axis=2)                       # (n, k)
        new_labels = dists.argmin(axis=1)

        # Update centroids
        new_centroids = np.array([
            vecs[new_labels == i].mean(axis=0) if (new_labels == i).any() else centroids[i]
            for i in range(k)
        ])

        if np.array_equal(new_labels, labels) and np.allclose(centroids, new_centroids):
            break
        labels, centroids = new_labels, new_centroids

    return labels


# ── Cluster naming ─────────────────────────────────────────────────────────────

def _name_cluster(descriptions: list[str]) -> str:
    """Ask Gemini for a 2-4 word title that captures the theme of these descriptions."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or not descriptions:
        return "Untitled"

    snippets = "\n".join(f"- {d[:120]}" for d in descriptions[:6])
    prompt = (
        f"These screenshots share a common theme:\n{snippets}\n\n"
        "Give a 2-4 word title that captures what they have in common. "
        "Be specific and descriptive. Reply with only the title, no punctuation."
    )
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=SUMMARY_MODEL, contents=prompt)
        return response.text.strip()
    except Exception:
        return "Untitled"


# ── Route ──────────────────────────────────────────────────────────────────────

@router.get("/organise")
def organise(user_id: str = Depends(_get_user_id)):
    """
    Cluster the user's screenshots by embedding similarity.
    Returns a list of named clusters, each with its screenshots.
    """
    screenshots = _get_cached_screenshots(user_id)

    if not screenshots:
        return JSONResponse(content={"clusters": []})

    vecs = np.array([s["vec"] for s in screenshots], dtype=np.float32)
    n = len(screenshots)
    k = max(2, min(8, n // 5))

    # Edge case: fewer items than clusters
    if n < k:
        k = n

    labels = _kmeans(vecs, k)

    # Build clusters
    clusters = []
    for cluster_id in range(k):
        indices = [i for i, lbl in enumerate(labels) if lbl == cluster_id]
        if not indices:
            continue

        members = [screenshots[i] for i in indices]
        descriptions = [m["description"] for m in members if m.get("description")]
        name = _name_cluster(descriptions)

        clusters.append({
            "name": name,
            "screenshots": [
                {
                    "id": m["id"],
                    "filename": m["filename"],
                    "filepath": m["filepath"],
                    "thumbnail": m["thumbnail"],
                    "captured_at": m["captured_at"],
                    "description": m["description"],
                    "tags": m["tags"],
                }
                for m in members
            ],
        })

    # Sort clusters largest-first
    clusters.sort(key=lambda c: len(c["screenshots"]), reverse=True)

    return JSONResponse(content={"clusters": clusters})
