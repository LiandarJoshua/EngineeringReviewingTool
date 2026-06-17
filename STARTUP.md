# Engineering Review Platform — Startup Guide

## Prerequisites (one-time setup)
- Docker Desktop installed and running
- [ngrok](https://ngrok.com/download) installed
- Ollama installed ([ollama.com/download](https://ollama.com/download))

---

## Every Time You Start

### 1. Start Ollama (if not already running)
Open a terminal and run:
```
ollama serve
```
Verify models are available:
```
ollama list
```
You should see: `qwen2.5-coder:7b`, `mistral:7b`, `nomic-embed-text`

If any are missing, pull them:
```
ollama pull qwen2.5-coder:7b
ollama pull mistral:7b
ollama pull nomic-embed-text
```

---

### 2. Start Docker Desktop
Open Docker Desktop from the Start menu and wait until it says **"Engine running"**.

---

### 3. Start All Services
```
cd engineering-review-platform
docker compose up -d
```

Wait ~20 seconds for all services to be healthy.

**Verify everything is running:**
```
docker compose ps
```
You should see 8 containers with status `Up`:
- `postgres`
- `redis`
- `chromadb`
- `neo4j`
- `minio`
- `langfuse`
- `api`
- `celery_worker`
- `frontend`
- `nginx`

---

### 4. Start ngrok (for GitHub webhook auto-triggering)
Open a **separate terminal** and run:
```
ngrok http 8000
```
Copy the `https://xxxx.ngrok-free.app` URL.

Go to your GitHub repo → **Settings → Webhooks** → Add/Edit webhook:
- **Payload URL:** `https://xxxx.ngrok-free.app/webhooks/github`
- **Content type:** `application/json`
- **Events:** Select **"Let me select individual events"** and enable:
  - ✅ Pull requests
  - ✅ Pushes
  - ✅ Issue comments

> ngrok URL changes every session on the free plan — update the webhook each time.

**Automation triggers active after this:**

| Event | What happens |
|-------|-------------|
| PR opened / updated | Full PIV review → inline comments on PR |
| PR merged | Full 11-stage repo health review queued |
| Push to main/master | Security + logic scan → ✅/❌ commit status |
| Comment `/review` on PR | Re-review with all 4 skills |
| Comment `/review security` | Security scan only |
| Comment `/review style` | Style check only |
| Comment `/review logic` | Logic & bug review only |
| Comment `/review tests` | Test coverage check only |

---

## Access Points

| Service | URL | Notes |
|---------|-----|-------|
| Frontend UI | http://localhost:3000 | Main app |
| API | http://localhost:8000 | REST API |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Langfuse | http://localhost:3001 | Observability — login: `admin@local.dev` / `Admin1234!` |
| Neo4j Browser | http://localhost:7474 | Graph DB — login: `neo4j` / `changeme_local` |
| MinIO Console | http://localhost:9001 | Object storage — login: `minioadmin` / `changeme_local` |
| ChromaDB | http://localhost:8001 | Vector DB |

---

## Key Workflows

### Run a Full Repo Review
1. Go to http://localhost:3000
2. Click **New Review**
3. Enter a GitHub repo URL + your email
4. Watch the 11-stage pipeline run live
5. View report at Review Detail → tabs: Overview, Security, Architecture, Findings, Coaching

### Trigger a PR Review Manually
1. Go to http://localhost:3000/pr-reviews
2. Fill in: repo (`owner/repo`), PR number, head SHA, GitHub PAT
3. Click **Trigger PR Review**
4. Results appear as comments on the GitHub PR in ~2-3 minutes

### Get PR Head SHA
```
# Replace with your repo and PR number
curl -H "Authorization: Bearer YOUR_GITHUB_TOKEN" \
  https://api.github.com/repos/OWNER/REPO/pulls/PR_NUMBER \
  | grep '"sha"' | head -1
```
Or check the Commits tab on the PR page.

---

## Stopping Everything
```
cd C:\Users\joshu\Momus\engineering-review-platform
docker compose down
```
Data is preserved in Docker volumes — safe to stop and restart anytime.

---

## Troubleshooting

**API not responding:**
```
docker compose logs api --tail=20
```

**Celery worker not processing tasks:**
```
docker compose logs celery_worker --tail=20
```

**Langfuse not loading:**
```
docker compose restart langfuse
```

**Ollama connection errors (models not responding):**
- Make sure `ollama serve` is running on the host
- Test: `curl http://localhost:11434/api/tags`

**Disk space running low:**
```
docker system prune --volumes -f
```
> Safe — only removes unused/orphaned containers, images, and volumes.

**Rebuild a specific service after code changes:**
```
docker compose build frontend
docker compose up -d frontend
```

**Full rebuild (after requirements.txt changes):**
```
docker compose build --no-cache api
docker compose up -d api celery_worker
```

---

## GitHub Actions (Automatic PR Review)
Copy `.github/workflows/ai-review.yml` into any repo.
Add repository secret `REVIEW_API_URL` = your ngrok URL.
The workflow fires automatically on every PR open/update.

---

## Environment Variables
All config is in `.env` at the project root.
Key vars to keep updated:
- `GITHUB_TOKEN` — PAT for posting PR review comments
- `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` — from Langfuse dashboard
- `GITHUB_WEBHOOK_SECRET` — must match what's set in GitHub webhook settings
