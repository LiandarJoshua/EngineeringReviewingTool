import json
from pathlib import Path
from typing import List, Dict, Any
from app.agents.state import ReviewState


def run(state: ReviewState) -> ReviewState:
    """Stage 6: Testing quality analysis — coverage, test patterns, missing test types."""
    from app.agents.llm_client import get_ollama_llm
    from app.rag.retrievers import query_knowledge

    llm = get_ollama_llm()
    test_summary = _analyze_test_files(state["local_path"], state["parsed_files"])
    rag_context = query_knowledge("unit testing integration testing coverage test pyramid")

    prompt = f"""
You are a senior QA engineer reviewing a codebase's test quality.

Test file analysis:
{json.dumps(test_summary, indent=2)}

Testing reference:
{rag_context}

Evaluate the testing quality and find issues:
1. Are there tests at all?
2. Is coverage adequate for critical paths (auth, writes, business logic)?
3. Are there integration tests or only unit tests?
4. Are there any tests that never assert anything?
5. Is there a test pyramid (unit > integration > E2E) or only one type?
6. Are async functions tested correctly?

Output a JSON list of findings. Each item must have:
severity (high/medium/low), category, issue, recommendation.
Also include a JSON summary object with keys: test_file_count, source_file_count, has_integration_tests, estimated_coverage_pct.
"""

    raw = llm.invoke(prompt).content
    findings = _parse_findings(raw)
    score = _compute_score(test_summary, findings)

    return {
        **state,
        "testing_findings": findings,
        "scores": {**state.get("scores", {}), "testing": score},
        "stage_status": {**state.get("stage_status", {}), "testing": "complete"},
    }


def _analyze_test_files(local_path: str, parsed_files: List[Dict]) -> Dict[str, Any]:
    root = Path(local_path)
    test_files = [
        str(p.relative_to(root))
        for p in root.rglob("*")
        if p.is_file() and ("test" in p.stem.lower() or "spec" in p.stem.lower())
    ]
    source_files = [f for f in parsed_files if "test" not in f["file_path"].lower()]
    test_functions = sum(
        len([fn for fn in f.get("functions", []) if "test" in fn["name"].lower()])
        for f in parsed_files
        if "test" in f["file_path"].lower()
    )
    return {
        "test_file_count": len(test_files),
        "source_file_count": len(source_files),
        "test_function_count": test_functions,
        "test_to_source_ratio": round(len(test_files) / max(len(source_files), 1), 2),
        "test_files": test_files[:10],
        "has_pytest_ini": (root / "pytest.ini").exists() or (root / "pyproject.toml").exists(),
        "has_coverage_config": (root / ".coveragerc").exists(),
    }


def _parse_findings(raw: str) -> List[Dict[str, Any]]:
    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            findings = json.loads(raw[start:end])
            for f in findings:
                f.setdefault("agent_name", "testing")
                f.setdefault("severity", "medium")
            return findings
    except Exception:
        pass
    return []


def _compute_score(test_summary: Dict, findings: List[Dict]) -> float:
    base = 100.0
    if test_summary["test_file_count"] == 0:
        base -= 50
    elif test_summary["test_to_source_ratio"] < 0.1:
        base -= 30
    elif test_summary["test_to_source_ratio"] < 0.2:
        base -= 15
    weights = {"high": 10, "medium": 5, "low": 2}
    base -= sum(weights.get(f.get("severity", "info"), 0) for f in findings)
    return max(0.0, base)
