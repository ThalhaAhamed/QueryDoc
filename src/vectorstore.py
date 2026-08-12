import os
import faiss
import numpy as np
import pickle
import re
from typing import List, Any, Dict, Optional
from sentence_transformers import SentenceTransformer
from .embedding import EmbeddingPipeline
from rank_bm25 import BM25Okapi

class FaissVectorStore:
    def __init__(
        self,
        persist_dir: str = "faiss_store",
        embedding_model: str = "all-MiniLM-L6-v2",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)

        self.index = None
        self.metadata = []
        self.corpus = []
        self.bm25 = None

        self.embedding_model = embedding_model
        self.model = SentenceTransformer(embedding_model)

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        print(f"[INFO] Loaded embedding model: {embedding_model}")

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\w+', text.lower())

    def _rebuild_bm25(self):
        if self.metadata:
            self.corpus = [self._tokenize(m.get("text", "")) for m in self.metadata]
            self.bm25 = BM25Okapi(self.corpus)
        else:
            self.corpus = []
            self.bm25 = None

    def build_from_documents(self, documents: List[Any]):
        print(f"[INFO] Building vector store from {len(documents)} raw documents...")

        emb_pipe = EmbeddingPipeline(
            model_name=self.embedding_model,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        chunks = emb_pipe.chunk_documents(documents)
        embeddings = emb_pipe.embed_chunks(chunks)

        metadatas = []
        for chunk in chunks:
            meta = {"text": chunk.page_content}
            if hasattr(chunk, "metadata") and chunk.metadata:
                meta["source_filename"] = chunk.metadata.get("source_filename", "")
                meta["source_path"] = chunk.metadata.get("source_path", "")
                meta["page"] = chunk.metadata.get("page", -1)
            metadatas.append(meta)

        self.add_embeddings(
            np.array(embeddings).astype("float32"),
            metadatas,
        )

        self._rebuild_bm25()
        self.save()

        print(f"[INFO] Vector store built and saved to {self.persist_dir}")

    def add_documents(self, documents: List[Any], source_id: str = None, skip_bm25_rebuild: bool = False) -> int:
        """
        Embed and index a list of documents.
        Set skip_bm25_rebuild=True during batch ingestion to defer the
        expensive full-corpus BM25 rebuild until finalize_batch() is called.
        """
        emb_pipe = EmbeddingPipeline(
            model_name=self.embedding_model,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        chunks = emb_pipe.chunk_documents(documents)
        embeddings = emb_pipe.embed_chunks(chunks)

        metadatas = []
        for chunk in chunks:
            meta = {"text": chunk.page_content}
            if source_id:
                meta["source_id"] = source_id
            if hasattr(chunk, "metadata") and chunk.metadata:
                meta["source_filename"] = chunk.metadata.get("source_filename", "")
                meta["source_path"] = chunk.metadata.get("source_path", "")
                meta["page"] = chunk.metadata.get("page", -1)
            metadatas.append(meta)

        self.add_embeddings(
            np.array(embeddings).astype("float32"),
            metadatas,
        )

        if not skip_bm25_rebuild:
            self._rebuild_bm25()
            self.save()

        print(f"[INFO] Incrementally added {len(chunks)} chunks for source: {source_id}")
        return len(chunks)

    def finalize_batch(self):
        """Rebuild BM25 index and persist to disk. Call once after a batch of add_documents() with skip_bm25_rebuild=True."""
        print("[INFO] Finalizing batch: rebuilding BM25 and saving index...")
        self._rebuild_bm25()
        self.save()
        print(f"[INFO] Batch finalized. Total vectors: {self.index.ntotal if self.index else 0}")

    def delete_by_source(self, source_id: str) -> bool:
        if self.index is None or not self.metadata:
            return False

        keep_indices = []
        for i, meta in enumerate(self.metadata):
            if meta.get("source_id") != source_id:
                keep_indices.append(i)

        if len(keep_indices) == len(self.metadata):
            return False

        removed_count = len(self.metadata) - len(keep_indices)

        if len(keep_indices) == 0:
            self.index = None
            self.metadata = []
        else:
            dim = self.index.d
            all_vectors = np.array([
                self.index.reconstruct(i) for i in keep_indices
            ]).astype("float32")

            new_index = faiss.IndexFlatL2(dim)
            new_index.add(all_vectors)
            self.index = new_index
            self.metadata = [self.metadata[i] for i in keep_indices]

        self._rebuild_bm25()
        self.save()
        print(f"[INFO] Deleted {removed_count} vectors for source: {source_id}")
        return True

    def add_embeddings(self, embeddings: np.ndarray, metadatas: List[Any] = None):
        dim = embeddings.shape[1]
        if self.index is None:
            self.index = faiss.IndexFlatL2(dim)

        self.index.add(embeddings)
        if metadatas:
            self.metadata.extend(metadatas)

        print(f"[INFO] Added {embeddings.shape[0]} vectors to Faiss index.")

    def save(self):
        faiss_path = os.path.join(self.persist_dir, "faiss.index")
        meta_path = os.path.join(self.persist_dir, "metadata.pkl")

        if self.index is not None:
            faiss.write_index(self.index, faiss_path)
        else:
            if os.path.exists(faiss_path):
                os.remove(faiss_path)
            if os.path.exists(meta_path):
                os.remove(meta_path)
            return

        with open(meta_path, "wb") as f:
            pickle.dump(self.metadata, f)

        print(f"[INFO] Saved Faiss index and metadata to {self.persist_dir}")

    def load(self):
        faiss_path = os.path.join(self.persist_dir, "faiss.index")
        meta_path = os.path.join(self.persist_dir, "metadata.pkl")

        if not os.path.exists(faiss_path):
            print(f"[WARN] No Faiss index found at {faiss_path}. Starting empty.")
            return

        self.index = faiss.read_index(faiss_path)
        with open(meta_path, "rb") as f:
            self.metadata = pickle.load(f)
            
        self._rebuild_bm25()
        print(f"[INFO] Loaded Faiss index and metadata from {self.persist_dir}")

    def search_dense(self, query_embedding: np.ndarray, top_k: int = 5):
        if self.index is None or self.index.ntotal == 0:
            return []

        actual_k = min(top_k, self.index.ntotal)
        D, I = self.index.search(query_embedding, actual_k)
        
        results = []
        for idx, dist in zip(I[0], D[0]):
            if idx < 0:
                continue
            meta = self.metadata[idx] if idx < len(self.metadata) else None
            similarity = float(1.0 / (1.0 + dist))
            results.append({
                "index": int(idx),
                "distance": float(dist),
                "similarity": similarity,
                "metadata": meta,
                "dense_score": similarity
            })
        return results

    def query(self, query_text: str, top_k: int = 5, min_similarity: float = 0.0) -> List[Dict]:
        """
        Hybrid search using Reciprocal Rank Fusion (RRF) of Dense and Sparse results.
        """
        print(f"[INFO] Querying hybrid vector store for: '{query_text}'")

        if self.index is None or self.index.ntotal == 0:
            return []

        # 1. Dense Search
        clean_query = str(query_text or "").encode("utf-8", "ignore").decode("utf-8")
        query_emb = self.model.encode([clean_query]).astype("float32")
        dense_results = self.search_dense(query_emb, top_k=top_k * 2)

        # 2. Sparse Search (BM25)
        bm25_results = []
        if self.bm25:
            tokenized_query = self._tokenize(query_text)
            bm25_scores = self.bm25.get_scores(tokenized_query)
            # get top k indices
            top_bm25_idx = np.argsort(bm25_scores)[::-1][:top_k * 2]
            for idx in top_bm25_idx:
                score = bm25_scores[idx]
                if score > 0:
                    bm25_results.append({
                        "index": int(idx),
                        "bm25_score": float(score)
                    })

        # 3. Reciprocal Rank Fusion (RRF)
        k = 60
        rrf_scores = {}
        
        for rank, res in enumerate(dense_results):
            idx = res["index"]
            if idx not in rrf_scores:
                rrf_scores[idx] = {"score": 0.0, "meta": res["metadata"], "similarity": res["similarity"]}
            rrf_scores[idx]["score"] += 1.0 / (k + rank + 1)
            
        for rank, res in enumerate(bm25_results):
            idx = res["index"]
            if idx not in rrf_scores:
                rrf_scores[idx] = {"score": 0.0, "meta": self.metadata[idx], "similarity": 0.0}
            rrf_scores[idx]["score"] += 1.0 / (k + rank + 1)
            
        fused_results = []
        for idx, data in rrf_scores.items():
            fused_results.append({
                "index": idx,
                "similarity": data["similarity"],
                "rrf_score": data["score"],
                "metadata": data["meta"]
            })
            
        fused_results.sort(key=lambda x: x["rrf_score"], reverse=True)
        final_results = fused_results[:top_k]
        
        if min_similarity > 0:
            final_results = [r for r in final_results if r["similarity"] >= min_similarity]

        return final_results

    def get_stats(self) -> Dict:
        if self.index is None:
            return {"total_vectors": 0, "dimension": 0, "index_loaded": False}
        return {
            "total_vectors": int(self.index.ntotal),
            "dimension": int(self.index.d),
            "index_loaded": True,
            "has_bm25": self.bm25 is not None
        }

    def get_chunks_by_source(self, source_id: str) -> int:
        return sum(1 for m in self.metadata if m.get("source_id") == source_id)