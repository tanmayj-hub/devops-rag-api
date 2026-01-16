from fastapi import FastAPI, Query
import chromadb
import ollama

app = FastAPI()

# Chroma setup
chroma = chromadb.PersistentClient(path="./db")
collection = chroma.get_or_create_collection("docs")

# Models
EMBED_MODEL = "nomic-embed-text"   # make sure: ollama pull nomic-embed-text
LLM_MODEL = "tinyllama"

def embed(text: str) -> list[float]:
    """Create an embedding for the given text using Ollama."""
    resp = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return resp["embedding"]

@app.post("/query")
def query(
    q: str = Query(..., description="User question"),
    debug: bool = Query(False, description="Return retrieval debug info")
):
    # 1) Embed the query
    q_emb = embed(q)

    # 2) Retrieve top-k relevant chunks
    results = collection.query(
        query_embeddings=[q_emb],
        n_results=3,
        include=["documents", "metadatas", "distances"]
    )

    docs = results.get("documents", [[]])[0]
    context = "\n\n---\n\n".join(docs) if docs else ""

    # 3) Strict extraction prompt: return only the value, verbatim
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

    llm_resp = ollama.generate(
        model=LLM_MODEL,
        prompt=prompt,
        options={
            "temperature": 0
        }
    )

    answer = (llm_resp.get("response") or "").strip()

    # Optional: normalize common unwanted formatting (still keep it strict)
    # e.g., strip surrounding quotes if the model adds them
    if answer.startswith('"') and answer.endswith('"') and len(answer) >= 2:
        answer = answer[1:-1].strip()

    payload = {"answer": answer}

    if debug:
        payload["results"] = results

    return payload
