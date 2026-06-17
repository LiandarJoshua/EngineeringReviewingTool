from typing import Optional
from app.config import get_settings

settings = get_settings()


def _get_embed_model():
    from llama_index.embeddings.ollama import OllamaEmbedding
    return OllamaEmbedding(
        model_name=settings.ollama_embedding_model,
        base_url=settings.ollama_host,
    )


def get_knowledge_retriever(top_k: int = 5):
    """Retriever over the static engineering knowledge base (OWASP, patterns, etc.)."""
    from llama_index.core import VectorStoreIndex
    from llama_index.vector_stores.chroma import ChromaVectorStore
    from llama_index.core import StorageContext
    from app.storage.chroma_store import get_chroma_client

    client = get_chroma_client()
    collection = client.get_or_create_collection("engineering_knowledge")
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=_get_embed_model(),
    )
    return index.as_retriever(similarity_top_k=top_k)


def get_code_retriever(repo_id: str, top_k: int = 5):
    """Retriever over code chunks for a specific repository."""
    from llama_index.core import VectorStoreIndex
    from llama_index.vector_stores.chroma import ChromaVectorStore
    from llama_index.core import StorageContext
    from llama_index.core.vector_stores import MetadataFilter, MetadataFilters
    from app.storage.chroma_store import get_chroma_client

    client = get_chroma_client()
    collection = client.get_or_create_collection("code_chunks")
    vector_store = ChromaVectorStore(chroma_collection=collection)
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=_get_embed_model(),
    )
    filters = MetadataFilters(filters=[MetadataFilter(key="repo_id", value=repo_id)])
    return index.as_retriever(similarity_top_k=top_k, filters=filters)


def query_knowledge(query: str, top_k: int = 5) -> str:
    """Convenience: query the knowledge base and return concatenated text."""
    try:
        retriever = get_knowledge_retriever(top_k=top_k)
        nodes = retriever.retrieve(query)
        return "\n\n".join(n.get_content() for n in nodes)
    except Exception as e:
        return f"[Knowledge retrieval unavailable: {e}]"


def query_code(repo_id: str, query: str, top_k: int = 5) -> str:
    """Convenience: query code chunks for a repo and return concatenated text."""
    try:
        retriever = get_code_retriever(repo_id=repo_id, top_k=top_k)
        nodes = retriever.retrieve(query)
        return "\n\n".join(n.get_content() for n in nodes)
    except Exception as e:
        return f"[Code retrieval unavailable: {e}]"
