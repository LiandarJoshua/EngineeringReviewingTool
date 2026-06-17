from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.skills.base import BaseSkill


class LogicReviewSkill(BaseSkill):
    """Reviews PR diff for bugs, logic errors, and missing error handling.

    Focuses on correctness — things that will cause wrong behavior
    or crashes at runtime, not style issues.
    """

    name = "logic_review"
    description = "Bugs, logic errors, missing error handling, performance anti-patterns"

    def run(self, pr_context: dict, llm) -> list[dict]:
        diff  = pr_context.get("diff_summary", "")
        title = pr_context.get("pr_title", "")
        desc  = pr_context.get("pr_description", "")

        prompt = f"""You are a senior engineer reviewing code for correctness.

PR title: {title}
PR description: {desc}

Changed code:
{diff}

Check ONLY for logic and correctness issues:
1. Off-by-one errors, incorrect comparisons, wrong operators
2. Null/None dereference without guard checks
3. Unhandled exceptions or bare except clauses
4. Race conditions or missing locks in concurrent code
5. Incorrect boolean logic (and/or precedence, negation errors)
6. Missing return values or early returns that skip logic
7. Mutating function arguments (unexpected side effects)
8. N+1 query patterns (DB call inside a loop)
9. Blocking I/O calls inside async functions
10. Resource leaks (unclosed files, DB connections, sockets)

For each issue output a JSON object:
{self._finding_schema()}

Set category to "bug", "performance", or "architecture".
Set severity "critical" for crashes/data loss, "high" for wrong behavior, "medium" for performance.
Only populate suggested_code if the fix is a simple, clear replacement. Leave empty for complex logic fixes.

Output a JSON array. Nothing else."""

        raw = llm.invoke([
            SystemMessage(content="You are an expert in finding runtime bugs and logic errors. Return only valid JSON arrays."),
            HumanMessage(content=prompt),
        ]).content

        return self._parse(raw)
