# RAG API with FastAPI + Chroma + Ollama (Local)

A **Retrieval-Augmented Generation (RAG)** API built with **FastAPI**, **ChromaDB**, and **Ollama**.  
It answers questions by retrieving relevant chunks from a **public knowledge source** (`resume.txt`) and generating an answer with a local LLM.

## 4-part DevOps × AI roadmap
- [x] Project 1 — Run the RAG API locally (this repo state)
- [ ] Project 2 — Containerize with Docker
- [ ] Project 3 — Deploy to Kubernetes
- [ ] Project 4 — Automate testing with GitHub Actions

---

## What this project demonstrates
- Building an API with **FastAPI**
- Storing/searching embeddings in **ChromaDB**
- Using **Ollama** for:
  - **Embeddings** (example: `nomic-embed-text`)
  - **Generation** (example: `tinyllama`)
- Rebuildable local vector DB workflow (delete `db/` and re-ingest anytime)
- Optional debug mode to inspect retrieval quality (if implemented in `app.py`)

---

## Repo structure
- `app.py` — FastAPI app (query endpoint)
- `embed.py` — ingestion script: chunks `resume.txt`, generates embeddings, stores in `db/`
- `resume.txt` — public knowledge source (intentionally committed)
- `db/` — Chroma persistence (**NOT committed**, rebuildable)
- `venv/` — local virtualenv (**NOT committed**)

---

## Prerequisites

### Python
Recommended: **Python 3.12.x**

### Ollama (Windows)
Install:
```bash
winget install -e --id Ollama.Ollama
````

Start Ollama (if not already running):

```bash
ollama serve
```

Verify Ollama is up:

```bash
curl http://localhost:11434
```

Pull models (use the models your code expects; these are common defaults):

```bash
ollama pull tinyllama
ollama pull nomic-embed-text
```

---

## Setup (Windows - Git Bash)

### 1) Create + activate virtualenv

```bash
python -m venv venv
source venv/Scripts/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

---

## Build embeddings (ingest knowledge base)

Run ingestion to build Chroma DB locally:

```bash
python embed.py
```

### Rebuild-from-scratch (important)

This repo is designed so the Chroma DB is always rebuildable:

* `db/` is ignored by git
* delete `db/` to force a clean rebuild

```bash
rm -rf db
python embed.py
```

(Windows PowerShell alternative: `Remove-Item -Recurse -Force db`)

---

## Run the API

Start the server:

```bash
uvicorn app:app --reload
```

Swagger UI:

* [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Test with curl

Basic query (matches the pattern you tested earlier):

```bash
curl -s -X POST "http://127.0.0.1:8000/query?q=What%20is%20my%20name%3F" | python -m json.tool
```

If your API supports debug retrieval (optional), try:

```bash
curl -s -X POST "http://127.0.0.1:8000/query?q=What%20is%20my%20name%3F&debug=true" | python -m json.tool
```

---

## Project 2 — Docker (next)

Planned:

* Add `Dockerfile` + `.dockerignore`
* Build image: `docker build -t devops-rag-api .`
* Run API container: `docker run -p 8000:8000 devops-rag-api`
* Connect to Ollama via HTTP (host Ollama or separate container)

## Project 3 — Kubernetes (next)

Planned:

* Add manifests under `deploy/k8s/`
* Deploy API + optional persistence volume patterns
* Expose service and add health checks

## Project 4 — GitHub Actions (next)

Planned:

* CI: run tests/lint on push + PR
* Build Docker image in CI
* Optional: re-ingest trigger when `resume.txt` changes

---

## License

MIT — see `LICENSE`.

````