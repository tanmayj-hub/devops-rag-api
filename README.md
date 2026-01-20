# RAG API with FastAPI + Chroma + Ollama (Local + Docker)

A **Retrieval-Augmented Generation (RAG)** API built with **FastAPI**, **ChromaDB**, and **Ollama**.  
It answers questions by retrieving relevant chunks from a **public knowledge source** (`resume.txt`) and generating an answer with a local LLM.

This repo is part of a 4-part DevOps × AI series:
- ✅ Project 1: Run locally (FastAPI + Chroma + Ollama)
- ✅ Project 2: Containerize with Docker
- ⏳ Project 3: Deploy to Kubernetes
- ⏳ Project 4: Automate testing with GitHub Actions

---

## What this project demonstrates
- Building an API with **FastAPI**
- Chunking + embedding a document into a local vector DB (**ChromaDB**)
- Using **Ollama** for:
  - **Embeddings:** `nomic-embed-text`
  - **Generation:** `tinyllama`
- Rebuildable workflow (delete `db/` and re-ingest anytime)
- Optional debug mode to inspect retrieval quality (`debug=true`)

---

## Repo structure

```text
.
├── app.py            # FastAPI app (POST /query)
├── embed.py          # Ingestion: chunk + embed resume.txt into Chroma
├── resume.txt        # Public knowledge source (intentionally committed)
├── requirements.txt  # Runtime dependencies
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── README.md
├── LICENSE
├── .gitignore
└── db/               # Created locally by Chroma (ignored by git)
````

> Note: `db/` is intentionally ignored by git so the vector store is always rebuildable from scratch.

---

# Option A — Run locally (Project 1)

## Prerequisites

### 1) Python

Recommended: **Python 3.12.x**

Check:

```bash
python --version
```

### 2) Ollama

Install (Windows):

```bash
winget install -e --id Ollama.Ollama
```

Start Ollama (if not already running):

```bash
ollama serve
```

Verify Ollama is up:

```bash
curl http://localhost:11434
```

Pull the required models:

```bash
ollama pull tinyllama
ollama pull nomic-embed-text
```

---

## Setup (Windows - Git Bash)

From the repo root:

### 1) Create + activate a virtual environment

```bash
python -m venv venv
source venv/Scripts/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

---

## Build embeddings (ingest the knowledge base)

Run ingestion to create the local Chroma DB under `./db`:

```bash
python embed.py
```

This will:

* read and chunk `resume.txt`
* create embeddings using `nomic-embed-text` via Ollama
* store embeddings in Chroma under `db/`

---

## Run the API

Start the FastAPI server:

```bash
uvicorn app:app --reload
```

Open Swagger UI:

* [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Test with curl

Basic query:

```bash
curl -s -X POST "http://127.0.0.1:8000/query?q=What%20is%20my%20name%3F" | python -m json.tool
```

Query with retrieval debug info:

```bash
curl -s -X POST "http://127.0.0.1:8000/query?q=What%20is%20my%20name%3F&debug=true" | python -m json.tool
```

---

# Option B — Run with Docker (Project 2)

This runs the project as **two containers**:

* `ollama` container: runs the Ollama model server (port `11434`) and stores models in a Docker volume
* `rag-api` container: runs the FastAPI API (port `8000`) and calls Ollama over the Docker network

## Prerequisites

* Docker Desktop installed + running

Verify Docker:

```bash
docker run hello-world
```

## Start the stack (build + run)

From the repo root:

```bash
docker compose up --build
```

This will:

* build the `rag-api` image using the `Dockerfile`
* pull the `ollama/ollama` image if needed
* start both containers on a shared Docker network

## Pull required Ollama models (first time only)

In a second terminal:

```bash
docker compose exec ollama ollama pull tinyllama
docker compose exec ollama ollama pull nomic-embed-text
```

> These models are stored in a Docker volume mounted to the `ollama` container, so you don’t need to re-download them every time.

## Build embeddings (ingest) inside Docker

```bash
docker compose exec rag-api python embed.py
```

### Where is the Chroma DB in this Docker setup?

By default (with the current compose file), Chroma writes to `./db` **inside the `rag-api` container filesystem**.

* If you run `docker compose down`, the `rag-api` container is removed and the DB is **deleted**.
* Ollama models persist unless you delete volumes.

## Test the API (host machine)

Swagger UI:

* [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Example curl:

```bash
curl -s -X POST "http://127.0.0.1:8000/query?q=What%20is%20my%20name%3F" | python -m json.tool
```

## Stop

```bash
docker compose down
```

## Full cleanup (removes Ollama model cache volume too)

⚠️ This will delete downloaded Ollama models:

```bash
docker compose down -v
```

---

## Rebuild-from-scratch behavior (important)

This project is designed so the Chroma DB is always rebuildable:

* `db/` is ignored by git
* delete `db/` and re-run ingestion to rebuild from scratch

Local rebuild:

```bash
rm -rf db
python embed.py
```

Windows PowerShell alternative:

```powershell
Remove-Item -Recurse -Force db
python embed.py
```

Docker rebuild (DB lives inside the container by default):

```bash
docker compose down
docker compose up --build
docker compose exec ollama ollama pull tinyllama
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec rag-api python embed.py
```

---

## Roadmap (Next Projects)

### Project 3 — Kubernetes

* Add manifests under `deploy/k8s/`
* Deploy the API and Ollama as separate workloads
* Add readiness/liveness probes + service exposure

### Project 4 — GitHub Actions

* CI: lint/test on push + PR
* Build Docker image in CI
* Optional: trigger re-ingestion when `resume.txt` changes

---

## License

MIT — see `LICENSE`.