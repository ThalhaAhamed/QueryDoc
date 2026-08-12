"""
QueryDoc — Async Ingestion Queue
Processes document uploads in the background so HTTP handlers return immediately.
Prevents timeout on large uploads and batches BM25 rebuilds for efficiency.
"""
import asyncio
import time
import uuid
from datetime import datetime
from typing import Dict, Optional, Any


class IngestionJob:
    """Represents a single document ingestion job."""

    def __init__(self, job_id: str, doc_id: str, filename: str, file_path: str):
        self.job_id = job_id
        self.doc_id = doc_id
        self.filename = filename
        self.file_path = file_path
        self.status: str = "queued"          # queued | processing | ready | error
        self.chunk_count: int = 0
        self.error_message: Optional[str] = None
        self.queued_at: str = datetime.now().isoformat()
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "doc_id": self.doc_id,
            "filename": self.filename,
            "status": self.status,
            "chunk_count": self.chunk_count,
            "error_message": self.error_message,
            "queued_at": self.queued_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


class IngestionQueue:
    """
    Lightweight async ingestion queue.
    - HTTP handlers call submit_job() → returns job_id immediately (202 Accepted).
    - Background worker task drains the queue, embeds documents, and finalizes
      BM25 once per idle period (no O(N²) per-upload rebuild).
    """

    # How long to wait for more jobs before calling finalize_batch (seconds)
    BATCH_FINALIZE_IDLE_SECONDS = 2.0

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._jobs: Dict[str, IngestionJob] = {}
        self._vectorstore = None
        self._doc_registry = None
        self._data_loader = None
        self._worker_task: Optional[asyncio.Task] = None
        self._needs_finalize: bool = False

    def init(self, vectorstore, doc_registry, data_loader_module):
        self._vectorstore = vectorstore
        self._doc_registry = doc_registry
        self._data_loader = data_loader_module

    def start(self):
        """Start the background worker. Call from the FastAPI lifespan startup."""
        self._worker_task = asyncio.create_task(self._worker())
        print("[IngestionQueue] Background worker started.")

    async def stop(self):
        """Gracefully stop the worker. Call from the FastAPI lifespan shutdown."""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        print("[IngestionQueue] Background worker stopped.")

    def submit_job(self, doc_id: str, filename: str, file_path: str) -> str:
        """Enqueue a document for background ingestion. Returns job_id immediately."""
        job_id = str(uuid.uuid4())[:12]
        job = IngestionJob(job_id=job_id, doc_id=doc_id, filename=filename, file_path=file_path)
        self._jobs[job_id] = job
        self._queue.put_nowait(job)
        print(f"[IngestionQueue] Job {job_id} queued for '{filename}'")
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict]:
        job = self._jobs.get(job_id)
        return job.to_dict() if job else None

    def get_all_jobs(self) -> list:
        # Return most recent first
        jobs = list(self._jobs.values())
        jobs.sort(key=lambda j: j.queued_at, reverse=True)
        return [j.to_dict() for j in jobs]

    def get_active_job_count(self) -> int:
        return sum(1 for j in self._jobs.values() if j.status in ("queued", "processing"))

    async def _worker(self):
        """
        Background worker loop.
        Processes jobs from the queue. After the queue drains, calls finalize_batch()
        once to rebuild BM25 and flush the FAISS index — instead of doing it per-file.
        """
        print("[IngestionQueue] Worker is running.")
        while True:
            try:
                # Wait up to BATCH_FINALIZE_IDLE_SECONDS for a job
                try:
                    job: IngestionJob = await asyncio.wait_for(
                        self._queue.get(), timeout=self.BATCH_FINALIZE_IDLE_SECONDS
                    )
                except asyncio.TimeoutError:
                    # No new job arrived — finalize any pending batch
                    if self._needs_finalize and self._vectorstore is not None:
                        print("[IngestionQueue] Idle timeout reached — finalizing batch...")
                        try:
                            await asyncio.get_event_loop().run_in_executor(
                                None, self._vectorstore.finalize_batch
                            )
                        except Exception as e:
                            print(f"[IngestionQueue] finalize_batch error: {e}")
                        self._needs_finalize = False
                    continue

                await self._process_job(job)
                self._queue.task_done()

            except asyncio.CancelledError:
                # Finalize before shutting down
                if self._needs_finalize and self._vectorstore is not None:
                    try:
                        self._vectorstore.finalize_batch()
                    except Exception:
                        pass
                raise

    async def _process_job(self, job: IngestionJob):
        """Process a single ingestion job in a thread executor (non-blocking)."""
        job.status = "processing"
        job.started_at = datetime.now().isoformat()

        if self._doc_registry:
            self._doc_registry.update_document(job.doc_id, status="processing")

        print(f"[IngestionQueue] Processing job {job.job_id}: '{job.filename}'")

        try:
            # Run blocking I/O + ML embedding in thread pool to not block the event loop
            chunk_count = await asyncio.get_event_loop().run_in_executor(
                None, self._ingest_document, job
            )
            job.status = "ready"
            job.chunk_count = chunk_count
            job.finished_at = datetime.now().isoformat()
            self._needs_finalize = True  # defer BM25 rebuild to batch finalize

            if self._doc_registry:
                self._doc_registry.update_document(
                    job.doc_id, status="ready", chunk_count=chunk_count
                )
            print(f"[IngestionQueue] Job {job.job_id} done — {chunk_count} chunks indexed.")

        except Exception as e:
            job.status = "error"
            job.error_message = str(e)
            job.finished_at = datetime.now().isoformat()

            if self._doc_registry:
                self._doc_registry.update_document(job.doc_id, status="error")
            print(f"[IngestionQueue] Job {job.job_id} failed: {e}")

    def _ingest_document(self, job: IngestionJob) -> int:
        """Synchronous ingestion — runs in thread executor."""
        documents = self._data_loader.load_single_document(job.file_path)
        if not documents:
            raise ValueError("Document appears to be empty.")

        # skip_bm25_rebuild=True: defer BM25 to finalize_batch()
        chunk_count = self._vectorstore.add_documents(
            documents,
            source_id=job.doc_id,
            skip_bm25_rebuild=True,
        )
        return chunk_count


# Singleton instance — imported by server.py and documents.py
ingestion_queue = IngestionQueue()
