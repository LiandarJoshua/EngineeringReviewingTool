import json
from typing import List, Dict, Any, Optional
from app.agents.state import ReviewState


def run(state: ReviewState) -> ReviewState:
    """Stage 9: Personalized developer coaching report using Mistral:7b."""
    from app.agents.llm_client import get_synthesis_llm

    llm = get_synthesis_llm()
    all_findings = (
        state.get("architecture_findings", [])
        + state.get("security_findings", [])
        + state.get("scalability_findings", [])
        + state.get("testing_findings", [])
        + state.get("debt_findings", [])
    )
    scores = state.get("scores", {})
    experience_level = state.get("experience_level", "mid")

    # Check for longitudinal progress data
    progress_context = _get_progress_context(state.get("user_id"), state.get("repo_id"))

    prompt = f"""
You are a senior engineering mentor providing personalized coaching to a developer.

Developer profile:
- Experience level: {experience_level}

Current review scores:
{json.dumps(scores, indent=2)}

Top findings requiring attention:
{json.dumps(_top_findings(all_findings, n=10), indent=2)}

{f"Progress history:{chr(10)}{progress_context}" if progress_context else ""}

Generate a personalized coaching report covering:
1. **Strengths** — what this developer is doing well (be specific, reference the code)
2. **Priority improvements** — top 3 things to fix immediately, with concrete steps
3. **Learning roadmap** — 5 specific learning topics tailored to their level and gaps
4. **Next week's focus** — one concrete actionable goal

Be encouraging but honest. Be specific — no generic advice.
Tailor the language to a {experience_level} developer.

Output ONLY valid JSON with these exact keys:
- strengths: list of strings (each string is one strength)
- priority_improvements: list of strings (each string is one improvement, e.g. "Fix auth bypass: add input sanitization to LoginController")
- learning_roadmap: list of objects, each with keys: topic (string), resource_type (one of: book, course, article, video), reason (string)
- next_week_focus: string (one sentence)
- narrative: string (2-paragraph summary)

Do NOT nest objects inside strengths or priority_improvements — they must be plain strings.
"""

    raw = llm.invoke(prompt).content
    coaching_report = _parse_coaching(raw)

    return {
        **state,
        "coaching_report": coaching_report,
        "stage_status": {**state.get("stage_status", {}), "coaching": "complete"},
    }


def _top_findings(findings: List[Dict], n: int = 10) -> List[Dict]:
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    sorted_findings = sorted(findings, key=lambda f: severity_order.get(f.get("severity", "info"), 4))
    return [{k: v for k, v in f.items() if k in ("severity", "category", "issue", "recommendation")}
            for f in sorted_findings[:n]]


def _get_progress_context(user_id: Optional[str], repo_id: Optional[str]) -> Optional[str]:
    """Fetch past review scores if available."""
    if not user_id or not repo_id:
        return None
    try:
        from app.storage.postgres_store import get_past_review_scores
        import asyncio
        past = asyncio.get_event_loop().run_until_complete(
            get_past_review_scores(user_id, repo_id, limit=5)
        )
        if len(past) < 2:
            return None
        lines = [f"Review #{i+1}: {json.dumps(r)}" for i, r in enumerate(past)]
        return "\n".join(lines)
    except Exception:
        return None


def _flatten_string_list(items: Any) -> List[str]:
    """Ensure every item in a list is a plain string, even if the LLM returned objects."""
    if not isinstance(items, list):
        return []
    result = []
    for item in items:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            # Try common keys the LLM might use
            text = (
                item.get("text") or item.get("description") or item.get("issue")
                or item.get("improvement") or item.get("step") or item.get("action")
                or item.get("title") or item.get("content")
            )
            if text:
                detail = item.get("steps") or item.get("details") or item.get("recommendation") or item.get("reason")
                result.append(f"{text}: {detail}" if detail else str(text))
            else:
                result.append(", ".join(str(v) for v in item.values() if v))
        else:
            result.append(str(item))
    return result


def _parse_coaching(raw: str) -> Dict[str, Any]:
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(raw[start:end])
            # Normalize list fields to plain strings in case the LLM returned objects
            data["strengths"] = _flatten_string_list(data.get("strengths", []))
            data["priority_improvements"] = _flatten_string_list(data.get("priority_improvements", []))
            return data
    except Exception:
        pass
    return {
        "strengths": [],
        "priority_improvements": [],
        "learning_roadmap": [],
        "next_week_focus": "",
        "narrative": raw[:800],
    }
