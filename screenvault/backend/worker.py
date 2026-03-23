"""
worker.py — Async job queue for processing screenshots.

Uses a simple in-process queue backed by asyncio so we don't need Redis
for Phase 1. Jobs are processed concurrently up to MAX_WORKERS at a time.

Upgrade path: swap the asyncio queue for RQ/Celery when moving to prod.
"""

import asyncio
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

MAX_WORKERS = int(__import__("os").getenv("MAX_WORKERS", "5"))


@dataclass
class Job:
    user_id: str
    src_path: str
    submitted_at: datetime = None

    def __post_init__(self):
        if self.submitted_at is None:
            self.submitted_at = datetime.now()


class IngestionQueue:
    """
    Thread-safe async queue that processes screenshot jobs concurrently.

    Usage:
        queue = IngestionQueue()
        await queue.start()
        await queue.enqueue(Job(user_id="abc", src_path="/path/to/shot.png"))
    """

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(MAX_WORKERS)
        self._running = False
        self._stats = {"processed": 0, "failed": 0, "in_flight": 0}

    async def start(self):
        """Start the background consumer loop."""
        self._running = True
        asyncio.create_task(self._consumer())
        print(f"[worker] Queue started — max {MAX_WORKERS} concurrent workers")

    async def stop(self):
        self._running = False
        await self._queue.join()
        print("[worker] Queue drained and stopped")

    async def enqueue(self, job: Job):
        await self._queue.put(job)
        print(f"[worker] Enqueued job for {job.src_path} (queue size: {self._queue.qsize()})")

    @property
    def stats(self) -> dict:
        return {**self._stats, "queued": self._queue.qsize()}

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _consumer(self):
        """Continuously pull jobs from the queue and dispatch workers."""
        while self._running:
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                # Dispatch to a worker without blocking the consumer loop
                asyncio.create_task(self._process(job))
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"[worker] Consumer error: {e}")

    async def _process(self, job: Job):
        """Run the pipeline for one job, respecting the concurrency semaphore."""
        async with self._semaphore:
            self._stats["in_flight"] += 1
            try:
                # Pipeline is CPU/IO bound — run it in a thread pool
                # so it doesn't block the event loop
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, _run_pipeline, job.user_id, job.src_path
                )
                self._stats["processed"] += 1
                print(f"[worker] Done: {job.src_path} → id={result['id']}")
            except Exception:
                self._stats["failed"] += 1
                print(f"[worker] Failed: {job.src_path}")
                traceback.print_exc()
            finally:
                self._stats["in_flight"] -= 1
                self._queue.task_done()


def _run_pipeline(user_id: str, src_path: str) -> dict:
    """Synchronous wrapper around pipeline.process_screenshot for thread pool execution."""
    from pipeline import process_screenshot
    return process_screenshot(user_id, src_path)


# ── Singleton queue instance shared across the app ────────────────────────────

_queue_instance: IngestionQueue | None = None


def get_queue() -> IngestionQueue:
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = IngestionQueue()
    return _queue_instance
