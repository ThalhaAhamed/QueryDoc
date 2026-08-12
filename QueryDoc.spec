# -*- mode: python ; coding: utf-8 -*-
"""
QueryDoc — PyInstaller Spec File
Packages the application into a one-folder distributable .exe.
"""

import os
import sys
import importlib

block_cipher = None

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = os.path.abspath(".")
STATIC_DIR = os.path.join(ROOT, "static")

# ---------------------------------------------------------------------------
# Data files to bundle
# ---------------------------------------------------------------------------

datas = [
    # Pre-built React frontend
    (STATIC_DIR, "static"),
    # Python source modules (imported at runtime by server.py)
    (os.path.join(ROOT, "src"), "src"),
    # Server module (imported by launcher)
    (os.path.join(ROOT, "server.py"), "."),
]

# ---------------------------------------------------------------------------
# Hidden imports — dynamically loaded packages PyInstaller can't detect
# ---------------------------------------------------------------------------

hiddenimports = [
    # Server
    "server",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",

    # FastAPI / Starlette
    "fastapi",
    "starlette",
    "starlette.responses",
    "starlette.routing",
    "starlette.middleware",
    "starlette.middleware.cors",
    "multipart",
    "python_multipart",

    # ML / Embeddings
    "sentence_transformers",
    "torch",
    "transformers",
    "tokenizers",
    "faiss",
    "numpy",
    "sklearn",
    "sklearn.utils._cython_blas",
    "scipy",

    # LangChain
    "langchain",
    "langchain_core",
    "langchain_community",
    "langchain_community.document_loaders",
    "langchain_groq",
    "langchain_text_splitters",

    # Misc
    "tiktoken",
    "tiktoken_ext",
    "tiktoken_ext.openai_public",
    "rank_bm25",
    "dotenv",
    "python_dotenv",
    "groq",
    "httpx",
    "httpcore",
    "anyio",
    "sniffio",
    "pydantic",
    "pydantic_core",
    "orjson",
    "docx2txt",
    "pypdf",
    "pymupdf",
    "fitz",
    "aiofiles",

    # pywebview
    "webview",

    # Source modules
    "src",
    "src.search",
    "src.vectorstore",
    "src.embedding",
    "src.data_loader",
    "src.document_registry",
    "src.ingestion_queue",
    "src.telemetry",
    "src.api",
    "src.api.chat",
    "src.api.documents",
    "src.api.settings",
    "src.api.status",
]

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

a = Analysis(
    ["launcher.py"],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "tkinter",
        "IPython",
        "ipykernel",
        "jupyter",
        "notebook",
        "pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="QueryDoc",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window — splash screen handles the loading UI
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="QueryDoc",
)
