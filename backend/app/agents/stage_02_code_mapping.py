import uuid
from typing import List, Dict, Any
from app.agents.state import ReviewState
from app.ingestion.code_parser import parse_file_with_treesitter, compute_complexity
from app.ingestion.metadata_extractor import walk_source_files


def run(state: ReviewState) -> ReviewState:
    """
    Stage 2: Parse all source files with Tree-sitter.
    Stores code chunks in ChromaDB and graph in Neo4j.
    DB writes to ChromaDB and Neo4j happen here; PostgreSQL file records written too.
    """
    local_path = state["local_path"]
    repo_id = state["repo_id"]
    language = state["stack"].get("language", "unknown")

    source_files = walk_source_files(local_path, language)
    parsed_files: List[Dict[str, Any]] = []

    for file_path in source_files:
        ast_data = parse_file_with_treesitter(file_path, language)
        ast_data["complexity_score"] = compute_complexity(file_path)
        parsed_files.append(ast_data)

        # Store in ChromaDB
        _store_code_chunks_in_chroma(ast_data, repo_id)

        # Store in Neo4j
        _store_code_graph_in_neo4j(ast_data, repo_id)

    return {
        **state,
        "parsed_files": parsed_files,
        "stage_status": {**state.get("stage_status", {}), "code_mapping": "complete"},
    }


def _store_code_chunks_in_chroma(ast_data: Dict, repo_id: str) -> None:
    try:
        from app.storage.chroma_store import upsert_documents
        file_path = ast_data["file_path"]
        documents = []
        metadatas = []
        ids = []

        for fn in ast_data.get("functions", []):
            doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{repo_id}:{file_path}:{fn['name']}"))
            documents.append(f"function {fn['name']} in {file_path} lines {fn['line_start']}-{fn['line_end']}")
            metadatas.append({
                "repo_id": repo_id,
                "file_path": file_path,
                "chunk_type": "function",
                "language": ast_data["language"],
            })
            ids.append(doc_id)

        for cls in ast_data.get("classes", []):
            doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{repo_id}:{file_path}:{cls['name']}:class"))
            documents.append(f"class {cls['name']} in {file_path} lines {cls['line_start']}-{cls['line_end']}")
            metadatas.append({
                "repo_id": repo_id,
                "file_path": file_path,
                "chunk_type": "class",
                "language": ast_data["language"],
            })
            ids.append(doc_id)

        if documents:
            upsert_documents("code_chunks", ids, documents, metadatas)
    except Exception:
        pass  # Non-fatal; storage failures don't block the pipeline


def _store_code_graph_in_neo4j(ast_data: Dict, repo_id: str) -> None:
    try:
        from app.storage.neo4j_store import create_file_node, create_function_node
        file_path = ast_data["file_path"]
        create_file_node(repo_id, file_path, ast_data["language"], ast_data.get("complexity_score", 0.0))

        for fn in ast_data.get("functions", []):
            create_function_node(
                repo_id=repo_id,
                name=fn["name"],
                file_path=file_path,
                line_start=fn["line_start"],
                line_end=fn["line_end"],
                signature=fn.get("signature", fn["name"]),
            )
    except Exception:
        pass  # Non-fatal
