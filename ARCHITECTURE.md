# Engineering Review Platform — Architecture & Workflow Guide

## What This System Does

The Engineering Review Platform is an autonomous, multi-agent AI system that reviews code repositories and pull requests. You give it a GitHub repo URL, and 11 specialized AI agents work in sequence to analyze the code across 5 dimensions — security, architecture, scalability, testing, and technical debt — then generate a scored report and a personalized developer coaching plan.

It also integrates directly with GitHub: when a developer opens a pull request, the system automatically fetches the diff, runs a focused review, posts inline comments directly on the changed lines, and flags issues that need human attention before merging.

---

## High-Level Workflow

```
GitHub Repo URL
       │
       ▼
┌─────────────────────────────────────────────────────┐
│                   11-Stage Pipeline                  │
│                                                     │
│  Stage 1  → Clone repo, detect language/framework   │
│  Stage 2  → Parse code, build AST + graph           │
│  Stage 3  → Architecture analysis                   │
│  Stage 4  → Security scan (LLM + Semgrep + Bandit)  │
│  Stage 5  → Scalability analysis                    │
│  Stage 6  → Test quality analysis                   │
│  Stage 7  → Technical debt analysis                 │
│  Stage 8  → Requirements alignment (if PDF given)   │
│  Stage 9  → Generate coaching report                │
│  Stage 10 → Prioritize all findings                 │
│  Stage 11 → Synthesize final report + scores        │
└─────────────────────────────────────────────────────┘
       │
       ▼
  Scored Report (A/B/C/D grade)
  Inline Findings (security, arch, debt...)
  Coaching Plan (strengths, roadmap, this week's focus)
```

---

## Step-by-Step Workflow (Full Repo Review)

### Step 1 — User Submits a Repo
The user goes to the frontend at `http://localhost:3000`, clicks **New Review**, and enters:
- A GitHub repository URL
- Their email address
- Their experience level (junior / mid / senior / principal)
- Optionally uploads a requirements PDF

The frontend calls `POST /reviews/` on the FastAPI backend. The backend:
1. Creates a `User` record in PostgreSQL (or finds an existing one by email)
2. Creates a `Repository` record
3. Creates a `Review` record with status `pending`
4. Fires a **Celery task** (`run_review`) and returns a `review_id` immediately

### Step 2 — Celery Queues the Pipeline
The **Celery worker** picks up the task from the Redis job queue. It builds a **LangGraph DAG** (directed acyclic graph) — a structured pipeline where each node is one stage. LangGraph manages the state passing between nodes, ensuring each stage receives the outputs of all previous stages.

### Step 3 — Pipeline Executes (11 Stages)
Each stage runs in sequence, reading from and writing to a shared `ReviewState` dictionary.

### Step 4 — Real-Time Progress Updates
As each stage completes, the worker publishes a message to a **Redis pub/sub channel** (`progress:{review_id}`). The frontend has an open **WebSocket** connection listening on that channel. The progress tracker updates in real time — each of the 11 stages lights up green as it finishes.

### Step 5 — Results Saved
After all 11 stages complete, the worker saves everything to **PostgreSQL**:
- Scores (security, architecture, testing, scalability, debt, overall)
- All findings (with severity, file path, line number, recommendation)
- The full raw output as JSONB
- A developer progress snapshot (for tracking improvement over time)

### Step 6 — User Views the Report
The frontend fetches the completed review from `GET /reviews/{id}`. The report shows:
- A **Radar chart** with scores across all 5 dimensions
- A **grade** (A = 80+, B = 65+, C = 50+, D = below 50)
- **5 tabs**: Overview, Security, Architecture, All Findings, Coaching
- Filterable findings table sorted by severity
- A personalized coaching plan with strengths, improvements, and a learning roadmap

---

## PR Review Workflow (PIV Loop)

When a developer opens or updates a pull request on GitHub:

```
PR opened/updated
       │
       ▼
GitHub fires webhook → POST /webhooks/github
       │
       ▼
Celery queues run_pr_review task
       │
       ▼
Fetch PR diff + changed file contents from GitHub API
       │
       ▼
Build PR context (parse unified diff, extract added lines)
       │
       ▼
Run review agents on changed code only (not full repo)
       │
       ▼
Compute quality score (0-100)
       │
       ├─ Score ≥ 70 and no blockers → post COMMENT review
       │
       └─ Score < 70 or blockers → post REQUEST_CHANGES review
              │
              ▼
       Post inline comments on PR lines
       Post summary comment with grade + findings table
       Apply labels: ai:reviewed / ai:needs-human-review / ai:quality-gate-failed
       │
       ▼
Human engineer reviews AI comments, applies suggestions,
fixes blocking issues, removes label, then merges manually.
AI NEVER auto-merges. AI NEVER sends "Approve" event.
```

