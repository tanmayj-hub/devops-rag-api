import os
from pathlib import Path
from typing import Any, Optional

import chromadb
from ollama import Client

CHROMA_PATH = os.getenv("CHROMA_PATH", "./db")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "docs")
MAX_CHARS = int(os.getenv("CHUNK_MAX_CHARS", "900"))

BASE_DIR = Path(__file__).resolve().parent
RESUME_PATH = Path(os.getenv("RESUME_PATH", str(BASE_DIR / "resume.txt")))


def is_section_header(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    # Treat uppercase-only headers like PROFILE, SUMMARY, CERTIFICATIONS, SKILLS, etc.
    return s.isupper() and len(s) >= 3


def split_sections(text: str) -> list[tuple[str, str]]:
    """
    Returns list of (section_name, section_text_including_header).
    """
    text = text.replace("\r\n", "\n").strip()
    lines = text.splitlines()

    sections: list[tuple[str, str]] = []
    current_section: Optional[str] = None
    buf: list[str] = []

    def flush():
        nonlocal buf, current_section
        if current_section is not None and buf:
            sections.append((current_section, "\n".join(buf).strip()))
        buf = []

    for line in lines:
        if is_section_header(line):
            flush()
            current_section = line.strip()
            buf = [line.strip()]
        else:
            # If no section header encountered yet, bucket into UNKNOWN
            if current_section is None:
                current_section = "UNKNOWN"
                buf = []
            buf.append(line)

    flush()
    return sections


def chunk_paragraphs(text: str, max_chars: int) -> list[str]:
    """
    Chunk within a section without merging across sections.
    Splits by blank-line paragraphs and packs until max_chars.
    """
    text = text.strip()
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


def clear_collection(collection) -> None:
    """
    Clear documents without deleting the collection itself (prevents stale handles).
    """
    try:
        existing = collection.get(include=[])
        ids = existing.get("ids") if existing else None
        if ids:
            collection.delete(ids=ids)
    except Exception:
        # If collection is empty or get/delete behaves differently, proceed safely.
        pass


def main():
    if not RESUME_PATH.exists():
        raise FileNotFoundError(f"resume.txt not found at: {RESUME_PATH}")

    raw = RESUME_PATH.read_text(encoding="utf-8", errors="ignore")

    # Build section-aware chunks + metadatas
    sections = split_sections(raw)

    chunks: list[str] = []
    metas: list[dict[str, Any]] = []

    chunk_idx = 0
    for section_name, section_text in sections:
        section_chunks = chunk_paragraphs(section_text, max_chars=MAX_CHARS)
        for part_idx, c in enumerate(section_chunks):
            chunks.append(c)
            metas.append(
                {
                    "source": "resume.txt",
                    "chunk": chunk_idx,
                    "section": section_name,
                    "section_part": part_idx,
                }
            )
            chunk_idx += 1

    ollama = Client(host=OLLAMA_HOST)

    Path(CHROMA_PATH).mkdir(parents=True, exist_ok=True)
    chroma = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma.get_or_create_collection(name=COLLECTION_NAME)

    # Rebuildable DB: clear docs each run (do NOT delete collection)
    clear_collection(collection)

    ids = [f"resume-{i:04d}" for i in range(len(chunks))]
    embs = [embed_text(ollama, c) for c in chunks]

    collection.add(ids=ids, documents=chunks, metadatas=metas, embeddings=embs)
    print(f"✅ Embedded {len(chunks)} chunks into '{COLLECTION_NAME}' at '{CHROMA_PATH}'")


if __name__ == "__main__":
    main()
