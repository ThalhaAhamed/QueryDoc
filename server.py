"""
QueryDoc — FastAPI Server
Serves the web application frontend and exposes the RAG API.
"""
import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# --- Initialize RAG engine and registries ---
from src.search import RAGSearch
from src.document_registry import DocumentRegistry
from src import data_loader as data_loader_module
from src.ingestion_queue import ingestion_queue

print("[STARTUP] Initializing QueryDoc engine...")

rag_engine = RAGSearch(
    persist_dir="faiss_store",
    embedding_model="all-MiniLM-L6-v2",
    llm_model="llama-3.1-8b-instant",
)

doc_registry = DocumentRegistry(persist_dir="faiss_store")

print(f"[STARTUP] Loaded {doc_registry.get_document_count()} registered documents.")
print(f"[STARTUP] FAISS stats: {rag_engine.vectorstore.get_stats()}")

# Wire ingestion queue with dependencies
ingestion_queue.init(rag_engine.vectorstore, doc_registry, data_loader_module)


# --- Lifespan: start/stop background worker ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    ingestion_queue.start()
    yield
    await ingestion_queue.stop()


# --- App setup ---
app = FastAPI(
    title="QueryDoc",
    description="AI-powered document assistant using Retrieval-Augmented Generation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Wire up API routers ---
from src.api.chat import router as chat_router, init_chat
from src.api.documents import router as docs_router, init_documents
from src.api.status import router as status_router, init_status
from src.api.settings import router as settings_router, get_settings

init_chat(rag_engine, get_settings())
init_documents(rag_engine.vectorstore, doc_registry, data_loader_module, ingestion_queue)
init_status(rag_engine, doc_registry)

app.include_router(chat_router)
app.include_router(docs_router)
app.include_router(status_router)
app.include_router(settings_router)

# --- Static files ---
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root():
    """Serve the main SPA."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