**Self-correction loop:** The pipeline runs up to 3 passes. If the quality score doesn't meet the threshold after each pass, the author can apply the suggested fixes and push again — the next push triggers another webhook and a fresh review cycle.

---

## The 11 Agents Explained

### Stage 1 — Ingestion
**What it does:** Clones the GitHub repository to a temp directory on disk using **GitPython**. Detects the tech stack by reading config files (`package.json`, `requirements.txt`, `pom.xml`, `go.mod`, etc.).

**Output:** `local_path` (where code lives on disk), `stack` (language, framework, package manager).

**Why it matters:** Every subsequent agent needs to know where the code is and what language it's written in to ask the right questions.

---

### Stage 2 — Code Mapping
**What it does:** Walks every source file and parses it with **Tree-sitter** — a fast, language-aware AST parser. For each file it extracts all functions, classes, and their line ranges. Computes a **complexity score** using the **Radon** library (cyclomatic complexity). Stores two indexes:
- **ChromaDB** — vector embeddings of every function/class for semantic search (RAG)
- **Neo4j** — a graph of files and functions for structural analysis

**Output:** `parsed_files` — structured metadata for all source files.

**Why it matters:** Gives every downstream agent a structured, queryable understanding of the code rather than raw text. The graph in Neo4j enables understanding *relationships* between files.

---

### Stage 3 — Architecture Analysis
**What it does:** Uses the LLM (qwen2.5-coder:7b) to analyze the code structure for architectural problems. Runs a 3-step LangChain chain:
1. **Detect** — what architectural patterns are present? (MVC, microservices, monolith, etc.)
2. **Analyze** — identify boundary violations, tight coupling, god classes, circular dependencies
3. **Recommend** — concrete refactoring suggestions

**Output:** `architecture_findings` list, `architecture` score.

**Why it matters:** Catches structural problems that static analyzers can't see — like a service layer that directly queries the database, or a "god module" that does 15 unrelated things.

---

### Stage 4 — Security Analysis
**What it does:** Three parallel approaches:
1. **Semgrep** — runs hundreds of pre-built security rules against the source files (OWASP Top 10, injection patterns, secrets detection)
2. **Bandit** — Python-specific static analysis for common vulnerabilities (insecure functions, hardcoded passwords, etc.)
3. **LLM** — asks the LLM to find security issues that static tools miss (logic flaws, auth bypasses, business logic vulnerabilities)

All three results are merged and deduplicated.

**Output:** `security_findings` list, `security` score.

**Why it matters:** Static tools catch known patterns; the LLM catches subtle logic errors that require understanding intent. Using both together is significantly more thorough than either alone.

---

