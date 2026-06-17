from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.storage.chroma_store import initialize_collections
from app.storage.minio_store import ensure_bucket

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize storage collections
    try:
        initialize_collections()
    except Exception as e:
        print(f"[WARNING] ChromaDB not ready yet: {e}")

    # Auto-seed engineering knowledge base if ChromaDB collection is empty
    try:
        from app.storage.chroma_store import get_chroma_client
        client = get_chroma_client()
        col = client.get_or_create_collection("engineering_knowledge")
        if col.count() == 0:
            print("[INFO] Engineering knowledge base is empty — seeding ChromaDB...")
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _seed_knowledge_base)
        else:
            print(f"[INFO] ChromaDB knowledge base ready ({col.count()} documents)")
    except Exception as e:
        print(f"[WARNING] ChromaDB knowledge seeding skipped: {e}")

    try:
        ensure_bucket()
    except Exception as e:
        print(f"[WARNING] MinIO not ready yet: {e}")

    yield

    # Shutdown: close Neo4j driver
    from app.storage.neo4j_store import close_driver
    close_driver()


def _seed_knowledge_base():
    try:
        from app.rag.indexes.knowledge_index import build_knowledge_index
        build_knowledge_index()
    except Exception as e:
        print(f"[WARNING] Knowledge base seeding failed: {e}")


app = FastAPI(
    title="Engineering Review Platform",
    description="Autonomous multi-agent code review and developer coaching system",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "environment": settings.environment,
        "ollama_host": settings.ollama_host,
    }


from app.api.routes import reviews, websocket, webhooks, feedback, dashboard, schedules
from app.api.routes.auth import router as auth_router

app.include_router(auth_router)
app.include_router(reviews.router)
app.include_router(websocket.router)
app.include_router(webhooks.router)
app.include_router(feedback.router)
app.include_router(dashboard.router)
app.include_router(schedules.router)
