#!/usr/bin/env bash
# start.sh — Launch ScreenVault backend + file watcher in one command.
#
# Usage:
#   ./start.sh
#   WATCH_DIR=~/Pictures/Screenshots ./start.sh   # custom watch folder

set -euo pipefail

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
AGENT_DIR="$SCRIPT_DIR/agent"

# ── Config (override via env) ──────────────────────────────────────────────────
export WATCH_DIR="${WATCH_DIR:-$HOME/Desktop/ScreenVault_Screenshots}"
export BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
export SCREENVAULT_USER_ID="${SCREENVAULT_USER_ID:-dev-user-001}"
export BACKEND_PORT="${BACKEND_PORT:-8000}"

# Load backend .env if it exists (sets ANTHROPIC_API_KEY etc.)
if [ -f "$BACKEND_DIR/.env" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$BACKEND_DIR/.env"
    set +a
fi

# ── Create watch folder if it doesn't exist ───────────────────────────────────
if [ ! -d "$WATCH_DIR" ]; then
    echo "[setup] Creating screenshots folder at $WATCH_DIR"
    mkdir -p "$WATCH_DIR"
else
    echo "[setup] Watch folder exists: $WATCH_DIR"
fi

# ── Trap Ctrl+C — kill both child processes cleanly ───────────────────────────
BACKEND_PID=""
WATCHER_PID=""

cleanup() {
    echo ""
    echo "[shutdown] Stopping ScreenVault..."
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null && echo "[shutdown] Backend stopped"
    [ -n "$WATCHER_PID" ] && kill "$WATCHER_PID" 2>/dev/null && echo "[shutdown] Watcher stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM

# ── Start backend ──────────────────────────────────────────────────────────────
echo "[backend] Starting on port $BACKEND_PORT..."
cd "$BACKEND_DIR"
uvicorn main:app --port "$BACKEND_PORT" &
BACKEND_PID=$!

# Give the backend a moment to bind its port before the watcher starts uploading
sleep 2

# ── Start watcher ──────────────────────────────────────────────────────────────
echo "[watcher] Starting — watching $WATCH_DIR"
cd "$AGENT_DIR"
python watcher.py &
WATCHER_PID=$!

# ── Status ─────────────────────────────────────────────────────────────────────
echo ""
echo "  ScreenVault is running"
echo "  Backend  → http://localhost:$BACKEND_PORT"
echo "  Watching → $WATCH_DIR"
echo "  Press Ctrl+C to stop both services"
echo ""

# Wait for both processes — exit if either crashes
wait $BACKEND_PID $WATCHER_PID
