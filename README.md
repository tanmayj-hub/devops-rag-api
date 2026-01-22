# RAG API with FastAPI + Chroma + Ollama (Local + Docker + Kubernetes + CI)

A **Retrieval-Augmented Generation (RAG)** API built with **FastAPI**, **ChromaDB**, and **Ollama**.  
It answers questions by retrieving relevant chunks from a **public knowledge source** (`resume.txt`) and generating/extracting an answer with a local LLM.

This repo is part of a 4-part DevOps × AI series:
- ✅ Project 1: Run locally (FastAPI + Chroma + Ollama)
- ✅ Project 2: Containerize with Docker
- ✅ Project 3: Deploy to Kubernetes (Minikube)
- ✅ Project 4: Automate testing with GitHub Actions (PR tests + main tests)

---

## What this project demonstrates
- Building an API with **FastAPI**
- Chunking + embedding a document into a local vector DB (**ChromaDB**)
- Using **Ollama** for:
  - **Embeddings:** `nomic-embed-text`
  - **Generation/Extraction:** `qwen2.5:1.5b`
- Rebuildable workflow (delete `db/` and re-ingest anytime)
- Optional debug mode to inspect retrieval quality (`debug=true`)
- CI design that separates:
  - **Deterministic retrieval checks** on PRs
  - **End-to-end semantic extraction checks** on merges to `main`

---

## Repo structure

```text
.
├── app.py                 # FastAPI app (POST /query, GET /health)
├── embed.py               # Ingestion: chunk + embed resume.txt into Chroma
├── resume.txt             # Public knowledge source (intentionally committed)
├── requirements.txt       # Runtime dependencies
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── README.md
├── LICENSE
├── .gitignore
├── k8s/                   # Kubernetes manifests (Project 3)
│   ├── 00-namespace.yaml
│   ├── 01-ollama-pvc.yaml
│   ├── 02-ollama-deploy-svc.yaml
│   ├── 03-rag-deploy-svc.yaml
│   └── jobs/
│       └── 01-pull-models-job.yaml
├── tests/
│   ├── semantic_cases.json          # End-to-end expected outputs (LLM extraction)
│   ├── run_semantic_tests.py        # End-to-end test runner
│   ├── retrieval_cases.json         # NextWork-style retrieval assertions
│   └── run_retrieval_tests.py       # Retrieval test runner (mock mode)
└── db/                    # Created locally by Chroma (ignored by git)
````

> Note: `db/` is intentionally ignored by git so the vector store is rebuildable from scratch.

---

# Option A — Run locally (Project 1)

## Prerequisites

### 1) Python

Recommended: **Python 3.12.x**

```bash
python --version
```

### 2) Ollama

Install (Windows):

```bash
winget install -e --id Ollama.Ollama
```

Start Ollama:

```bash
ollama serve
```

Verify:

```bash
curl http://localhost:11434
```

Pull required models:

```bash
ollama pull qwen2.5:1.5b
ollama pull nomic-embed-text
```

---

## Setup (Windows - Git Bash)

```bash
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

---

## Build embeddings (ingest the knowledge base)

Creates the local Chroma DB under `./db`:

```bash
python embed.py
```

---

## Run the API

```bash
uvicorn app:app --reload
```

Swagger UI:

