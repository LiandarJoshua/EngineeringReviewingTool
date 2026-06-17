import json
from typing import List, Dict, Any
from app.agents.state import ReviewState


def run(state: ReviewState) -> ReviewState:
    """Stage 5: Scalability analysis — N+1, caching, async I/O, pagination, connection pools."""
    from app.agents.llm_client import get_ollama_llm, cached_llm_call
    from app.rag.retrievers import query_knowledge
    import asyncio

    llm = get_ollama_llm()
    rag_context = query_knowledge("N+1 query caching pagination async IO connection pool scalability")
    code_summary = _build_code_summary(state["parsed_files"])

    prompt = f"""
You are a senior backend engineer reviewing code for scalability issues.

Codebase summary:
{code_summary}

Scalability reference:
{rag_context}

Find scalability issues in this codebase. Look for:
1. N+1 query patterns (loop with DB call inside)
2. Missing pagination on list endpoints
3. Synchronous blocking calls in async handlers (requests.get, time.sleep)
4. No caching on expensive repeated operations
5. Missing database indexes for filtered columns
6. Connection pool not configured
7. Unbounded data loading (no limit/offset)

Output a JSON list. Each item must have:
severity (high/medium/low), category, issue, recommendation, file_path.
"""

    try:
        raw = asyncio.get_event_loop().run_until_complete(cached_llm_call(llm, prompt))
    except RuntimeError:
        raw = llm.invoke(prompt).content

    findings = _parse_findings(raw)
    score = _score(findings)

    return {
        **state,
        "scalability_findings": findings,
        "scores": {**state.get("scores", {}), "scalability": score},
        "stage_status": {**state.get("stage_status", {}), "scalability": "complete"},
    }


def _build_code_summary(parsed_files: List[Dict]) -> str:
    lines = []
    for f in parsed_files[:20]:
        fns = [fn["name"] for fn in f.get("functions", [])[:8]]
        lines.append(f"{f['file_path']}: {', '.join(fns)}")
    return "\n".join(lines)


def _parse_findings(raw: str) -> List[Dict[str, Any]]:
    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            findings = json.loads(raw[start:end])
            for f in findings:
                f.setdefault("agent_name", "scalability")
                f.setdefault("severity", "medium")
            return findings
    except Exception:
        pass
    return [{"agent_name": "scalability", "severity": "info", "issue": raw[:300], "category": "scalability"}]


def _score(findings: List[Dict]) -> float:
    weights = {"high": 15, "medium": 7, "low": 3, "info": 0}
    deductions = sum(weights.get(f.get("severity", "info"), 0) for f in findings)
    return max(0.0, 100.0 - deductions)
