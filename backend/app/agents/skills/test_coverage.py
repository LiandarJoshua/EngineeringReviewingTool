from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.skills.base import BaseSkill


class TestCoverageSkill(BaseSkill):
    """Reviews whether the PR includes adequate tests for its changes.

    Does not check existing coverage — only evaluates whether the
    new/changed code in this PR has corresponding tests added.
    """

    name = "test_coverage"
    description = "Missing tests for new functionality, untested edge cases, weak assertions"

    def run(self, pr_context: dict, llm) -> list[dict]:
        diff         = pr_context.get("diff_summary", "")
        title        = pr_context.get("pr_title", "")
        changed_files = pr_context.get("changed_files", [])

        test_files   = [f for f in changed_files if "test" in f.lower() or "spec" in f.lower()]
        source_files = [f for f in changed_files if f not in test_files]

        prompt = f"""You are a test quality reviewer.

PR title: {title}
Source files changed: {source_files}
Test files changed: {test_files}

Changed code:
{diff}

Check ONLY for test coverage gaps:
1. New functions or methods with no corresponding test added
2. New API endpoints not covered by integration tests
3. New business logic paths (if/else branches) without test cases
4. Error handling paths (exceptions, edge cases) not tested
5. Tests with no assertions or only trivial assertions
6. Test file changed but source not changed (or vice versa) — signals missing test
7. Critical paths (auth, payments, data writes) with no test

For each gap output a JSON object:
{self._finding_schema()}

Set file_path to the SOURCE file missing coverage (not the test file).
Set category to "testing".
Set severity: "high" for untested critical paths, "medium" for untested new functions, "low" for missing edge cases.
Leave suggested_code empty — test implementation is the developer's responsibility.

If the PR only changes tests or docs with no logic, return an empty array [].

Output a JSON array. Nothing else."""

        raw = llm.invoke([
            SystemMessage(content="You are a test coverage reviewer. Return only valid JSON arrays."),
            HumanMessage(content=prompt),
        ]).content

        return self._parse(raw)
