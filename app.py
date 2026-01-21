import os
from typing import Any

import chromadb
from fastapi import FastAPI, Query
from ollama import Client

app = FastAPI()

# --- Config (K8s-friendly) ---
CHROMA_PATH = os.getenv("CHROMA_PATH", "./db")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:1.5b")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "docs")

TOP_K = int(os.getenv("TOP_K", "5"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "64"))

ollama = Client(host=OLLAMA_HOST)

chroma = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma.get_or_create_collection(name=COLLECTION_NAME)


def embed_text(text: str) -> list[float]:
    resp: dict[str, Any] = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    embedding = resp.get("embedding")
    if not embedding:
        raise RuntimeError("No embedding returned from Ollama embeddings()")
    return embedding


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query")
def query(
    q: str = Query(..., min_length=1, description="User question"),
    debug: bool = Query(False, description="Return retrieval debug info"),
):
    q_emb = embed_text(q)

    results = collection.query(
        query_embeddings=[q_emb],
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"],
    )

    docs = (results.get("documents") or [[]])[0]
    context = "\n\n---\n\n".join(docs) if docs else ""

    # If nothing retrieved, don't call the LLM
    if not context.strip():
        payload: dict[str, Any] = {"answer": "NOT_FOUND"}
        if debug:
            payload["debug"] = {
                "reason": "empty_context",
                "ollama_host": OLLAMA_HOST,
                "chroma_path": CHROMA_PATH,
                "collection": COLLECTION_NAME,
                "results": results,
            }
        return payload

    prompt = f"""You are an information extraction system.

Rules:
- Use ONLY the provided context.
- Return ONLY the extracted answer value.
- Copy the answer EXACTLY as it appears in the context (verbatim). Do not rephrase. Do not correct spelling.
- Do not add any extra words, labels, punctuation, or explanations.
- If the answer is not explicitly present in the context, return exactly: NOT_FOUND

Context:
{context}

Question: {q}

Extracted value:"""

    llm_resp: dict[str, Any] = ollama.generate(
        model=LLM_MODEL,
        prompt=prompt,
        options={
            "temperature": 0,
            "num_predict": MAX_TOKENS,
            "stop": ["\n\n", "\nRules:", "\nContext:", "\nQuestion:"],
        },
    )

    answer = (llm_resp.get("response") or "").strip()

    if answer.startswith('"') and answer.endswith('"') and len(answer) >= 2:
        answer = answer[1:-1].strip()

    # Prompt-echo guard
    bad_markers = ("rules:", "context:", "question:", "information extraction system")
    if any(m in answer.lower() for m in bad_markers):
        answer = "NOT_FOUND"

    if not answer:
        answer = "NOT_FOUND"

    payload: dict[str, Any] = {"answer": answer}
    if debug:
        payload["debug"] = {
            "ollama_host": OLLAMA_HOST,
            "chroma_path": CHROMA_PATH,
            "embed_model": EMBED_MODEL,
            "llm_model": LLM_MODEL,
            "collection": COLLECTION_NAME,
            "top_k": TOP_K,
            "results": results,
        }
    return payload