* [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Health:

```bash
curl http://127.0.0.1:8000/health
```

---

## Test with curl

Notes:

* This API extracts answers from `resume.txt` (it’s not a general chatbot).
* If the answer isn’t present in `resume.txt`, the API returns `NOT_FOUND` (expected).
* If your machine is slower, add `-m 120` to curl to avoid timeouts.

Basic query:

```bash
curl -sS -m 120 -X POST "http://127.0.0.1:8000/query?q=What%20is%20my%20name%3F" | python -m json.tool
```

Debug mode:

```bash
curl -sS -m 120 -X POST "http://127.0.0.1:8000/query?q=What%20is%20my%20name%3F&debug=true" | python -m json.tool
```

---

# Option B — Run with Docker (Project 2)

This runs the project as **two containers**:

* `ollama` container: runs Ollama (port `11434`) and stores models in a Docker volume
* `rag-api` container: runs FastAPI (port `8000`) and calls Ollama over the Docker network

## Prerequisites

* Docker Desktop installed + running

Verify Docker:

```bash
docker run hello-world
```

---

## Start the stack (build + run)

```bash
docker compose up --build
```

---

## Pull required Ollama models (first time only)

In a second terminal:

```bash
docker compose exec ollama ollama pull qwen2.5:1.5b
docker compose exec ollama ollama pull nomic-embed-text
```

---

## Build embeddings (ingest) inside Docker

```bash
docker compose exec rag-api python embed.py
```

> By default, Chroma writes to `./db` inside the `rag-api` container filesystem.
> If you run `docker compose down`, the `rag-api` container is removed and the DB is deleted (rebuildable by rerunning embed).

---

## Test the API (host machine)

Swagger UI:

* [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Example curl:

```bash
curl -sS -m 120 -X POST "http://127.0.0.1:8000/query?q=What%20is%20my%20name%3F" | python -m json.tool
```

---

## Stop

```bash
docker compose down
```

Full cleanup (removes Ollama model cache volume too):

```bash
docker compose down -v
```

---

# Option C — Run on Kubernetes with Minikube (Project 3)

This runs everything inside Kubernetes:

* **Ollama** service (`ollama:11434`)
* **RAG API** service (`rag-api:8000`) calling Ollama via Kubernetes DNS

## Why this approach?

* Simple + repeatable: `kubectl apply -f k8s/` recreates the stack
* Production-aligned: service discovery (`http://ollama:11434`) — no host hacks
* Models persist: Ollama models stored on a **PVC**
* DB is rebuildable (NOT persistent): Chroma DB is rebuilt automatically at pod start by an **initContainer**

---

## Prerequisites

* Docker Desktop installed + running
* Minikube + kubectl installed

Verify:

```bash
minikube version
kubectl version --client
docker run hello-world
```

---

## 1) Start Minikube

```bash
minikube start
kubectl get nodes
```

---

## 2) Build your RAG API image and load it into Minikube

From repo root:

```bash
docker build -t devops-rag-api-rag-api:latest .
minikube image load devops-rag-api-rag-api:latest
```

---

## 3) Deploy Ollama + RAG API

```bash
kubectl apply -f k8s/
kubectl get pods -n rag
kubectl get svc -n rag
```

> The `rag-api` pod becomes Ready after its initContainer finishes running `python embed.py`.

---

## 4) One-time setup: Pull Ollama models (Job)

This pulls:

* `qwen2.5:1.5b` (generation/extraction)
* `nomic-embed-text` (embeddings)

```bash
kubectl apply -f k8s/jobs/01-pull-models-job.yaml
kubectl logs -n rag job/ollama-pull-models -f
```

---

## 5) Access and test the API (port-forward)

```bash
kubectl port-forward -n rag svc/rag-api 8000:8000
```

Swagger UI:

* [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Example curl:

```bash
curl -sS -m 120 -X POST "http://127.0.0.1:8000/query?q=What%20is%20my%20name%3F" | python -m json.tool
```

Debug:

```bash
curl -sS -m 120 -X POST "http://127.0.0.1:8000/query?q=What%20is%20my%20name%3F&debug=true" | python -m json.tool
```

---

# Project 4 — Automated Testing with GitHub Actions (CI)

This repo includes **two CI workflows**:

## 1) PR / Branch CI: Deterministic Retrieval Tests (NextWork-style)

**Workflow:** `.github/workflows/ci-retrieval-mock.yml`
**Triggers:** `pull_request` and `push` (all branches except `main`)
**Mode:** `USE_MOCK_LLM=1`

What it validates:

* Embeddings are built successfully
* Chroma retrieval returns the expected **context**
* Tests are deterministic (no LLM output randomness)

How it works:

* Starts Ollama
* Pulls **only** `nomic-embed-text` (embeddings)
* Runs `embed.py` to create the vector DB
* Starts the API in **mock mode** (`USE_MOCK_LLM=1`)
* Runs: `python tests/run_retrieval_tests.py http://localhost:8000`

### Run retrieval tests locally (Docker Compose)

```bash
docker compose up -d ollama
docker compose exec ollama ollama pull nomic-embed-text

USE_MOCK_LLM=1 docker compose up -d --build rag-api
docker compose exec rag-api python embed.py
docker compose restart rag-api

python tests/run_retrieval_tests.py http://localhost:8000
```

---

## 2) Main CI: End-to-End Semantic Extraction Tests (Your tests)

**Workflow:** `.github/workflows/ci-semantic.yml`
**Triggers:** push to `main` (and manual `workflow_dispatch`)
**Mode:** normal production mode (`USE_MOCK_LLM=0`)

What it validates:

* Full end-to-end pipeline:

  * retrieval + LLM extraction output
* Regression protection for prompt/model changes

How it works:

* Starts Ollama
* Pulls both models:

  * `nomic-embed-text` (embeddings)
  * `qwen2.5:1.5b` (generation/extraction)
* Starts the API
* Runs ingestion (`embed.py`)
* Runs: `python tests/run_semantic_tests.py http://localhost:8000`

### Run end-to-end semantic tests locally (Docker Compose)

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

## What is Mock LLM mode?

Mock mode returns the **retrieved context** directly instead of calling the LLM.

* Production mode (`USE_MOCK_LLM=0`): uses Ollama generation/extraction
* Mock mode (`USE_MOCK_LLM=1`): returns retrieved text for deterministic tests

Why it matters:

* LLM outputs can be non-deterministic
* CI must be deterministic to be trusted on PRs

---

# Fork-and-Replicate Guide (Project 4)

If you fork this repo and want to replicate Project 4:

1. Fork the repo on GitHub (Actions should be enabled by default on your fork)
2. Clone your fork:

```bash
git clone <your-fork-url>
cd devops-rag-api
```

3. Create a feature branch:

```bash
git checkout -b feature/my-change
```

4. Make a change and push:

```bash
git add .
git commit -m "My change"
git push -u origin feature/my-change
```

5. Open a Pull Request into `main`:

* The **PR workflow** runs automatically (mock retrieval tests).
* When you merge the PR, the **main workflow** runs automatically (end-to-end semantic tests).

Optional (recommended): add branch protection for `main` so merges require the PR workflow to pass.

---

## License

MIT — see `LICENSE`.
