from pathlib import Path
from typing import List, Any

from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader, CSVLoader


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".docx", ".md", ".csv"}


def load_single_document(file_path: str) -> List[Any]:
    """
    Load a single document file and return LangChain document objects.

    Supported: PDF, TXT, DOCX, Markdown, CSV
    """
    path = Path(file_path).resolve()
    ext = path.suffix.lower()

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}. Supported: {SUPPORTED_EXTENSIONS}")

    documents = []

    try:
        if ext == ".pdf":
            loader = PyPDFLoader(str(path))
            documents = loader.load()
            print(f"[INFO] Loaded {len(documents)} pages from PDF: {path.name}")

        elif ext == ".docx":
            loader = Docx2txtLoader(str(path))
            documents = loader.load()
            print(f"[INFO] Loaded DOCX: {path.name}")

        elif ext in (".txt", ".md"):
            loader = TextLoader(str(path), encoding="utf-8")
            documents = loader.load()
            print(f"[INFO] Loaded text file: {path.name}")

        elif ext == ".csv":
            loader = CSVLoader(str(path), encoding="utf-8")
            documents = loader.load()
            print(f"[INFO] Loaded CSV file: {path.name}")

    except Exception as e:
        print(f"[ERROR] Failed to load {path.name}: {e}")
        raise

    # Tag each document with source filename and sanitize text
    for doc in documents:
        if hasattr(doc, "page_content") and doc.page_content:
            raw_text = str(doc.page_content)
            doc.page_content = raw_text.encode("utf-8", "ignore").decode("utf-8")
        doc.metadata["source_filename"] = path.name
        doc.metadata["source_path"] = str(path)

    return documents


def load_all_documents(data_dir: str) -> List[Any]:
    """
    Load all supported files from the data directory and convert to LangChain document structure.

    Supported: PDF, TXT, DOCX, Markdown
    """

    # Use project root data folder
    data_path = Path(data_dir).resolve()
    print(f"[DEBUG] Data path: {data_path}")

    documents = []

    # PDF files
    pdf_files = list(data_path.glob("**/*.pdf"))
    print(f"[DEBUG] Found {len(pdf_files)} PDF files: {[str(f) for f in pdf_files]}")

    for pdf_file in pdf_files:
        print(f"[DEBUG] Loading PDF: {pdf_file}")

        try:
            loader = PyPDFLoader(str(pdf_file))
            loaded = loader.load()

            print(f"[DEBUG] Loaded {len(loaded)} PDF docs from {pdf_file}")

            documents.extend(loaded)

        except Exception as e:
            print(f"[ERROR] Failed to load PDF {pdf_file}: {e}")

    # Text files
    txt_files = list(data_path.glob("**/*.txt"))
    for txt_file in txt_files:
        try:
            loader = TextLoader(str(txt_file), encoding="utf-8")
            loaded = loader.load()
            documents.extend(loaded)
            print(f"[DEBUG] Loaded {len(loaded)} docs from {txt_file}")
        except Exception as e:
            print(f"[ERROR] Failed to load TXT {txt_file}: {e}")

    # DOCX files
    docx_files = list(data_path.glob("**/*.docx"))
    for docx_file in docx_files:
        try:
            loader = Docx2txtLoader(str(docx_file))
            loaded = loader.load()
            documents.extend(loaded)
            print(f"[DEBUG] Loaded {len(loaded)} docs from {docx_file}")
        except Exception as e:
            print(f"[ERROR] Failed to load DOCX {docx_file}: {e}")

    # Markdown files
    md_files = list(data_path.glob("**/*.md"))
    for md_file in md_files:
        try:
            loader = TextLoader(str(md_file), encoding="utf-8")
            loaded = loader.load()
            documents.extend(loaded)
            print(f"[DEBUG] Loaded {len(loaded)} docs from {md_file}")
        except Exception as e:
            print(f"[ERROR] Failed to load MD {md_file}: {e}")

    # CSV files
    csv_files = list(data_path.glob("**/*.csv"))
    for csv_file in csv_files:
        try:
            loader = CSVLoader(str(csv_file), encoding="utf-8")
            loaded = loader.load()
            documents.extend(loaded)
            print(f"[DEBUG] Loaded {len(loaded)} docs from {csv_file}")
        except Exception as e:
            print(f"[ERROR] Failed to load CSV {csv_file}: {e}")

    print(f"[INFO] Total documents loaded: {len(documents)}")
    return documents