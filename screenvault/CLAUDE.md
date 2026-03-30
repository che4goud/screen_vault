# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

ScreenVault is a Mac screenshot ingestion and semantic search app. It watches a folder for new screenshots, runs them through a pipeline (OCR → Gemini vision description → auto-tags → embedding), stores everything in SQLite, and serves a Next.js search UI.

## Development Commands

```bash
# Start everything (recommended) — backend + watcher in one command
cd screenvault && ./start.sh

# Backend only (with hot-reload)
cd screenvault/backend && uvicorn main:app --reload --port 8000

# Frontend — must use production build (npm run dev uses Turbopack which crashes on Apple Silicon)
cd screenvault/frontend && npm run build && npm start

# One-time setup: create dev user in DB
cd screenvault/backend && python seed_user.py

# Backfill embeddings for screenshots processed before the Gemini pipeline
cd screenvault/backend && python backfill_embeddings.py

# Inspect the database
sqlite3 ~/.screenvault/db.sqlite "SELECT id, filename, substr(description,1,60), embedding IS NOT NULL FROM screenshots ORDER BY id DESC;"
```

## Architecture

```
screenvault/
  agent/      Mac watcher — polls ~/Desktop/ScreenVault_Screenshots, POSTs new files to /ingest
  backend/    FastAPI — ingestion queue, Gemini pipeline, semantic search
  frontend/   Next.js (production build only) — search UI
```

**Ingestion flow:**
```
New file in watch folder
  → POST /ingest  (agent/watcher.py or POST /sync on page load)
  → worker.py     (async queue, max 5 concurrent)
  → pipeline.py   OCR (ocrmac/Apple Vision)
                  generate_description() → Gemini 2.0 Flash vision
                  generate_tags()        → Gemini 2.0 Flash text
                  generate_embedding()   → gemini-embedding-2-preview (3072-dim)
  → SQLite        screenshots table, embedding stored as JSON TEXT
```

**Search flow:**
```
GET /search?q=...
  → embed query with gemini-embedding-2-preview
  → load all rows WHERE embedding IS NOT NULL
  → cosine similarity (numpy, in-process)
  → filter score >= 0.40, sort descending, paginate
  → return JSON

GET /screenshots  → browse all, newest first (no embedding required)
POST /sync        → called by frontend on every page load; scans WATCH_DIR, enqueues new files
```

## Key Files

| File | Purpose |
|---|---|
| `backend/pipeline.py` | Full processing pipeline — all Gemini calls live here |
| `backend/routes/ingest.py` | POST /ingest (file upload), POST /sync (folder scan on page load) |
| `backend/routes/search.py` | GET /search (cosine similarity), GET /screenshots (browse all) |
| `backend/database.py` | Schema, `db()` context manager, migration guard for embedding column |
| `backend/worker.py` | Async job queue; `Job` dataclass carries `original_filename` |
| `backend/main.py` | FastAPI app entry — `load_dotenv()` must be first import |
| `frontend/app/page.tsx` | Main page — calls `/sync` on mount, SWR polls while processing |
| `frontend/lib/api.ts` | All backend API calls; `thumbnailUrl()` maps file paths to `/thumbnails/` URLs |

## Environment Variables

**Backend (`backend/.env`)**
```
GOOGLE_API_KEY=...
DB_PATH=~/.screenvault/db.sqlite
STORAGE_DIR=~/.screenvault
WATCH_DIR=~/Desktop/ScreenVault_Screenshots
```

All four path vars use literal `~` which must be expanded with `os.path.expanduser()` — `os.getenv()` alone will not expand them. `load_dotenv()` in `main.py` must run before any module-level constants are set in `database.py` or `pipeline.py`.

**Frontend (`frontend/.env.local`)**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USER_ID=dev-user-001
```

## Critical Gotchas

- **`npm run dev` is broken** on Apple Silicon (Turbopack crash). Always use `npm run build && npm start`. Rebuild after any frontend code change.
- **`load_dotenv()` position matters** — it must be the very first call in `main.py`, before `from database import ...` and `from routes import ...`, because those modules set `DB_PATH`/`STORAGE_DIR` as module-level constants at import time.
- **Tilde paths** — `DB_PATH`, `STORAGE_DIR`, `WATCH_DIR` from `.env` are literal strings like `"~/.screenvault"`. Always wrap with `os.path.expanduser()`.
- **FTS5 table is kept but not queried** — `screenshots_fts` and its 3 triggers still exist in the schema and fire on INSERT/UPDATE/DELETE. The `/search` route no longer queries it (uses cosine similarity instead). Don't drop it without understanding the trigger chain.
- **Embedding model** — `models/gemini-embedding-2-preview` (3072-dim). Use `task_type="SEMANTIC_SIMILARITY"` for both document and query embedding.
- **Search threshold** — `MIN_SCORE = 0.40` in `routes/search.py`. Results below this are dropped entirely.
- **Filename preservation** — `Job.original_filename` threads the real filename through the queue so `pipeline.py` can call `copy_to_vault(dest_name=filename)` instead of using the temp file's name.

## Auth (Phase 1)

All endpoints require `X-User-Id` header. The only valid value in dev is `dev-user-001` (created by `seed_user.py`). Phase 3 will replace this with JWT.

## Roadmap State

- **Done:** ingestion pipeline, Gemini vision + embeddings, cosine similarity search, auto-sync on page load, thumbnail serving
- **Next:** Phase 3 (Supabase Auth + JWT), Phase 4 (Stripe payments)
