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

### Point macOS screenshots at ScreenVault

The best experience is to set your Mac's default screenshot save location to the ScreenVault watch folder, so every screenshot you take is automatically picked up and searchable.

1. Press **Cmd + Shift + 5** to open the Screenshot toolbar
2. Click **Options**
3. Under *Save to*, click **Other Location…**
4. Navigate to `~/Desktop/ScreenVault_Screenshots` and click **Choose**

From now on every screenshot you take (Cmd+Shift+3, Cmd+Shift+4, Cmd+Shift+5) saves directly into ScreenVault and is processed automatically in the background.

> You can also drop existing screenshots into `~/Desktop/ScreenVault_Screenshots` at any time — they will be picked up on the next page load.

### Search

Open [http://localhost:3000/vault](http://localhost:3000/vault) and search in natural language — *"Chelsea badge"*, *"invoice from March"*, *"dark mode settings screen"*.

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
