# RAG API with FastAPI + Chroma + Ollama (Local + Docker + Kubernetes + CI)

A **Retrieval-Augmented Generation (RAG)** API built with **FastAPI**, **ChromaDB**, and **Ollama**.  
It answers questions by retrieving relevant chunks from a **public knowledge source** (`resume.txt`) and generating/extracting an answer with a local LLM.

This repo is part of a 4-part DevOps × AI series:
- ✅ Project 1: Run locally (FastAPI + Chroma + Ollama)
- ✅ Project 2: Containerize with Docker
- ✅ Project 3: Deploy to Kubernetes (Minikube)
- ✅ Project 4: Automate testing with GitHub Actions (CI)

---

## What this project demonstrates
- Building an API with **FastAPI**
- Chunking + embedding a document into a local vector DB (**ChromaDB**)
- Using **Ollama** for:
  - **Embeddings:** `nomic-embed-text`
  - **Generation/Extraction:** `qwen2.5:1.5b`
- Rebuildable workflow (delete `db/` and re-ingest anytime)
- A practical CI setup with **two workflows**:
  - **Fast, deterministic retrieval tests** for pull requests
  - **Full end-to-end tests** on merges to `main`

---

## Project 1 — Run locally

### Prerequisites
- Python 3.12.x recommended
- Ollama installed and running

Pull models:
```bash
ollama pull nomic-embed-text
ollama pull qwen2.5:1.5b
````

### Setup

```bash
python -m venv venv
# Windows (PowerShell)
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate

pip install -r requirements.txt
```

### Build embeddings

This creates the local Chroma DB in `./db` (ignored by git):

```bash
python embed.py
```

### Run the API

```bash
uvicorn app:app --reload
```

### Test

Health:

```bash
curl http://127.0.0.1:8000/health
```

Query:

```bash
curl -sS -m 120 -X POST "http://127.0.0.1:8000/query?q=What%20is%20my%20name%3F" | python -m json.tool
```

Debug:

```bash
curl -sS -m 120 -X POST "http://127.0.0.1:8000/query?q=What%20is%20my%20name%3F&debug=true" | python -m json.tool
```

---

## Project 2 — Containerize with Docker

### Prerequisites

* Docker Desktop installed and running

### Start containers

```bash
docker compose up --build
```

### Pull models (first time only)

In a second terminal:

```bash
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama pull qwen2.5:1.5b
```

### Build embeddings (inside container)

```bash
docker compose exec rag-api python embed.py
```

### Test

```bash
curl -sS -m 120 -X POST "http://127.0.0.1:8000/query?q=What%20is%20my%20name%3F" | python -m json.tool
```

### Stop

```bash
docker compose down
```

Full cleanup (removes Ollama model volume too):

```bash
docker compose down -v
```

---

## Project 3 — Deploy to Kubernetes (Minikube)

### Prerequisites

* Minikube + kubectl installed
* Docker Desktop running

### Start Minikube

```bash
minikube start
kubectl get nodes
```

### Build and load the API image into Minikube

```bash
docker build -t devops-rag-api-rag-api:latest .
minikube image load devops-rag-api-rag-api:latest
```

### Deploy resources

```bash
kubectl apply -f k8s/
kubectl get pods -n rag
kubectl get svc -n rag
```

### Pull Ollama models (Job)

```bash
kubectl apply -f k8s/jobs/01-pull-models-job.yaml
kubectl logs -n rag job/ollama-pull-models -f
```

### Access the API

```bash
kubectl port-forward -n rag svc/rag-api 8000:8000
```

Test:

```bash
curl -sS -m 120 -X POST "http://127.0.0.1:8000/query?q=What%20is%20my%20name%3F" | python -m json.tool
```

---

## Project 4 — Automate testing with GitHub Actions (CI)

This repo includes two automated workflows:

1. **Pull request / branch workflow (fast + deterministic)**

   * Runs retrieval tests in **mock mode** (`USE_MOCK_LLM=1`)
   * In mock mode, the API returns the **retrieved context** directly instead of calling the LLM
   * This makes results stable and suitable for CI on every PR

2. **Main branch workflow (end-to-end)**

   * Runs full semantic extraction tests using the real LLM
   * This validates the complete pipeline (retrieve + generate/extract) after code is merged to `main`

### Mock mode (deterministic retrieval testing)

* **Production mode:** `USE_MOCK_LLM=0` (default) → uses Ollama generation/extraction
* **Mock mode:** `USE_MOCK_LLM=1` → returns retrieved context directly

### Run the deterministic retrieval tests locally

```bash
docker compose up -d ollama
docker compose exec ollama ollama pull nomic-embed-text

USE_MOCK_LLM=1 docker compose up -d --build rag-api
docker compose exec rag-api python embed.py
docker compose restart rag-api

python tests/run_retrieval_tests.py http://localhost:8000
```

### Run the full end-to-end semantic tests locally

```bash
docker compose up -d ollama
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama pull qwen2.5:1.5b

docker compose up -d --build rag-api
docker compose exec rag-api python embed.py
docker compose restart rag-api

python tests/run_semantic_tests.py http://localhost:8000
```

---

## Notes

* `db/` is ignored by git and should be rebuilt using `python embed.py`
* `resume.txt` is intentionally committed and acts as the public knowledge base
* If curl times out on slower machines, use `-m 120`

---

## License

MIT — see `LICENSE`.
