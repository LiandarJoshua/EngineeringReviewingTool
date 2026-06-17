from app.agents.state import ReviewState
from app.ingestion.repo_cloner import clone_repository, detect_stack


def run(state: ReviewState) -> ReviewState:
    """
    Stage 1: Clone repo, detect language/framework/package manager.
    Stores metadata in state; DB write happens in API layer.
    """
    repo_url = state["repo_url"]
    review_id = state["review_id"]

    local_path = clone_repository(repo_url, review_id)
    stack = detect_stack(local_path)

    return {
        **state,
        "local_path": local_path,
        "stack": stack,
        "stage_status": {**state.get("stage_status", {}), "ingestion": "complete"},
    }
