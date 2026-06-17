import json
import subprocess
from typing import List, Dict, Any
from app.agents.state import ReviewState


def run(state: ReviewState) -> ReviewState:
    """Stage 4: Security analysis — Semgrep + Bandit + LLM contextual review."""
    local_path = state["local_path"]
    language = state["stack"].get("language", "unknown")

    semgrep_findings = _run_semgrep(local_path)
    bandit_findings = _run_bandit(local_path) if language == "python" else []
    llm_findings = _run_security_llm(state, semgrep_findings + bandit_findings)

    all_findings = semgrep_findings + bandit_findings + llm_findings
    deduped = _deduplicate(all_findings)
    score = _score(deduped)

    return {
        **state,
        "security_findings": deduped,
        "scores": {**state.get("scores", {}), "security": score},
        "stage_status": {**state.get("stage_status", {}), "security": "complete"},
    }


def _run_semgrep(local_path: str) -> List[Dict[str, Any]]:
    try:
        result = subprocess.run(
            ["semgrep", "--config=auto", "--json", "--quiet", local_path],
            capture_output=True, text=True, timeout=120,
        )
        data = json.loads(result.stdout)
        findings = []
        for r in data.get("results", []):
            findings.append({
                "agent_name": "semgrep",
                "severity": r.get("extra", {}).get("severity", "medium").lower(),
                "category": r.get("check_id", "unknown"),
                "issue": r.get("extra", {}).get("message", ""),
                "recommendation": r.get("extra", {}).get("fix", ""),
                "file_path": r.get("path", ""),
                "line_number": r.get("start", {}).get("line"),
            })
        return findings
    except Exception:
        return []


def _run_bandit(local_path: str) -> List[Dict[str, Any]]:
    try:
        result = subprocess.run(
            ["bandit", "-r", local_path, "-f", "json", "-q"],
            capture_output=True, text=True, timeout=60,
        )
        data = json.loads(result.stdout)
        findings = []
        severity_map = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
        for r in data.get("results", []):
            findings.append({
                "agent_name": "bandit",
                "severity": severity_map.get(r.get("issue_severity", "MEDIUM"), "medium"),
                "category": r.get("test_id", "unknown"),
                "issue": r.get("issue_text", ""),
                "recommendation": "",
                "file_path": r.get("filename", ""),
                "line_number": r.get("line_number"),
                "cwe_reference": r.get("issue_cwe", {}).get("id", ""),
            })
        return findings
    except Exception:
        return []


def _run_security_llm(state: ReviewState, existing_findings: List[Dict]) -> List[Dict[str, Any]]:
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from app.agents.llm_client import get_ollama_llm
        from app.rag.retrievers import query_knowledge

        llm = get_ollama_llm()
        owasp_context = query_knowledge("OWASP authentication authorization injection")

        high_complexity = sorted(
            state["parsed_files"],
            key=lambda f: f.get("complexity_score", 0),
            reverse=True,
        )[:5]
        code_summary = "\n".join(
            f"File: {f['file_path']} — functions: {[fn['name'] for fn in f.get('functions', [])[:5]]}"
            for f in high_complexity
        )

        messages = [
            SystemMessage(content=(
                "You are an application security engineer specializing in business logic flaws, "
                "authentication bypass, and OWASP Top 10 issues that static scanners miss. "
                "Respond with a valid JSON list only."
            )),
            HumanMessage(content=f"""
Review this codebase for security vulnerabilities that static analysis misses:
authentication logic, authorization gaps, insecure direct object references,
missing rate limiting, and business logic flaws.

Existing static findings summary ({len(existing_findings)} total):
{json.dumps(existing_findings[:5], indent=2)}

High-complexity files (most likely to have issues):
{code_summary}

OWASP Reference:
{owasp_context}

Output a JSON list of findings. Each finding must have:
severity (critical/high/medium/low), category, issue, recommendation, file_path.
Only report issues not already covered by the static findings above.
"""),
        ]
        result = llm.invoke(messages)
        raw = result.content if hasattr(result, "content") else str(result)
        return _parse_llm_findings(raw)
    except Exception:
        return []


def _parse_llm_findings(raw: str) -> List[Dict[str, Any]]:
    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            findings = json.loads(raw[start:end])
            for f in findings:
                f.setdefault("agent_name", "security_llm")
                f.setdefault("severity", "medium")
            return findings
    except Exception:
        pass
    return []


def _deduplicate(findings: List[Dict]) -> List[Dict]:
    seen = set()
    result = []
    for f in findings:
        key = (f.get("file_path", ""), f.get("line_number", 0), f.get("category", ""))
        if key not in seen:
            seen.add(key)
            result.append(f)
    return result


def _score(findings: List[Dict]) -> float:
    weights = {"critical": 25, "high": 15, "medium": 5, "low": 2, "info": 0}
    deductions = sum(weights.get(f.get("severity", "info"), 0) for f in findings)
    return max(0.0, 100.0 - deductions)
