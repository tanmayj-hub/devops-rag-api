import os
import shutil
import chromadb
import ollama

DB_PATH = "./db"
COLLECTION_NAME = "docs"
EMBED_MODEL = "nomic-embed-text"   # or "mxbai-embed-large"

def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    text = text.replace("\r\n", "\n")
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
        if start < 0:
            start = 0
        if end == len(text):
            break
    return chunks

def embed(text: str) -> list[float]:
    resp = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return resp["embedding"]

# OPTIONAL: rebuild DB from scratch for consistency
if os.path.exists(DB_PATH):
    shutil.rmtree(DB_PATH)

client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection(COLLECTION_NAME)

with open("resume.txt", "r", encoding="utf-8") as f:
    text = f.read()

chunks = chunk_text(text)

ids = [f"resume-{i:04d}" for i in range(len(chunks))]
embeddings = [embed(c) for c in chunks]

collection.add(
    ids=ids,
    documents=chunks,
    embeddings=embeddings,
    metadatas=[{"source": "resume.txt", "chunk": i} for i in range(len(chunks))]
)

print(f"Stored {len(chunks)} chunks + embeddings in Chroma.")
