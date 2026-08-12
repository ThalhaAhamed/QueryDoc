"""
QueryDoc — Resume stuck ingestion (memory-optimized)
Re-processes all documents stuck in 'queued' or 'processing' status.
Reuses a single embedding model instance and processes one doc at a time.
"""
import json
import os
import sys
import time
import gc

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.document_registry import DocumentRegistry
from src import data_loader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import pickle

import logging
logging.getLogger("pypdf").setLevel(logging.ERROR)
logging.getLogger("pypdf._reader").setLevel(logging.ERROR)

FAISS_DIR = "faiss_store"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def main():
    # Load registry
    registry = DocumentRegistry(persist_dir=FAISS_DIR)
    all_docs = registry.get_all_documents()

    stuck = [d for d in all_docs if d.get("status") in ("queued", "processing")]
    print(f"Found {len(stuck)} stuck documents out of {len(all_docs)} total.")

    if not stuck:
        print("Nothing to resume!")
        return

    # Load FAISS index + metadata directly
    faiss_path = os.path.join(FAISS_DIR, "faiss.index")
    meta_path = os.path.join(FAISS_DIR, "metadata.pkl")

    if os.path.exists(faiss_path):
        index = faiss.read_index(faiss_path)
        with open(meta_path, "rb") as f:
            metadata = pickle.load(f)
        print(f"Loaded FAISS index: {index.ntotal} vectors, dim={index.d}")
    else:
        index = None
        metadata = []
        print("No existing FAISS index — starting fresh.")

    # Load embedding model ONCE
    print("Loading embedding model (one time)...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print("Model ready.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )

    # Process each stuck document
    success = 0
    failed = 0
    skipped = 0

    for i, doc in enumerate(stuck):
        doc_id = doc["id"]
        filename = doc.get("filename", "unknown")
        file_path = doc.get("file_path", "")

        print(f"\n[{i+1}/{len(stuck)}] {filename} (id={doc_id})", end=" ... ")

        if not file_path or not os.path.exists(file_path):
            print("SKIP (file not found)")
            registry.update_document(doc_id, status="error")
            skipped += 1
            continue

        try:
            start = time.time()

            # Load document
            documents = data_loader.load_single_document(file_path)
            if not documents:
                raise ValueError("Empty document")

            # Chunk
            chunks = splitter.split_documents(documents)

            # Extract text
            texts = []
            chunk_metas = []
            for chunk in chunks:
                raw = getattr(chunk, "page_content", "") or ""
                clean = str(raw).encode("utf-8", "ignore").decode("utf-8").strip()
                if clean:
                    texts.append(clean)
                    meta = {"text": clean, "source_id": doc_id}
                    if hasattr(chunk, "metadata") and chunk.metadata:
                        meta["source_filename"] = chunk.metadata.get("source_filename", "")
                        meta["source_path"] = chunk.metadata.get("source_path", "")
                        meta["page"] = chunk.metadata.get("page", -1)
                    chunk_metas.append(meta)

            if not texts:
                raise ValueError("No extractable text")

            # Embed
            embeddings = model.encode(texts, show_progress_bar=False).astype("float32")

            # Add to FAISS index
            if index is None:
                index = faiss.IndexFlatL2(embeddings.shape[1])
            index.add(embeddings)
            metadata.extend(chunk_metas)

            chunk_count = len(texts)
            registry.update_document(doc_id, status="ready", chunk_count=chunk_count)
            elapsed = time.time() - start
            print(f"OK ({chunk_count} chunks, {elapsed:.1f}s)")
            success += 1

            # Save every 20 documents to avoid data loss
            if success % 20 == 0:
                print(f"  [CHECKPOINT] Saving index ({index.ntotal} vectors)...")
                faiss.write_index(index, faiss_path)
                with open(meta_path, "wb") as f:
                    pickle.dump(metadata, f)

            # Free memory
            del documents, chunks, texts, chunk_metas, embeddings
            gc.collect()

        except BaseException as e:
            print(f"ERROR ({e})")
            registry.update_document(doc_id, status="error")
            failed += 1

    # Final save
    if index is not None:
        print("\nSaving final FAISS index...")
        faiss.write_index(index, faiss_path)
        with open(meta_path, "wb") as f:
            pickle.dump(metadata, f)

    print(f"\n{'='*60}")
    print(f"DONE! Processed {success + failed + skipped} documents:")
    print(f"  Success: {success}")
    print(f"  Failed:  {failed}")
    print(f"  Skipped: {skipped}")
    if index:
        print(f"  Total FAISS vectors: {index.ntotal}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
