import json
from typing import List, Dict, Any
from app.agents.state import ReviewState


def run(state: ReviewState) -> ReviewState:
    """Stage 3: Architecture analysis using a 3-step LangChain chain (no crewai)."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from app.agents.llm_client import get_ollama_llm
    from app.rag.retrievers import query_knowledge

    llm = get_ollama_llm()
    rag_context = query_knowledge("clean architecture principles boundary violations coupling")
    repo_structure = _summarize_repo_structure(state["parsed_files"], state["stack"])

    # Step 1: Detect pattern
    detect_messages = [
        SystemMessage(content=(
            "You are an expert software architect who identifies MVC, Clean Architecture, "
            "Layered, Hexagonal, and Microservice patterns from code structure. "
            "Respond with valid JSON only."
        )),
        HumanMessage(content=f"""
Analyze this repository structure and identify the architecture pattern.

Repository Structure:
{repo_structure}

Architecture Reference:
{rag_context}

Output JSON with keys: pattern, confidence (0.0-1.0), evidence (list of strings).
"""),
    ]
    detect_result = llm.invoke(detect_messages)
    pattern_info = detect_result.content if hasattr(detect_result, "content") else str(detect_result)

    # Step 2: Analyze violations
    analyze_messages = [
        SystemMessage(content=(
            "You are a senior engineer specializing in identifying architectural anti-patterns "
            "and technical debt. Respond with a valid JSON list only."
        )),
        HumanMessage(content=f"""
Based on this detected architecture pattern:
{pattern_info}

Repository Structure:
{repo_structure}

Find all boundary violations, coupling issues, and missing abstractions.
Output a JSON list of findings, each with:
- severity (high/medium/low)
- category (string)
- issue (string)
- file_path (string)
"""),
    ]
    analyze_result = llm.invoke(analyze_messages)
    violations_raw = analyze_result.content if hasattr(analyze_result, "content") else str(analyze_result)

    # Step 3: Recommend fixes
    recommend_messages = [
        SystemMessage(content=(
            "You are a principal engineer who has refactored multiple production systems. "
            "Give concrete, specific recommendations, not generic advice. "
            "Respond with a valid JSON list only."
        )),
        HumanMessage(content=f"""
For each of these architecture findings, produce a specific actionable recommendation.
Include before/after code examples where possible.

Findings:
{violations_raw}

Output a JSON list with fields: issue, recommendation, priority (1-5).
Merge recommendation into the original finding so each item has: severity, category, issue, file_path, recommendation, priority.
"""),
    ]
    recommend_result = llm.invoke(recommend_messages)
    final_raw = recommend_result.content if hasattr(recommend_result, "content") else str(recommend_result)

    findings = _parse_findings(final_raw, agent_name="architecture")
    score = _score(findings)

    return {
        **state,
        "architecture_findings": findings,
        "scores": {**state.get("scores", {}), "architecture": score},
        "stage_status": {**state.get("stage_status", {}), "architecture": "complete"},
    }


def _summarize_repo_structure(parsed_files: List[Dict], stack: Dict) -> str:
    lines = [
        f"Language: {stack.get('language', 'unknown')}",
        f"Framework: {stack.get('framework', 'unknown')}",
        f"Files parsed: {len(parsed_files)}",
        "",
        "Top-level files and their function/class counts:",
    ]
    for f in parsed_files[:30]:
        fn_count = len(f.get("functions", []))
        cls_count = len(f.get("classes", []))
        lines.append(f"  {f['file_path']}  ({fn_count} functions, {cls_count} classes)")
    return "\n".join(lines)


def _parse_findings(raw: str, agent_name: str) -> List[Dict[str, Any]]:
    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            findings = json.loads(raw[start:end])
            for f in findings:
                f.setdefault("agent_name", agent_name)
                f.setdefault("severity", "medium")
                f.setdefault("category", "architecture")
            return findings
    except Exception:
        pass
    return [{"agent_name": agent_name, "severity": "info", "issue": raw[:500], "category": "architecture"}]


def _score(findings: List[Dict]) -> float:
    weights = {"critical": 20, "high": 10, "medium": 5, "low": 2, "info": 0}
    deductions = sum(weights.get(f.get("severity", "info"), 0) for f in findings)
    return max(0.0, 100.0 - deductions)
