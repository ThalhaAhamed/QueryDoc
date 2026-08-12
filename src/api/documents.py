import os
import sys
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import List

router = APIRouter(prefix="/api", tags=["documents"])

# Global references set by server.py
vectorstore = None
doc_registry = None
data_loader_module = None
_ingestion_queue = None

def _get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

UPLOAD_DIR = os.path.join(_get_base_dir(), "uploads")
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv"}


def init_documents(vs, registry, loader, ingestion_queue_instance):
    global vectorstore, doc_registry, data_loader_module, _ingestion_queue
    vectorstore = vs
    doc_registry = registry
    data_loader_module = loader
    _ingestion_queue = ingestion_queue_instance
    os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Upload — returns 202 Accepted immediately; processing happens in background
# ---------------------------------------------------------------------------

@router.post("/documents/upload", status_code=202)
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Upload one or more documents.
    Files are saved to disk and queued for background ingestion.
    Returns job IDs that the frontend can poll for status.
    """
    if vectorstore is None or _ingestion_queue is None:
        raise HTTPException(status_code=503, detail="Vector store not initialized")

    results = []

    for file in files:
        if not file.filename:
            results.append({"filename": None, "status": "error", "message": "No filename provided."})
            continue
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            results.append({
                "filename": file.filename,
                "status": "error",
                "message": f"Unsupported file type: {ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            })
            continue

        # Ensure unique filename to avoid collisions
        base, extension = os.path.splitext(file.filename)
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        counter = 1
        while os.path.exists(file_path):
            file_path = os.path.join(UPLOAD_DIR, f"{base}_{counter}{extension}")
            counter += 1

        try:
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            file_size = len(content)
        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "error",
                "message": f"Failed to save file: {str(e)}",
            })
            continue

        # Register document with status='queued'
        assert doc_registry is not None
        doc_id = doc_registry.add_document(
            filename=os.path.basename(file_path),
            file_size=file_size,
            file_path=file_path,
            status="queued",
        )

        # Enqueue for background processing — returns immediately
        job_id = _ingestion_queue.submit_job(
            doc_id=doc_id,
            filename=os.path.basename(file_path),
            file_path=file_path,
        )

        results.append({
            "filename": file.filename,
            "doc_id": doc_id,
            "job_id": job_id,
            "status": "queued",
            "message": "Queued for background ingestion.",
        })

    return JSONResponse(status_code=202, content={"results": results})


# ---------------------------------------------------------------------------
# Ingestion job status endpoints
# ---------------------------------------------------------------------------

@router.get("/documents/jobs")
async def list_ingestion_jobs():
    """Return status of all ingestion jobs (most recent first)."""
    if _ingestion_queue is None:
        raise HTTPException(status_code=503, detail="Ingestion queue not initialized")
    return {
        "jobs": _ingestion_queue.get_all_jobs(),
        "active_count": _ingestion_queue.get_active_job_count(),
    }


@router.get("/documents/jobs/{job_id}")
async def get_ingestion_job(job_id: str):
    """Return status of a specific ingestion job."""
    if _ingestion_queue is None:
        raise HTTPException(status_code=503, detail="Ingestion queue not initialized")
    job = _ingestion_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ---------------------------------------------------------------------------
# List documents — paginated
# ---------------------------------------------------------------------------

@router.get("/documents")
async def list_documents(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=200, description="Results per page"),
    search: str = Query(default="", description="Filter by filename (case-insensitive)"),
):
    """List indexed documents with pagination and optional filename search."""
    if doc_registry is None:
        raise HTTPException(status_code=503, detail="Document registry not initialized")

    docs = doc_registry.get_all_documents()

    # Sort by upload date descending
    docs.sort(key=lambda d: d.get("upload_date", ""), reverse=True)

    # Filter by search term
    if search:
        term = search.lower()
        docs = [d for d in docs if term in d.get("filename", "").lower()]

    total = len(docs)
    total_pages = max(1, (total + page_size - 1) // page_size)
    start = (page - 1) * page_size
    end = start + page_size
    page_docs = docs[start:end]

    # Format file sizes
    for doc in page_docs:
        size = doc.get("file_size", 0)
        if size < 1024:
            doc["file_size_display"] = f"{size} B"
        elif size < 1024 * 1024:
            doc["file_size_display"] = f"{size / 1024:.1f} KB"
        else:
            doc["file_size_display"] = f"{size / (1024 * 1024):.1f} MB"

    return {
        "documents": page_docs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


# ---------------------------------------------------------------------------
# Delete document
# ---------------------------------------------------------------------------

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and its embeddings."""
    if doc_registry is None or vectorstore is None:
        raise HTTPException(status_code=503, detail="Not initialized")

    doc = doc_registry.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove from vector store
    vectorstore.delete_by_source(doc_id)

    # Remove uploaded file
    file_path = doc.get("file_path", "")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    # Remove from registry
    doc_registry.remove_document(doc_id)

    return {"message": f"Document '{doc.get('filename')}' deleted successfully."}


# ---------------------------------------------------------------------------
# Re-index document
# ---------------------------------------------------------------------------

@router.post("/documents/{doc_id}/reindex")
async def reindex_document(doc_id: str):
    """Re-queue a specific document for re-ingestion."""
    if doc_registry is None or vectorstore is None or _ingestion_queue is None:
        raise HTTPException(status_code=503, detail="Not initialized")

    doc = doc_registry.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc.get("file_path", "")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Source file not found on disk")

    # Remove old embeddings first
    vectorstore.delete_by_source(doc_id)

    # Mark as queued and re-submit
    doc_registry.update_document(doc_id, status="queued")

    job_id = _ingestion_queue.submit_job(
        doc_id=doc_id,
        filename=doc.get("filename", ""),
        file_path=file_path,
    )

    return {
        "message": f"Document '{doc.get('filename')}' queued for re-ingestion.",
        "job_id": job_id,
    }
