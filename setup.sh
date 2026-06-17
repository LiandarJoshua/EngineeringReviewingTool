#!/usr/bin/env bash
# Engineering Review Platform — first-time setup script
# Works on macOS and Linux.
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✓ $1${NC}"; }
warn() { echo -e "${YELLOW}  ! $1${NC}"; }
fail() { echo -e "${RED}  ✗ $1${NC}"; exit 1; }

echo ""
echo "  Engineering Review Platform — Setup"
echo "  ======================================"
echo ""

# ── Prerequisites check ────────────────────────────────────────────────────────
echo "Checking prerequisites..."

command -v docker   >/dev/null 2>&1 || fail "Docker not found. Install Docker Desktop: https://docs.docker.com/get-docker/"
docker info         >/dev/null 2>&1 || fail "Docker daemon not running. Start Docker Desktop first."
ok "Docker"

command -v ollama   >/dev/null 2>&1 || fail "Ollama not found. Install from: https://ollama.com/download"
ok "Ollama"

echo ""

# ── .env setup ────────────────────────────────────────────────────────────────
if [ -f .env ]; then
  warn ".env already exists — skipping copy (delete it to reset)"
else
  cp .env.example .env

  # Generate a random 32-char SECRET_KEY
  if command -v openssl >/dev/null 2>&1; then
    SECRET=$(openssl rand -hex 16)
    sed -i.bak "s/changeme_local_jwt_secret_32chars/$SECRET/" .env && rm -f .env.bak
    ok "Generated SECRET_KEY"
  fi

  ok "Created .env from .env.example"
  echo ""
  warn "Open .env and fill in:"
  warn "  GITHUB_TOKEN     — GitHub PAT with repo + pull_requests scopes"
  warn "  GITHUB_WEBHOOK_SECRET — any random string, must match GitHub webhook config"
  warn "  ADMIN_EMAIL / ADMIN_PASSWORD — login credentials for the UI"
  echo ""
  read -rp "  Press Enter after you have edited .env to continue..."
fi

echo ""

# ── Ollama models ──────────────────────────────────────────────────────────────
echo "Pulling Ollama models (this may take a while on first run)..."

pull_model() {
  local model=$1
  if ollama list 2>/dev/null | grep -q "^${model}"; then
    ok "$model (already downloaded)"
  else
    echo "  Pulling $model..."
    ollama pull "$model"
    ok "$model"
  fi
}

# Start ollama if not running
ollama list >/dev/null 2>&1 || (ollama serve &>/dev/null & sleep 3)

pull_model "qwen2.5-coder:7b"
pull_model "mistral:7b"
pull_model "nomic-embed-text"

echo ""

# ── Docker Compose ────────────────────────────────────────────────────────────
echo "Starting all services..."
docker compose pull --quiet
docker compose up -d

echo ""
echo "  Waiting for services to be healthy..."
sleep 15

docker compose ps --format "table {{.Name}}\t{{.Status}}" | grep -v "^NAME"

echo ""
ok "Setup complete!"
echo ""
echo "  Access points:"
echo "    Frontend UI  →  http://localhost:3000"
echo "    API Docs     →  http://localhost:8000/docs"
echo "    Langfuse     →  http://localhost:3001  (admin@local.dev / Admin1234!)"
echo ""
echo "  Read STARTUP.md for webhook setup and full usage guide."
echo ""
