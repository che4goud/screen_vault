"""
backfill_embeddings.py — One-time script to generate embeddings for existing screenshots.

Run this after migrating to the Gemini embedding pipeline if you have screenshots
that were processed before the migration (they will have embedding = NULL).

Usage:
    cd screenvault/backend && python backfill_embeddings.py
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from database import db
from pipeline import generate_embedding


def backfill():
    with db() as conn:
        rows = conn.execute(
            """
            SELECT id, ocr_text, description
            FROM screenshots
            WHERE embedding IS NULL AND status = 'done'
            """
        ).fetchall()

    total = len(rows)
    if total == 0:
        print("[backfill] All screenshots already have embeddings.")
        return

    print(f"[backfill] {total} screenshots need embeddings...")

    ok, skipped = 0, 0
    for row in rows:
        embedding = generate_embedding(row["ocr_text"] or "", row["description"] or "")
        if embedding is None:
            print(f"[backfill] id={row['id']}: failed, skipping")
            skipped += 1
            continue

        with db() as conn:
            conn.execute(
                "UPDATE screenshots SET embedding = ? WHERE id = ?",
                (json.dumps(embedding), row["id"]),
            )
        print(f"[backfill] id={row['id']}: ok")
        ok += 1

    print(f"[backfill] Done — {ok} embedded, {skipped} skipped")


if __name__ == "__main__":
    backfill()
