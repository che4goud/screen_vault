# ScreenVault

Semantic search for your screenshots. Drop screenshots into a watch folder — ScreenVault runs OCR, generates a description and tags with Gemini, embeds them, and lets you search your library in natural language.

**macOS only** — OCR uses Apple Vision via `ocrmac`.

---

## Requirements

- macOS 13+
- Python 3.11+
- Node.js 18+
- A Google API key with the **Generative Language API** enabled ([get one here](https://aistudio.google.com/app/apikey)) — free tier works, but billing must be enabled on the GCP project for reliable quota

---

## Setup

### 1. Clone

```bash
git clone https://github.com/che4goud/screen_vault.git
cd screen_vault/screenvault
```

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env` from the example:

```bash
cp .env.example .env
```

Then open `.env` and set your `GOOGLE_API_KEY`. The other values work as-is.

Seed the database (run once):

```bash
python seed_user.py
cd ..
```

### 3. Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run build
cd ..
```

> **Note:** `npm run dev` is broken on Apple Silicon (Turbopack crash). Always use `npm run build && npm start`.

---

## Running

Open two terminals:

**Terminal 1 — backend + file watcher:**
```bash
cd screenvault
./start.sh
```

**Terminal 2 — frontend:**
```bash
cd screenvault/frontend
npm start
```

Open [http://localhost:3000/vault](http://localhost:3000/vault).

---

## Usage

1. Drop screenshots into `~/Desktop/ScreenVault_Screenshots`
2. The watcher picks them up automatically and processes them in the background
3. Search your library at `http://localhost:3000/vault`

Screenshots are also synced on every page load, so you can drop files in and refresh to trigger processing.

---

## How it works

```
New screenshot
  → OCR (Apple Vision)
  → Description + tags  (Gemini 2.5 Flash)
  → Embedding           (gemini-embedding-2-preview, 3072-dim)
  → SQLite

Search query
  → Embed query
  → Cosine similarity (semantic) + FTS5 BM25 (keyword)
  → Reciprocal Rank Fusion
  → Results + async AI summary
```

---

## Custom watch folder

```bash
WATCH_DIR=~/Pictures/Screenshots ./start.sh
```
