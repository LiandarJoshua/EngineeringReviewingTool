import json
from typing import List, Dict, Any
from app.agents.state import ReviewState


def run(state: ReviewState) -> ReviewState:
    """Stage 8: Requirements alignment — only runs if a requirements PDF was uploaded."""
    if not state.get("requirements_pdf_path"):
        return {
            **state,
            "requirements_alignment": [],
            "stage_status": {**state.get("stage_status", {}), "requirements": "skipped"},
        }

    from app.agents.llm_client import get_ollama_llm
    from app.ingestion.pdf_extractor import extract_requirements_from_pdf

    llm = get_ollama_llm()
    req_data = extract_requirements_from_pdf(state["requirements_pdf_path"])
    requirements = req_data["requirements"]

    if not requirements:
        return {
            **state,
            "requirements_alignment": [{"note": "No structured requirements found in PDF"}],
            "stage_status": {**state.get("stage_status", {}), "requirements": "complete"},
        }

    implemented_functions = _collect_function_names(state["parsed_files"])
    routes = _collect_routes(state["parsed_files"])

    prompt = f"""
You are reviewing a software project against its requirements specification.

Requirements extracted from spec document ({len(requirements)} total):
{json.dumps(requirements[:30], indent=2)}

Implemented API routes:
{json.dumps(routes[:20], indent=2)}

Implemented functions (sample):
{json.dumps(implemented_functions[:40], indent=2)}

For each requirement, determine:
- is_implemented: true/false
- confidence: 0.0-1.0
- evidence: what in the code covers this, or what is missing
- gap: describe what is missing if not implemented

Output a JSON list, one item per requirement.
"""

    raw = llm.invoke(prompt).content
    alignment = _parse_alignment(raw, requirements)

    return {
        **state,
        "requirements_alignment": alignment,
        "stage_status": {**state.get("stage_status", {}), "requirements": "complete"},
    }


def _collect_function_names(parsed_files: List[Dict]) -> List[str]:
    names = []
    for f in parsed_files:
        names.extend(fn["name"] for fn in f.get("functions", []))
    return names[:60]


def _collect_routes(parsed_files: List[Dict]) -> List[Dict]:
    routes = []
    for f in parsed_files:
        routes.extend(f.get("routes", []))
    return routes


def _parse_alignment(raw: str, requirements: List[str]) -> List[Dict[str, Any]]:
    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except Exception:
        pass
    # Fallback: return requirements with unknown status
    return [
        {"requirement": r, "is_implemented": None, "confidence": 0.0, "gap": "Could not parse LLM output"}
        for r in requirements
    ]
