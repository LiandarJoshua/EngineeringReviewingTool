# Engineering Review Platform — first-time setup script (Windows PowerShell)
param()
$ErrorActionPreference = "Stop"

function ok   { Write-Host "  + $args" -ForegroundColor Green }
function warn { Write-Host "  ! $args" -ForegroundColor Yellow }
function fail { Write-Host "  x $args" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "  Engineering Review Platform -- Setup" -ForegroundColor Cyan
Write-Host "  ======================================" -ForegroundColor Cyan
Write-Host ""

# Prerequisites
Write-Host "Checking prerequisites..."

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { fail "Docker not found. Install Docker Desktop: https://docs.docker.com/get-docker/" }
try { docker info *>$null } catch { fail "Docker daemon not running. Start Docker Desktop first." }
ok "Docker"

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) { fail "Ollama not found. Install from: https://ollama.com/download" }
ok "Ollama"

Write-Host ""

# .env setup
if (Test-Path .env) {
  warn ".env already exists -- skipping (delete it to reset)"
} else {
  Copy-Item .env.example .env

  # Generate a random SECRET_KEY
  $secret = -join ((1..32) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
  (Get-Content .env) -replace 'changeme_local_jwt_secret_32chars', $secret | Set-Content .env -Encoding utf8
  ok "Generated SECRET_KEY"
  ok "Created .env from .env.example"

  Write-Host ""
  warn "Open .env and fill in:"
  warn "  GITHUB_TOKEN          -- GitHub PAT with repo + pull_requests scopes"
  warn "  GITHUB_WEBHOOK_SECRET -- any random string, must match GitHub webhook config"
  warn "  ADMIN_EMAIL / ADMIN_PASSWORD -- login credentials for the UI"
  Write-Host ""
  Read-Host "  Press Enter after you have edited .env to continue"
}

Write-Host ""

# Ollama models
Write-Host "Pulling Ollama models (this may take a while on first run)..."

function Pull-Model($model) {
  $list = ollama list 2>$null
  if ($list -match [regex]::Escape($model)) {
    ok "$model (already downloaded)"
  } else {
    Write-Host "  Pulling $model..."
    ollama pull $model
    ok "$model"
  }
}

Pull-Model "qwen2.5-coder:7b"
Pull-Model "mistral:7b"
Pull-Model "nomic-embed-text"

Write-Host ""

# Docker Compose
Write-Host "Starting all services..."
docker compose pull --quiet
docker compose up -d

Write-Host ""
Write-Host "  Waiting for services to be healthy..." -ForegroundColor DarkGray
Start-Sleep -Seconds 15
docker compose ps

Write-Host ""
ok "Setup complete!"
Write-Host ""
Write-Host "  Access points:"
Write-Host "    Frontend UI  ->  http://localhost:3000" -ForegroundColor Cyan
Write-Host "    API Docs     ->  http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "    Langfuse     ->  http://localhost:3001  (admin@local.dev / Admin1234!)" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Read STARTUP.md for webhook setup and full usage guide."
Write-Host ""
