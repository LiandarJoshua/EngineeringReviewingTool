.PHONY: dev down logs pull-models seed eval k8s-deploy test build

dev:
	cp -n .env.example .env 2>/dev/null || true
	docker compose up -d
	@echo ""
	@echo "Stack running:"
	@echo "  API:      http://localhost:8000"
	@echo "  Frontend: http://localhost:3000"
	@echo "  LangFuse: http://localhost:3001"
	@echo "  Neo4j:    http://localhost:7474"
	@echo "  MinIO:    http://localhost:9001"

down:
	docker compose down

logs:
	docker compose logs -f api celery_worker

build:
	docker compose build

pull-models:
	@echo "Pulling Ollama models (requires Ollama running on host)..."
	ollama pull qwen2.5-coder:7b
	ollama pull mistral:7b
	ollama pull nomic-embed-text
	@echo "Done. Models ready."

seed:
	@echo "Seeding engineering knowledge base into ChromaDB..."
	docker compose exec api python -m app.rag.indexes.knowledge_index --seed

eval:
	@echo "Running evaluation pipeline..."
	docker compose exec api python -m app.evaluation.pipeline

test:
	docker compose exec api pytest tests/ -v --cov=app --cov-report=term-missing

k8s-deploy:
	helm upgrade --install engineering-review infra/helm/engineering-review \
		--namespace engineering-review \
		--create-namespace \
		--values infra/helm/engineering-review/values.yaml
