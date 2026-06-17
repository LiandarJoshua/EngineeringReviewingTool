import json
from typing import List, Dict, Any
from app.agents.state import ReviewState


def run(state: ReviewState) -> ReviewState:
    """Stage 7: Technical debt analysis — complexity, dead code, TODOs, duplication."""
    from app.agents.llm_client import get_ollama_llm

    llm = get_ollama_llm()
    debt_metrics = _compute_debt_metrics(state["parsed_files"], state["local_path"])

    prompt = f"""
You are a senior engineer auditing a codebase for technical debt.

Debt metrics computed:
{json.dumps(debt_metrics, indent=2)}

Find and categorize technical debt:
1. High complexity files (complexity_score > 15) — flag for refactoring
2. TODO/FIXME/HACK comments — count and flag if critical paths affected
3. Files with too many functions (god modules)
4. Deeply nested code (complexity signals)
5. Dead code signals (unused imports, functions never called)
6. Missing error handling (bare except, swallowed exceptions)
7. Magic numbers / hardcoded configuration values

Output a JSON list of findings. Each item: severity, category, issue, recommendation, file_path.
Also output an overall debt_score from 0-100 (100 = no debt, 0 = severe debt).
"""

    raw = llm.invoke(prompt).content
    findings = _parse_findings(raw)
    score = _extract_or_compute_score(raw, findings)

    return {
        **state,
        "debt_findings": findings,
        "scores": {**state.get("scores", {}), "debt": score},
        "stage_status": {**state.get("stage_status", {}), "technical_debt": "complete"},
    }


def _compute_debt_metrics(parsed_files: List[Dict], local_path: str) -> Dict:
    from pathlib import Path
    import re

    todo_count = 0
    fixme_count = 0
    high_complexity = []
    god_modules = []

    root = Path(local_path)
    for f in parsed_files:
        try:
            content = Path(f["file_path"]).read_text(encoding="utf-8", errors="ignore")
            todo_count += len(re.findall(r"\bTODO\b", content, re.IGNORECASE))
            fixme_count += len(re.findall(r"\b(FIXME|HACK|XXX)\b", content, re.IGNORECASE))
        except Exception:
            pass

        complexity = f.get("complexity_score", 0)
        if complexity > 15:
            high_complexity.append({"file": f["file_path"], "score": complexity})

        fn_count = len(f.get("functions", []))
        if fn_count > 20:
            god_modules.append({"file": f["file_path"], "function_count": fn_count})

    return {
        "total_files": len(parsed_files),
        "todo_count": todo_count,
        "fixme_count": fixme_count,
        "high_complexity_files": high_complexity[:10],
        "god_modules": god_modules[:5],
        "avg_complexity": round(
            sum(f.get("complexity_score", 0) for f in parsed_files) / max(len(parsed_files), 1), 2
        ),
    }


def _parse_findings(raw: str) -> List[Dict[str, Any]]:
    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            findings = json.loads(raw[start:end])
            for f in findings:
                f.setdefault("agent_name", "technical_debt")
                f.setdefault("severity", "low")
            return findings
    except Exception:
        pass
    return []


def _extract_or_compute_score(raw: str, findings: List[Dict]) -> float:
    import re
    match = re.search(r'"debt_score"\s*:\s*(\d+(?:\.\d+)?)', raw)
    if match:
        return float(match.group(1))
    weights = {"high": 10, "medium": 5, "low": 2}
    deductions = sum(weights.get(f.get("severity", "low"), 0) for f in findings)
    return max(0.0, 100.0 - deductions)
