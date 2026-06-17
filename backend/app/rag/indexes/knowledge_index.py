"""
Build and seed the engineering knowledge base index into ChromaDB.
Run via: python -m app.rag.indexes.knowledge_index --seed
"""
import argparse
from pathlib import Path
from app.config import get_settings

settings = get_settings()
KNOWLEDGE_BASE_DIR = Path(__file__).parent.parent / "knowledge_base"


def build_knowledge_index():
    from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
    from llama_index.vector_stores.chroma import ChromaVectorStore
    from llama_index.embeddings.ollama import OllamaEmbedding
    from app.storage.chroma_store import get_chroma_client

    embed_model = OllamaEmbedding(
        model_name=settings.ollama_embedding_model,
        base_url=settings.ollama_host,
    )

    documents = SimpleDirectoryReader(str(KNOWLEDGE_BASE_DIR)).load_data()
    print(f"Loaded {len(documents)} documents from knowledge base.")

    client = get_chroma_client()
    collection = client.get_or_create_collection("engineering_knowledge")
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True,
    )
    print("Knowledge base indexed successfully.")
    return index


def build_code_index(repo_id: str, documents):
    from llama_index.core import VectorStoreIndex, StorageContext
    from llama_index.vector_stores.chroma import ChromaVectorStore
    from llama_index.embeddings.ollama import OllamaEmbedding
    from app.storage.chroma_store import get_chroma_client

    embed_model = OllamaEmbedding(
        model_name=settings.ollama_embedding_model,
        base_url=settings.ollama_host,
    )

    client = get_chroma_client()
    collection = client.get_or_create_collection("code_chunks")
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True,
    )
    return index


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", action="store_true", help="Seed knowledge base into ChromaDB")
    args = parser.parse_args()
    if args.seed:
        build_knowledge_index()
