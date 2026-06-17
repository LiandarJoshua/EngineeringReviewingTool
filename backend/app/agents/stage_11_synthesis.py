import json
from datetime import datetime
from typing import Dict, Any
from app.agents.state import ReviewState


def run(state: ReviewState) -> ReviewState:
    """Stage 11: Compile all agent outputs into the final review report."""
    from app.agents.llm_client import get_synthesis_llm

    llm = get_synthesis_llm()
    scores = state.get("scores", {})

    # Compute overall score as weighted average
    weights = {
        "security": 0.35,
        "architecture": 0.25,
        "testing": 0.20,
        "scalability": 0.12,
        "debt": 0.08,
    }
    overall = sum(scores.get(k, 50.0) * w for k, w in weights.items())
    scores["overall"] = round(overall, 1)

    # Executive summary
    top_critical = [
        f for f in state.get("prioritized_findings", [])
        if f.get("severity") in ("critical", "high")
    ][:5]

    prompt = f"""
You are a principal engineer writing an executive engineering review summary.

Review scores:
{json.dumps(scores, indent=2)}

Top critical/high severity findings:
{json.dumps(top_critical, indent=2)}

Stack: {state['stack'].get('language')} / {state['stack'].get('framework')}
Files reviewed: {len(state.get('parsed_files', []))}

Write a 3-paragraph executive summary:
1. Overall health assessment (reference the scores)
2. The 2-3 most critical issues that must be addressed
3. Positive aspects and overall trajectory

Be direct, professional, and specific. No filler.
Output as plain text (not JSON).
"""

    executive_summary = llm.invoke(prompt).content.strip()

    final_report = {
        "review_id": state["review_id"],
        "generated_at": datetime.utcnow().isoformat(),
        "stack": state["stack"],
        "scores": scores,
        "executive_summary": executive_summary,
        "findings_count": {
            "total": len(state.get("prioritized_findings", [])),
            "critical": sum(1 for f in state.get("prioritized_findings", []) if f.get("severity") == "critical"),
            "high": sum(1 for f in state.get("prioritized_findings", []) if f.get("severity") == "high"),
            "medium": sum(1 for f in state.get("prioritized_findings", []) if f.get("severity") == "medium"),
            "low": sum(1 for f in state.get("prioritized_findings", []) if f.get("severity") == "low"),
        },
        "architecture_findings": state.get("architecture_findings", []),
        "security_findings": state.get("security_findings", []),
        "scalability_findings": state.get("scalability_findings", []),
        "testing_findings": state.get("testing_findings", []),
        "debt_findings": state.get("debt_findings", []),
        "requirements_alignment": state.get("requirements_alignment", []),
        "coaching_report": state.get("coaching_report", {}),
        "prioritized_findings": state.get("prioritized_findings", []),
    }

    return {
        **state,
        "scores": scores,
        "final_report": final_report,
        "stage_status": {**state.get("stage_status", {}), "synthesis": "complete"},
    }
