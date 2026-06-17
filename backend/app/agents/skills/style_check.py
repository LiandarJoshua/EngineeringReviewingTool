from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.skills.base import BaseSkill


class StyleCheckSkill(BaseSkill):
    """Checks PR diff for style, formatting, and naming issues.

    High-confidence findings with suggested_code populated become
    1-click suggestion blocks on the GitHub PR.
    """

    name = "style_check"
    description = "Formatting, naming conventions, type hints, docstrings, unused imports"

    def run(self, pr_context: dict, llm) -> list[dict]:
        diff  = pr_context.get("diff_summary", "")
        stack = pr_context.get("stack", {})
        lang  = stack.get("language", "Python")

        prompt = f"""You are a code style reviewer. Language: {lang}.

Changed code:
{diff}

Check ONLY for style and formatting issues:
1. Naming convention violations (snake_case for Python, camelCase for JS/TS, etc.)
2. Unused imports
3. Missing type hints on function signatures (Python)
4. Missing or incomplete docstrings on public functions/classes
5. Inconsistent indentation or trailing whitespace
6. Lines exceeding 100 characters
7. Magic numbers (use named constants instead)
8. Commented-out code left in

For each issue output a JSON object:
{self._finding_schema()}

Set category to "style", "naming", "unused_import", "missing_type_hint", or "docstring".
Set confidence "high" only when the fix is unambiguous and you can provide the exact replacement.
Populate suggested_code with the corrected line(s) when confidence is "high" — this enables 1-click apply on GitHub.

Output a JSON array. Nothing else."""

        raw = llm.invoke([
            SystemMessage(content="You are a strict code style reviewer. Return only valid JSON arrays."),
            HumanMessage(content=prompt),
        ]).content

        return self._parse(raw)
