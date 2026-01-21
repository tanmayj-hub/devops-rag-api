# RAG API with FastAPI + Chroma + Ollama (Local + Docker + Kubernetes)

A **Retrieval-Augmented Generation (RAG)** API built with **FastAPI**, **ChromaDB**, and **Ollama**.  
It answers questions by retrieving relevant chunks from a **public knowledge source** (`resume.txt`) and generating an answer with a local LLM.

This repo is part of a 4-part DevOps × AI series:
- ✅ Project 1: Run locally (FastAPI + Chroma + Ollama)
- ✅ Project 2: Containerize with Docker
- ✅ Project 3: Deploy to Kubernetes (Minikube)
- ⏳ Project 4: Automate testing with GitHub Actions

---

## What this project demonstrates
- Building an API with **FastAPI**
- Chunking + embedding a document into a local vector DB (**ChromaDB**)
- Using **Ollama** for:
  - **Embeddings:** `nomic-embed-text`
  - **Generation:** `qwen2.5:1.5b`
- Rebuildable workflow (delete `db/` and re-ingest anytime)
- Optional debug mode to inspect retrieval quality (`debug=true`)

---

## Repo structure

```text
.
├── app.py                 # FastAPI app (POST /query)
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

Verify Ollama is up:

```bash
curl http://localhost:11434
```

Pull the required models:

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

---

## Test with curl

Basic query:

```bash
curl -s -X POST "http://127.0.0.1:8000/query?q=What%20is%20my%20name%3F" | python -m json.tool
```

Debug mode:

```bash
curl -s -X POST "http://127.0.0.1:8000/query?q=What%20is%20my%20name%3F&debug=true" | python -m json.tool
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
curl -s -X POST "http://127.0.0.1:8000/query?q=What%20is%20my%20name%3F" | python -m json.tool
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

This runs **everything inside Kubernetes**:

* **Ollama** service (`ollama:11434`)
* **RAG API** service (`rag-api:8000`) calling Ollama via Kubernetes DNS

## Why this approach?

* **Simple + repeatable:** `kubectl apply -f k8s/` recreates the stack
* **Production-aligned:** service discovery (`http://ollama:11434`) — no host hacks
* **Models persist:** Ollama models stored on a **PVC**
* **DB is rebuildable (NOT persistent):** Chroma DB is rebuilt automatically at pod start by an **initContainer** (no embed Job needed)

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

> The `rag-api` pod will only become Ready after its initContainer finishes running `python embed.py`.

---

## 4) One-time setup: Pull Ollama models (Job)

This pulls:

* `qwen2.5:1.5b` (generation)
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
curl -s -X POST "http://127.0.0.1:8000/query?q=What%20is%20my%20name%3F" | python -m json.tool
```

Debug:

```bash
curl -s -X POST "http://127.0.0.1:8000/query?q=What%20is%20my%20name%3F&debug=true" | python -m json.tool
```

---

## Rebuild-from-scratch (Kubernetes)

Delete the namespace (removes Deployments/Services/Pods/Jobs):

```bash
kubectl delete namespace rag
```

Recreate:

```bash
kubectl apply -f k8s/
kubectl apply -f k8s/jobs/01-pull-models-job.yaml
```

---

## Stop Minikube (optional)

```bash
minikube stop
```

---

## Roadmap (Next Project)

### Project 4 — GitHub Actions

* CI: lint/test on push + PR
* Build Docker image in CI
* Optional: rerun ingestion when `resume.txt` changes

---

## License

MIT — see `LICENSE`.