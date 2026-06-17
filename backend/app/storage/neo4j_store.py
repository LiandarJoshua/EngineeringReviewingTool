from neo4j import GraphDatabase, Driver
from typing import List, Dict, Any, Optional
from app.config import get_settings

settings = get_settings()
_driver: Optional[Driver] = None


def get_driver() -> Driver:
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


def close_driver() -> None:
    global _driver
    if _driver:
        _driver.close()
        _driver = None


def run_query(cypher: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
    driver = get_driver()
    with driver.session() as session:
        result = session.run(cypher, params or {})
        return [record.data() for record in result]


def create_repository_node(repo_id: str, name: str, language: str, framework: str) -> None:
    run_query(
        """
        MERGE (r:Repository {id: $repo_id})
        SET r.name = $name, r.language = $language, r.framework = $framework
        """,
        {"repo_id": repo_id, "name": name, "language": language, "framework": framework},
    )


def create_file_node(repo_id: str, file_path: str, file_type: str, complexity: float) -> None:
    run_query(
        """
        MERGE (f:File {path: $file_path, repo_id: $repo_id})
        SET f.type = $file_type, f.complexity = $complexity
        WITH f
        MATCH (r:Repository {id: $repo_id})
        MERGE (f)-[:PART_OF]->(r)
        """,
        {"repo_id": repo_id, "file_path": file_path, "file_type": file_type, "complexity": complexity},
    )


def create_function_node(
    repo_id: str, name: str, file_path: str, line_start: int, line_end: int, signature: str
) -> None:
    run_query(
        """
        MERGE (fn:Function {name: $name, file_path: $file_path, repo_id: $repo_id})
        SET fn.line_start = $line_start, fn.line_end = $line_end, fn.signature = $signature
        WITH fn
        MATCH (f:File {path: $file_path, repo_id: $repo_id})
        MERGE (fn)-[:DEFINED_IN]->(f)
        """,
        {
            "repo_id": repo_id, "name": name, "file_path": file_path,
            "line_start": line_start, "line_end": line_end, "signature": signature,
        },
    )


def create_function_call(caller: str, callee: str, file_path: str, repo_id: str) -> None:
    run_query(
        """
        MATCH (caller:Function {name: $caller, repo_id: $repo_id})
        MATCH (callee:Function {name: $callee, repo_id: $repo_id})
        MERGE (caller)-[:CALLS]->(callee)
        """,
        {"caller": caller, "callee": callee, "file_path": file_path, "repo_id": repo_id},
    )


def get_coupling_metrics(repo_id: str) -> List[Dict]:
    """Return functions with highest in-degree (most depended upon)."""
    return run_query(
        """
        MATCH (f:Function {repo_id: $repo_id})<-[:CALLS]-(caller)
        RETURN f.name AS function, f.file_path AS file, count(caller) AS in_degree
        ORDER BY in_degree DESC
        LIMIT 20
        """,
        {"repo_id": repo_id},
    )


def delete_repo_graph(repo_id: str) -> None:
    run_query(
        """
        MATCH (n {repo_id: $repo_id})
        DETACH DELETE n
        """,
        {"repo_id": repo_id},
    )
