import os
from pathlib import Path
from typing import Any

import chromadb
from ollama import Client

CHROMA_PATH = os.getenv("CHROMA_PATH", "./db")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "docs")
MAX_CHARS = int(os.getenv("CHUNK_MAX_CHARS", "900"))

BASE_DIR = Path(__file__).resolve().parent
RESUME_PATH = Path(os.getenv("RESUME_PATH", str(BASE_DIR / "resume.txt")))


def chunk_text_section_aware(text: str, max_chars: int = 900) -> list[str]:
    text = text.replace("\r\n", "\n").strip()
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for p in paragraphs:
        added_len = len(p) + (2 if current else 0)
        if current and (current_len + added_len) > max_chars:
            chunks.append("\n\n".join(current).strip())
            current = [p]
            current_len = len(p)
        else:
            current.append(p)
            current_len += added_len

    if current:
        chunks.append("\n\n".join(current).strip())

    return chunks


def embed_text(client: Client, text: str) -> list[float]:
    resp: dict[str, Any] = client.embeddings(model=EMBED_MODEL, prompt=text)
    embedding = resp.get("embedding")
    if not embedding:
        raise RuntimeError("No embedding returned from Ollama embeddings()")
    return embedding


def main():
    if not RESUME_PATH.exists():
        raise FileNotFoundError(f"resume.txt not found at: {RESUME_PATH}")

    raw = RESUME_PATH.read_text(encoding="utf-8", errors="ignore")
    chunks = chunk_text_section_aware(raw, max_chars=MAX_CHARS)

    ollama = Client(host=OLLAMA_HOST)

    Path(CHROMA_PATH).mkdir(parents=True, exist_ok=True)
    chroma = chromadb.PersistentClient(path=CHROMA_PATH)

    # Rebuildable DB: wipe collection each run
    try:
        chroma.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass
    collection = chroma.get_or_create_collection(name=COLLECTION_NAME)

    ids = [f"resume-{i:04d}" for i in range(len(chunks))]
    metas = [{"source": "resume.txt", "chunk": i} for i in range(len(chunks))]
    embs = [embed_text(ollama, c) for c in chunks]

    collection.add(ids=ids, documents=chunks, metadatas=metas, embeddings=embs)
    print(f"✅ Embedded {len(chunks)} chunks into '{COLLECTION_NAME}' at '{CHROMA_PATH}'")


if __name__ == "__main__":
    main()
