import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from app.config import get_settings

settings = get_settings()

COLLECTIONS = {
    "code_chunks": {
        "description": "Parsed code functions, classes, routes",
        "metadata_fields": ["repo_id", "file_path", "chunk_type", "language"],
    },
    "documentation": {
        "description": "READMEs, requirements docs, comments",
        "metadata_fields": ["repo_id", "doc_type", "file_path"],
    },
    "engineering_knowledge": {
        "description": "OWASP, design patterns, DDIA, best practices",
        "metadata_fields": ["source", "category", "topic"],
    },
}

_client: Optional[chromadb.HttpClient] = None


def get_chroma_client() -> chromadb.HttpClient:
    global _client
    if _client is None:
        _client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=ChromaSettings(
                chroma_client_auth_provider="chromadb.auth.token.TokenAuthClientProvider",
                chroma_client_auth_credentials=settings.chroma_token,
            ),
        )
    return _client


def get_or_create_collection(name: str) -> chromadb.Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def initialize_collections() -> None:
    for name in COLLECTIONS:
        get_or_create_collection(name)


def upsert_documents(
    collection_name: str,
    ids: List[str],
    documents: List[str],
    metadatas: List[Dict[str, Any]],
    embeddings: Optional[List[List[float]]] = None,
) -> None:
    col = get_or_create_collection(collection_name)
    kwargs: Dict[str, Any] = {"ids": ids, "documents": documents, "metadatas": metadatas}
    if embeddings:
        kwargs["embeddings"] = embeddings
    col.upsert(**kwargs)


def query_collection(
    collection_name: str,
    query_texts: List[str],
    n_results: int = 5,
    where: Optional[Dict] = None,
) -> Dict:
    col = get_or_create_collection(collection_name)
    kwargs: Dict[str, Any] = {"query_texts": query_texts, "n_results": n_results}
    if where:
        kwargs["where"] = where
    return col.query(**kwargs)


def delete_repo_chunks(repo_id: str) -> None:
    col = get_or_create_collection("code_chunks")
    col.delete(where={"repo_id": repo_id})