### Stage 5 — Scalability Analysis
**What it does:** Uses the LLM plus **RAG context** (retrieved from ChromaDB's knowledge base) to find performance anti-patterns:
- N+1 query patterns (DB query inside a loop)
- Missing pagination on list endpoints
- Synchronous blocking calls inside async handlers
- No caching on expensive repeated operations
- Missing database indexes on filtered columns
- Unbounded data loading (no LIMIT/OFFSET)

**Output:** `scalability_findings` list, `scalability` score.

**Why it matters:** These issues don't cause bugs — they cause the system to fall over under load. They're invisible in local dev and only show up in production at scale.

---

### Stage 6 — Testing Analysis
**What it does:** Scans the repo for test files, counts them vs source files, measures the test-to-source ratio, checks for pytest config, and coverage setup. Then asks the LLM to evaluate:
- Are there tests at all?
- Do critical paths (auth, writes, business logic) have coverage?
- Are there integration tests or only unit tests?
- Is there a proper test pyramid?

**Output:** `testing_findings` list, `testing` score.

**Why it matters:** A codebase with no tests can look clean but is a ticking time bomb. The score heavily penalizes zero test files (−50 points) and low ratios.

---

### Stage 7 — Technical Debt Analysis
**What it does:** Computes debt metrics from the parsed files (high complexity scores, TODO/FIXME comment counts, function counts per file) and passes them to the LLM, which identifies:
- God modules (files with too many responsibilities)
- Dead code signals
- Missing error handling (bare `except:` clauses)
- Magic numbers and hardcoded configuration
- Deeply nested code

**Output:** `debt_findings` list, `debt` score.

**Why it matters:** Technical debt slows down every future change. Identifying it early means it gets addressed before it becomes load-bearing.

---

### Stage 8 — Requirements Alignment
**What it does:** If the user uploaded a requirements PDF, this stage extracts text from it using **pdfplumber**, then uses the LLM to cross-check the code against the stated requirements. Finds gaps — requirements that aren't implemented, or implementations that contradict the spec.

**Output:** `requirements_alignment` findings.

**Why it matters:** Catches the gap between "what was supposed to be built" and "what was actually built" — something no static tool can do.

---

### Stage 9 — Coaching Report
**What it does:** Takes the scores and top findings from all previous stages and generates a personalized coaching report tailored to the developer's experience level. Uses **mistral:7b** (the synthesis model). Output includes:
- **Strengths** — what the developer is doing well (specific, not generic)
- **Priority improvements** — top 3 most impactful fixes
- **Learning roadmap** — 5 specific topics with resource types (book/course/article)
- **This week's focus** — one concrete, actionable goal
- **Narrative** — 2-paragraph personalized summary

**Output:** `coaching_report` dictionary.

**Why it matters:** Raw findings are overwhelming. The coaching report translates them into an actionable, encouraging plan that helps the developer grow, not just fix bugs.

---

### Stage 10 — Prioritization
**What it does:** Collects all findings from stages 3–8, scores each one by severity and category (security findings weighted highest), and sorts them into a single prioritized list. Security findings get the highest weight, then architecture, then debt/scalability/testing.

**Output:** `prioritized_findings` — the merged, sorted list of all issues.

**Why it matters:** Without prioritization, a developer sees 40 findings with no idea where to start. The prioritized list tells them: "Fix these 5 things first — they matter most."

---

### Stage 11 — Synthesis
**What it does:** Computes the final overall score (weighted average of all 5 dimension scores), generates an executive summary, and assembles the complete `final_report` dictionary that gets saved to the database.

**Output:** `final_report`, `scores` (including `overall`).

**Why it matters:** The single place where everything comes together into the output that the user sees.

---

## Software & Technology Stack

### AI / LLM

| Software | Role |
|----------|------|
| **Ollama** | Runs LLMs locally on your Windows host machine. No cloud API needed, no cost per token |
| **qwen2.5-coder:7b** | Primary model — used by architecture, scalability, debt, security, and testing agents. Code-specialized, fast |
| **mistral:7b** | Synthesis model — used for coaching reports and the final narrative. Better at long-form writing |
| **nomic-embed-text** | Embedding model — converts code chunks into vectors for semantic search in ChromaDB |
| **LangChain** | Framework for building LLM chains (prompt → LLM → parse output) |
| **LangGraph** | Orchestrates the 11-stage pipeline as a directed acyclic graph with shared state |

### Databases

| Database | Role | Why this one? |
|----------|------|---------------|
| **PostgreSQL** | Primary database — stores users, repositories, reviews, findings, scores, progress history | Relational, ACID-compliant, JSONB for flexible raw output storage |
| **Redis** | Two jobs: (1) Celery task broker — queues review jobs; (2) Pub/sub — broadcasts real-time stage progress to WebSocket clients | In-memory, perfect for job queues and real-time messaging |
| **ChromaDB** | Vector database — stores embeddings of every function/class for semantic search (RAG) | Purpose-built for vector similarity search, easy to self-host |
| **Neo4j** | Graph database — stores the code structure as a graph (files → functions → relationships) | Graphs naturally model code structure; Cypher queries enable relationship analysis |
| **MinIO** | Object storage — stores uploaded requirements PDFs | S3-compatible API, self-hosted, no AWS cost |

### Backend

| Software | Role |
|----------|------|
| **FastAPI** | REST API framework — handles HTTP requests, WebSocket connections, background tasks |
| **Celery** | Distributed task queue — runs the 11-stage pipeline asynchronously so the API stays responsive |
| **SQLAlchemy (async)** | ORM — async database access to PostgreSQL |
| **GitPython** | Clones GitHub repositories to disk for analysis |
| **Tree-sitter** | Language-aware AST parser — parses Python, JavaScript, TypeScript source files into structured data |
| **Radon** | Computes cyclomatic complexity scores for Python files |
| **Semgrep** | Static analysis security scanner — runs pre-built OWASP/security rules |
| **Bandit** | Python-specific security linter |
| **pdfplumber** | Extracts text from uploaded requirements PDF files |
| **httpx** | HTTP client — used by the GitHub API client to post PR review comments |
| **Langfuse** | LLM observability — traces every LLM call, shows latency, token usage, and prompt/response history |

### Frontend

| Software | Role |
|----------|------|
| **React + Vite** | UI framework — fast build tooling, hot reload in dev |
| **TypeScript** | Type-safe frontend code |
| **Tailwind CSS** | Utility-first CSS — design system, component styles |
| **Recharts** | Charts — Radar chart for scores, Line chart for progress history |
| **react-router-dom** | Client-side routing between pages |

### Infrastructure

| Software | Role |
|----------|------|
| **Docker** | Packages every service into isolated containers |
| **Docker Compose** | Runs all 10 services together with a single command |
| **Nginx** | Reverse proxy — routes traffic between frontend and API |
| **ngrok** | Exposes your local API to the internet so GitHub can send webhooks to it |

---

## How Docker Is Used

Docker solves the "works on my machine" problem. Every service (API, worker, databases, frontend) runs in its own isolated container with its own dependencies, so nothing conflicts and nothing needs to be manually installed.

### The 10 Docker Services

```
docker-compose.yml
│
├── postgres        → PostgreSQL database (port 5432)
├── redis           → Redis broker + cache (port 6379)
├── chromadb        → Vector database (port 8001)
├── neo4j           → Graph database (ports 7474, 7687)
├── minio           → Object storage (ports 9000, 9001)
├── langfuse        → LLM observability UI (port 3001)
├── api             → FastAPI backend (port 8000)
├── celery_worker   → Background task runner (no port — internal)
├── frontend        → React app served by Vite (port 3000)
└── nginx           → Reverse proxy (port 80)
```

### Data Persistence
Each database service has a **Docker volume** — a named storage area on your disk that persists even when containers stop. Your review data, findings, and scores are never lost when you run `docker compose down`.

```
postgres_data  → all your review records
chroma_data    → code embeddings
neo4j_data     → code graph
redis_data     → cached LLM responses
minio_data     → uploaded PDFs
```

### Networking
All containers share a private Docker network. They communicate using service names as hostnames (e.g., the API connects to PostgreSQL at `postgres:5432`, not `localhost:5432`). The only exception is Ollama — it runs on your Windows host machine (not in Docker), so containers reach it at `host.docker.internal:11434`.

### The Build Process
The `api` and `celery_worker` containers are built from `backend/Dockerfile`. The `frontend` container is built from `frontend/Dockerfile` using a two-stage build:
1. **Builder stage** — runs `npm run build` to compile TypeScript and bundle assets
2. **Serve stage** — copies the built `dist/` folder and serves it with Vite preview

---

## Data Flow Diagram

```
User (browser)
    │  HTTP/WebSocket
    ▼
Nginx (port 80)
    │
    ├──► Frontend (React, port 3000)
    │
    └──► FastAPI (port 8000)
              │
              ├──► PostgreSQL  (store/retrieve review records)
              │
              ├──► Redis       (publish WebSocket progress events)
              │                 (queue Celery tasks)
              │
              └──► Celery Worker
                        │
                        ├──► Ollama (host:11434) — LLM calls
                        ├──► ChromaDB — store/query code embeddings
                        ├──► Neo4j   — store/query code graph
                        ├──► MinIO   — store/retrieve PDFs
                        ├──► Semgrep / Bandit — security scans
                        └──► GitHub API — fetch diffs, post comments
```

---

## Guardrails & Human-in-the-Loop

The system is designed so AI assists but humans decide.

| Rule | Enforcement |
|------|-------------|
| AI never auto-merges | GitHub review event is always `COMMENT` or `REQUEST_CHANGES`, never `APPROVE` — hard-coded, not configurable |
| Critical/security issues always escalated | Any finding with `critical`/`high` severity or `security`/`architecture` category triggers `ai:needs-human-review` label |
| Quality gate | PRs below 70/100 score get `ai:quality-gate-failed` label |
| AI scope | AI handles syntax, style, obvious bugs, and known patterns. Architecture, business logic, and final merge decisions stay with humans |
| Confidence tiers | High confidence findings → suggestion blocks (1-click fix). Medium → inline comment. Low → summary flag for human |

---

## Scoring System

Each dimension is scored 0–100 based on the number and severity of findings:

| Deduction | Amount |
|-----------|--------|
| Critical finding | −25 points |
| High finding | −12 points |
| Medium finding | −5 points |
| Low finding | −2 points |

The overall score is a weighted average:
- Security: 30%
- Architecture: 25%
- Scalability: 20%
- Testing: 15%
- Technical Debt: 10%

| Grade | Score Range |
|-------|-------------|
| A | 80 – 100 |
| B | 65 – 79 |
| C | 50 – 64 |
| D | 0 – 49 |
