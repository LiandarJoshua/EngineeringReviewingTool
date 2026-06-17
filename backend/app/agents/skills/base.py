import json
import logging
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)


class BaseSkill(ABC):
    """All PR review skills implement this interface.

    Each skill focuses on one concern, runs its own prompt,
    and returns findings in the standard format.
    """

    name: str = ""
    description: str = ""

    @abstractmethod
    def run(self, pr_context: dict, llm) -> list[dict]:
        """Run this skill against the PR context. Returns a list of findings."""
        raise NotImplementedError

    def _parse(self, raw: str) -> list[dict]:
        """Extract a JSON array from raw LLM output."""
        try:
            start = raw.find("[")
            end   = raw.rfind("]") + 1
            if start >= 0 and end > start:
                items = json.loads(raw[start:end])
                return [
                    f for f in items
                    if isinstance(f, dict) and f.get("issue")
                ]
        except Exception as e:
            log.warning("[%s] Failed to parse LLM output: %s", self.name, e)
        return []

    def _finding_schema(self) -> str:
        return """{
  "file_path": "src/example.py",
  "line": 42,
  "severity": "critical|high|medium|low|info",
  "category": "security|style|naming|bug|performance|testing|architecture",
  "confidence": "high|medium|low",
  "issue": "One-sentence description of the problem",
  "recommendation": "Concrete fix",
  "suggested_code": "Optional: exact replacement code"
}"""
