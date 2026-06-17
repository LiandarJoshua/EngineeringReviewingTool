import json
from typing import List, Dict, Any
from app.agents.state import ReviewState

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
SEVERITY_EFFORT = {"critical": "high", "high": "medium", "medium": "medium", "low": "low"}


def run(state: ReviewState) -> ReviewState:
    """Stage 10: Prioritize all findings into an ordered fix list."""
    all_findings = (
        state.get("architecture_findings", [])
        + state.get("security_findings", [])
        + state.get("scalability_findings", [])
        + state.get("testing_findings", [])
        + state.get("debt_findings", [])
    )

    prioritized = _prioritize(all_findings)

    return {
        **state,
        "prioritized_findings": prioritized,
        "stage_status": {**state.get("stage_status", {}), "prioritization": "complete"},
    }


def _prioritize(findings: List[Dict]) -> List[Dict[str, Any]]:
    # Score: security findings weighted higher, then by severity, then by category impact
    CATEGORY_WEIGHTS = {
        "sql_injection": 100, "secret_exposure": 100, "missing_auth": 90,
        "ssrf": 80, "command_injection": 80, "xss": 70,
        "architecture": 40, "scalability": 35, "testing": 30, "debt": 20,
    }

    def priority_score(finding: Dict) -> int:
        severity_score = (4 - SEVERITY_ORDER.get(finding.get("severity", "info"), 4)) * 20
        category_score = CATEGORY_WEIGHTS.get(finding.get("category", ""), 10)
        agent_multiplier = 1.5 if finding.get("agent_name") in ("semgrep", "bandit", "security_llm") else 1.0
        return int((severity_score + category_score) * agent_multiplier)

    sorted_findings = sorted(findings, key=priority_score, reverse=True)

    result = []
    for rank, f in enumerate(sorted_findings, start=1):
        result.append({
            **f,
            "priority_rank": rank,
            "effort": SEVERITY_EFFORT.get(f.get("severity", "low"), "low"),
            "fix_window": _fix_window(f.get("severity", "low")),
        })

    return result


def _fix_window(severity: str) -> str:
    return {
        "critical": "immediate (before next deploy)",
        "high": "this sprint",
        "medium": "next sprint",
        "low": "backlog",
        "info": "optional",
    }.get(severity, "backlog")
