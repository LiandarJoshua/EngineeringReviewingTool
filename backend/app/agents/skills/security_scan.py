from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.skills.base import BaseSkill


class SecurityScanSkill(BaseSkill):
    """Scans PR diff for security vulnerabilities.

    Covers OWASP Top 10, injection patterns, auth bypasses,
    hardcoded secrets, and insecure defaults.
    All findings are flagged for human review — this skill never auto-suggests fixes.
    """

    name = "security_scan"
    description = "OWASP Top 10, injection, auth bypasses, secrets, insecure defaults"

    def run(self, pr_context: dict, llm) -> list[dict]:
        diff    = pr_context.get("diff_summary", "")
        title   = pr_context.get("pr_title", "")

        prompt = f"""You are a security engineer performing a focused security review.

PR title: {title}

Changed code:
{diff}

Check ONLY for security issues:
1. Injection vulnerabilities (SQL, command, LDAP, XPath)
2. Broken authentication or session management
3. Sensitive data exposure (secrets, tokens, PII logged or hardcoded)
4. Insecure direct object references
5. Missing authorization checks
6. Cross-site scripting (XSS) or CSRF
7. Use of dangerous functions (eval, exec, pickle.loads, etc.)
8. Insecure cryptography (MD5, SHA1, hardcoded IV/key)
9. Open redirects or SSRF patterns
10. Dependency confusion or path traversal

For each issue output a JSON object:
{self._finding_schema()}

Set category to "security", "authentication", or "authorization".
Set confidence based on how certain you are this is exploitable.
Leave suggested_code empty — security fixes require human judgment.

Output a JSON array. Nothing else."""

        raw = llm.invoke([
            SystemMessage(content="You are a security-focused code reviewer. Return only valid JSON arrays."),
            HumanMessage(content=prompt),
        ]).content

        findings = self._parse(raw)
        # Force all security findings to require human review
        for f in findings:
            f.setdefault("confidence", "high")
            if f.get("category") not in ("security", "authentication", "authorization"):
                f["category"] = "security"
        return findings
