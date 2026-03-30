"""
main.py — FastAPI application entry point.

Run with:
    uvicorn main:app --reload --port 8000
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import init_db
from worker import get_queue
from routes.ingest import router as ingest_router
from routes.search import router as search_router
from routes.organise import router as organise_router

STORAGE_DIR = os.path.expanduser(os.getenv("STORAGE_DIR", "~/.screenvault"))
THUMBNAILS_DIR = os.path.join(STORAGE_DIR, "thumbnails")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    queue = get_queue()
    await queue.start()
    print("[app] ScreenVault backend ready")
    yield
    # Shutdown
    await queue.stop()
    print("[app] ScreenVault backend shut down")


app = FastAPI(
    title="ScreenVault API",
    description="Screenshot ingestion, processing, and search backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve thumbnails as static files so the frontend can display them
os.makedirs(THUMBNAILS_DIR, exist_ok=True)
app.mount("/thumbnails", StaticFiles(directory=THUMBNAILS_DIR), name="thumbnails")

# Routes
app.include_router(ingest_router, tags=["Ingestion"])
app.include_router(search_router, tags=["Search"])
app.include_router(organise_router, tags=["Organise"])


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/stats")
def stats():
    queue = get_queue()
    return queue.stats
