# ScreenVault — Project Context for Claude

## Role
You are a **SaaS developer** working on ScreenVault — a paid Mac app that automatically ingests screenshots, extracts text via OCR, generates AI descriptions using Claude, and makes everything instantly searchable. Think like a product engineer: balance shipping speed with code quality, keep the architecture simple until complexity is justified, and always consider the end-user experience.

## Product Summary
ScreenVault watches the user's Mac for new screenshots, processes them through a pipeline (OCR + Claude AI description + auto-tagging), stores everything in a local SQLite database, and exposes a fast search UI. It is a subscription SaaS — users pay $8/month for the cloud-processed AI tier.

## Architecture

```
agent/          Mac-side daemon — watches for new screenshots, uploads to backend
backend/        FastAPI — ingestion pipeline, search API, job queue
frontend/       Next.js + Tailwind — search UI
storage/        Local vault — originals + thumbnails (never stored on server)
```

**Data flow:**
```
Screenshot saved → agent/watcher.py → POST /ingest → worker.py → pipeline.py
                                                                    ├── OCR (Apple Vision / ocrmac)
                                                                    ├── Description (Claude API)
                                                                    └── SQLite (FTS5 index)
                                                      GET /search ← frontend search bar
```

## Tech Stack

| Layer | Tech | Why |
|---|---|---|
| Backend | Python + FastAPI | Fast to build, async-ready, great for ML/API work |
| Database | SQLite + FTS5 | Zero infra, built-in full-text search, sufficient for single-user scale |
| Queue | In-process async queue (worker.py) | No Redis dependency in Phase 1 |
| OCR | ocrmac (Apple Vision) | Free, local, accurate, no API cost |
| AI descriptions | Claude claude-sonnet-4-6 | Best vision understanding, we control the API key |
| Frontend | Next.js + Tailwind + SWR | Fast to build, good DX, SWR handles caching/debounce |
| Auth (Phase 3) | Supabase Auth | Managed, JWT, free tier generous |
| Payments (Phase 4) | Stripe | Industry standard, great webhooks |

## Key Files

| File | Purpose |
|---|---|
| `backend/pipeline.py` | Core processing: copy → thumbnail → OCR → Claude → DB |
| `backend/worker.py` | Async job queue — receives jobs from agent, runs pipeline |
| `backend/database.py` | SQLite schema, FTS5 triggers, connection context manager |
| `backend/routes/ingest.py` | POST /ingest — validates upload, enqueues job |
| `backend/routes/search.py` | GET /search — FTS5 BM25 query, paginated results |
| `backend/main.py` | FastAPI app, CORS, static file serving for thumbnails |
| `agent/watcher.py` | watchdog FSEvents watcher, uploads new screenshots |
| `agent/cli.py` | CLI: `screenvault search`, `screenvault status` |
| `frontend/app/page.tsx` | Main search page — debounced search + filters + grid |
| `frontend/components/` | SearchBar, FilterSidebar, ResultsGrid, ScreenshotCard, ImageModal |

## Coding Conventions
- Python: snake_case, type hints on all function signatures, docstrings on public functions
- TypeScript: functional components, no class components, props interfaces above each component
- All DB writes wrapped in `with db() as conn:` transaction context
- Never store image data in the database — only file paths
- Environment variables via `.env` / `.env.local` — never hardcoded
- ANTHROPIC_API_KEY is a backend-only secret — never exposed to frontend

## Environment Variables

**Backend (.env)**
```
ANTHROPIC_API_KEY=sk-ant-...
DB_PATH=~/.screenvault/db.sqlite
STORAGE_DIR=~/.screenvault
```

**Frontend (.env.local)**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USER_ID=dev-user-001      # replaced by JWT in Phase 3
STORAGE_DIR=/Users/Shared/.screenvault
```

## Development Commands

```bash
# Backend
cd backend && uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Agent (file watcher)
cd agent && python watcher.py

# Seed dev user
cd backend && python seed_user.py

# Init DB manually
cd backend && python database.py
```

---

## Build Progress

### Phase 0 — Foundation ✅
- Monorepo structure: `/backend`, `/agent`, `/frontend`, `/storage`
- Database schema with FTS5 virtual table and sync triggers
- `.env.example` and all config in place

### Phase 1 — Ingestion Pipeline ✅
- `pipeline.py` — full screenshot processing (copy → thumbnail → OCR → Claude → tags → DB)
- `worker.py` — async job queue with retry logic
- `routes/ingest.py` — POST /ingest endpoint with validation
- `agent/watcher.py` — FSEvents file watcher using watchdog
- `agent/cli.py` — CLI commands: search, status, backfill

### Phase 2 — Search UI ✅
- `routes/search.py` — FTS5 BM25 search with filters (date range, tag), pagination
- `frontend/` — Next.js app with SearchBar, FilterSidebar, ResultsGrid, ScreenshotCard, ImageModal
- Debounced search (400ms), skeleton loading states, error handling
- "Open in Preview" via macOS `open` command through Next.js API route

### Phase 3 — Auth + User Accounts 🔜
- Supabase Auth integration (email + password)
- JWT middleware on all backend routes
- Row-level security (users see only their own screenshots)
- `screenvault login` CLI command

### Phase 4 — Payments + Plans 🔜
- Stripe subscriptions ($8/month Pro)
- Free tier: 100 screenshots/month cap
- Webhook handler for subscription lifecycle
- Billing page on frontend

### Phase 5 — Mac App 🔜
- SwiftUI or Tauri menubar app
- Replaces CLI agent
- Auto-updates via Sparkle

### Phase 6 — Privacy + Security 🔜
- Images never stored on server (in-memory only)
- HTTPS enforcement, rate limiting
- Privacy policy page
- GDPR delete-my-data endpoint

### Phase 7 — Growth Features 🔜
- Backfill existing screenshots
- Smart folders (saved searches)
- Export to CSV/ZIP
- iOS app (iCloud sync)
- Team plan

---

## Business Model

| Plan | Price | Limit | Notes |
|---|---|---|---|
| Free | $0 | 100 screenshots/month | OCR only, no AI description |
| Pro | $8/month | Unlimited | AI descriptions + tags |
| Pro Private | $15/month | Unlimited | Local model, no cloud |

**Unit economics (Pro):** ~$1.80/month API cost at 20 screenshots/day → ~$6.20 margin per user.

---

## Decisions Made
- **SQLite over Postgres for Phase 1** — single-user local app, no infra overhead. Will migrate when multi-tenancy is needed.
- **No Redis in Phase 1** — in-process async queue is sufficient. Add Redis + RQ when job volume justifies it.
- **No embeddings/vector search** — FTS5 is sufficient because Claude descriptions are rich enough to bridge vocabulary gaps. Revisit if users report search misses.
- **Images never leave server memory** — processed in-memory, immediately discarded. Fundamental privacy guarantee.
- **User brings Anthropic API key (dev)** — for Phase 1 dev, the key is set in backend `.env`. In production (Phase 4+), we run a shared key and absorb cost via subscription margin.
