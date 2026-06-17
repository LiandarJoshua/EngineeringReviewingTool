"""
Evaluation pipeline: run the full review against golden test repos.
Usage: python -m app.evaluation.pipeline
"""
import json
from pathlib import Path
from app.evaluation.metrics import compute_finding_metrics, compute_score_accuracy

GOLDEN_SET = [
    {
        "repo": "app/evaluation/golden_set/vulnerable_fastapi",
        "description": "Intentionally vulnerable FastAPI app",
        "expected_findings": [
            {"category": "sql_injection", "severity": "critical", "file": "routes/users.py"},
            {"category": "secret_exposure", "severity": "critical", "file": "config.py"},
            {"category": "missing_auth", "severity": "critical", "file": "routes/admin.py"},
            {"category": "missing_pagination", "severity": "medium", "file": "routes/orders.py"},
        ],
        "expected_scores": {
            "security": (0, 40),
            "testing": (0, 30),
        },
    },
]


def run_evaluation() -> list:
    from app.agents.orchestrator import build_review_graph
    from app.agents.state import ALL_STAGES

    graph = build_review_graph()
    results = []

    for test_case in GOLDEN_SET:
        repo_path = Path(test_case["repo"])
        if not repo_path.exists():
            print(f"[SKIP] Test repo not found: {repo_path}")
            continue

        print(f"\nEvaluating: {test_case['description']}")

        initial_state = {
            "review_id": "eval-001",
            "repo_id": "eval-repo-001",
            "repo_url": str(repo_path.absolute()),
            "user_id": "eval-user-001",
            "requirements_pdf_path": None,
            "local_path": str(repo_path.absolute()),
            "stack": {},
            "parsed_files": [],
            "architecture_findings": [], "security_findings": [],
            "scalability_findings": [], "testing_findings": [],
            "debt_findings": [], "requirements_alignment": [],
            "coaching_report": {}, "prioritized_findings": [],
            "final_report": {}, "scores": {},
            "stage_status": {s: "pending" for s in ALL_STAGES},
            "errors": [],
        }

        final_state = None
        for event in graph.stream(initial_state):
            final_state = list(event.values())[0]

        if not final_state:
            continue

        all_findings = final_state.get("prioritized_findings", [])
        precision, recall, f1 = compute_finding_metrics(
            predicted=all_findings,
            expected=test_case["expected_findings"],
        )
        score_acc = compute_score_accuracy(
            predicted=final_state.get("scores", {}),
            expected_ranges=test_case["expected_scores"],
        )

        result = {
            "test_case": test_case["description"],
            "findings_count": len(all_findings),
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "score_accuracy": score_acc,
            "scores": final_state.get("scores", {}),
        }
        results.append(result)
        print(json.dumps(result, indent=2))

    return results


if __name__ == "__main__":
    run_evaluation()
