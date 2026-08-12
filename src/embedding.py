from typing import List, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import numpy as np


class EmbeddingPipeline:

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.model = SentenceTransformer(model_name)
        print(f"[INFO] Loaded embedding model: {model_name}")

    def chunk_documents(self, documents: List[Any]) -> List[Any]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )

        chunks = splitter.split_documents(documents)

        # Drop empty/whitespace-only chunks here — once — so every downstream
        # consumer (embeddings, metadata) works off the same aligned list.
        # Filtering independently at each site risks embeddings and metadata
        # ending up different lengths, which desyncs FAISS index positions
        # from their metadata.
        kept = []
        for chunk in chunks:
            raw_content = getattr(chunk, "page_content", "") or ""
            clean_content = str(raw_content).encode("utf-8", "ignore").decode("utf-8")
            if clean_content.strip():
                chunk.page_content = clean_content
                kept.append(chunk)

        print(f"[INFO] Split {len(documents)} documents into {len(kept)} chunks "
              f"({len(chunks) - len(kept)} empty chunks dropped).")
        return kept

    def embed_chunks(self, chunks: List[Any]) -> np.ndarray:
        texts = [chunk.page_content for chunk in chunks]

        if not texts:
            raise ValueError("No extractable text found in the document chunks.")

        print(f"[INFO] Generating embeddings for {len(texts)} chunks...")

        embeddings = self.model.encode(
            texts,
            show_progress_bar=True,
        )

        result = np.array(embeddings)
        print(f"[INFO] Embeddings shape: {result.shape}")
        return result