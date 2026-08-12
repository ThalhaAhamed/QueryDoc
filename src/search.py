import os
import time
from dotenv import load_dotenv
from .vectorstore import FaissVectorStore
from .telemetry import TelemetryTracer
from langchain_groq import ChatGroq
from typing import Dict, Any, Optional
from sentence_transformers import CrossEncoder
import tiktoken

load_dotenv()


class RAGSearch:
    def __init__(
        self,
        persist_dir: str = "faiss_store",
        embedding_model: str = "all-MiniLM-L6-v2",
        llm_model: str = "llama-3.1-8b-instant"
    ):
        self.persist_dir = persist_dir
        self.embedding_model_name = embedding_model
        self.llm_model_name = llm_model

        self.vectorstore = FaissVectorStore(persist_dir, embedding_model)

        # Load or build vector store
        faiss_path = os.path.join(persist_dir, "faiss.index")
        meta_path = os.path.join(persist_dir, "metadata.pkl")

        if os.path.exists(faiss_path) and os.path.exists(meta_path):
            self.vectorstore.load()
        else:
            print("[INFO] No existing FAISS index found. Starting with empty store.")

        # Initialize Cross-Encoder for Reranking
        self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        
        # Telemetry
        self.tracer = TelemetryTracer(os.path.join(persist_dir, "telemetry.jsonl"))

        groq_api_key = os.getenv("GROQ_API_KEY")

        self.llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name=llm_model
        )
        
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        self.default_temperature = 0.7
        self.default_max_tokens = 1024

        print(f"[INFO] Groq LLM initialized: {llm_model}")

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def search_and_summarize(self, query: str, top_k: int = 5) -> str:
        results = self.search_with_metadata(query, top_k=top_k)
        return results.get("response", "Error generating summary.")

    def search_with_metadata(
        self,
        query: str,
        top_k: int = 5,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        min_similarity: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Enhanced search with Hybrid Retrieval -> CrossEncoder Reranking -> LLM Citation Generation.
        """
        start_time = time.time()

        # 1. Retrieval (Hybrid: BM25 + FAISS) - Fetch more for reranking
        initial_k = max(15, top_k * 3)
        retrieval_start = time.time()
        results = self.vectorstore.query(
            query,
            top_k=initial_k,
            min_similarity=min_similarity,
        )
        retrieval_time = (time.time() - retrieval_start) * 1000  # ms

        # 2. Reranking (CrossEncoder)
        rerank_start = time.time()
        if not results:
            return {
                "response": "No relevant documents found for your query. Please upload some documents first or try a different question.",
                "sources": [],
                "metadata": {
                    "total_chunks_searched": self.vectorstore.get_stats().get("total_vectors", 0),
                    "chunks_retrieved": 0,
                    "retrieval_time_ms": round(retrieval_time, 2),
                },
            }

        texts: list[str] = [r["metadata"].get("text", "") for r in results]
        pairs: list[tuple[str, str]] = [(query, text) for text in texts]
        
        rerank_scores = self.reranker.predict(pairs)  # type: ignore[call-overload]
        
        for i, score in enumerate(rerank_scores):
            results[i]["rerank_score"] = float(score)
            
        results.sort(key=lambda x: x["rerank_score"], reverse=True)
        top_results = results[:top_k]
        rerank_time = (time.time() - rerank_start) * 1000

        # Build context and sources
        sources = []
        context_parts = []
        for i, r in enumerate(top_results):
            meta = r.get("metadata", {}) or {}
            source_filename = meta.get("source_filename", f"Doc_{i}")
            source_id = f"[{i+1}]"
            
            context_parts.append(f"Source {source_id} (Filename: {source_filename}):\n{meta.get('text', '')}")
            
            sources.append({
                "document": source_filename,
                "chunk_index": r.get("index", -1),
                "similarity_score": round(r.get("similarity", 0), 4),
                "rerank_score": round(r.get("rerank_score", 0), 4),
                "text_preview": meta.get("text", "")[:200] + "..." if len(meta.get("text", "")) > 200 else meta.get("text", ""),
                "page": meta.get("page", -1),
                "citation_id": source_id
            })

        context = "\n\n".join(context_parts)

        # 3. Generation (with citation enforcement)
        prompt = f"""You are a helpful AI assistant. Answer the user's question based ONLY on the provided context from their documents.
Be thorough and precise. If the context doesn't contain enough information to fully answer, say so.
CRITICAL: You MUST cite your sources using the provided Source IDs (e.g., [1], [2]). Do not hallucinate information.
Use markdown formatting for your response when appropriate.

User Question: {query}

Context from documents:
{context}

Answer:"""

        input_tokens = self.count_tokens(prompt)

        temp = temperature if temperature is not None else self.default_temperature
        tokens = max_tokens if max_tokens is not None else self.default_max_tokens

        llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name=self.llm_model_name,
            temperature=temp,
            max_tokens=tokens,
        )

        generation_start = time.time()
        response = llm.invoke([prompt])
        generation_time = (time.time() - generation_start) * 1000

        output_tokens = self.count_tokens(str(response.content))

        # 4. Telemetry Logging
        self.tracer.log_request(
            query=query,
            retrieval_time_ms=retrieval_time,
            rerank_time_ms=rerank_time,
            generation_time_ms=generation_time,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            chunks_retrieved=len(sources),
            success=True
        )

        total_time = (time.time() - start_time) * 1000

        return {
            "response": response.content,
            "sources": sources,
            "metadata": {
                "total_chunks_searched": self.vectorstore.get_stats().get("total_vectors", 0),
                "chunks_retrieved": len(sources),
                "retrieval_time_ms": round(retrieval_time, 2),
                "rerank_time_ms": round(rerank_time, 2),
                "generation_time_ms": round(generation_time, 2),
                "total_time_ms": round(total_time, 2),
            },
        }