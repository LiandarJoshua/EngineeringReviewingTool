"""GitHub REST API client for PR review loop."""
import re
import json
import base64
from typing import Optional
import httpx


class GitHubClient:
    def __init__(self, token: str, repo_full_name: str):
        owner, repo = repo_full_name.split("/", 1)
        self.token = token
        self.owner = owner
        self.repo = repo
        self.base = f"https://api.github.com/repos/{owner}/{repo}"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _get(self, path: str, **params) -> dict:
        r = httpx.get(f"{self.base}{path}", headers=self.headers, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, body: dict) -> dict:
        r = httpx.post(f"{self.base}{path}", headers=self.headers, json=body, timeout=30)
        r.raise_for_status()
        return r.json()

    def _patch(self, path: str, body: dict) -> dict:
        r = httpx.patch(f"{self.base}{path}", headers=self.headers, json=body, timeout=30)
        r.raise_for_status()
        return r.json()

    # ── PR helpers ───────────────────────────────────────────────────────────

    def get_pr(self, pr_number: int) -> dict:
        return self._get(f"/pulls/{pr_number}")

    def get_pr_diff(self, pr_number: int) -> str:
        r = httpx.get(
            f"{self.base}/pulls/{pr_number}",
            headers={**self.headers, "Accept": "application/vnd.github.v3.diff"},
            timeout=60,
        )
        r.raise_for_status()
        return r.text

    def get_pr_files(self, pr_number: int) -> list[dict]:
        return self._get(f"/pulls/{pr_number}/files")

    def get_file_content(self, file_path: str, ref: str) -> Optional[str]:
        try:
            data = self._get(f"/contents/{file_path}", ref=ref)
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        except Exception:
            return None

    # ── Review posting ───────────────────────────────────────────────────────

    def post_review(
        self,
        pr_number: int,
        commit_sha: str,
        body: str,
        review_event: str,          # "COMMENT" | "REQUEST_CHANGES"
        inline_comments: list[dict],
    ) -> dict:
        """Post a PR review with inline comments.

        review_event must NOT be "APPROVE" — the AI never approves autonomously.
        Each inline_comment: {path, line, body}
        """
        if review_event == "APPROVE":
            raise ValueError("Guardrail: AI must never autonomously approve a PR")

        comments = [
            {
                "path": c["path"],
                "line": c["line"],
                "side": "RIGHT",
                "body": c["body"],
            }
            for c in inline_comments
            if c.get("path") and c.get("line")
        ]
        return self._post(
            f"/pulls/{pr_number}/reviews",
            {
                "commit_id": commit_sha,
                "body": body,
                "event": review_event,
                "comments": comments,
            },
        )

    def post_comment(self, pr_number: int, body: str) -> dict:
        """Post a general review comment on the PR (uses pulls API, not issues API,
        so it works with pull_requests:write scope only)."""
        return self._post(
            f"/pulls/{pr_number}/reviews",
            {"body": body, "event": "COMMENT", "comments": []},
        )

    # ── Commit status ────────────────────────────────────────────────────────

    def post_commit_status(
        self,
        sha: str,
        state: str,             # pending | success | failure | error
        description: str,
        context: str = "ai/security-scan",
        target_url: str = "",
    ) -> dict:
        """Post a status check on a commit SHA. Visible as ✅/❌ in GitHub UI."""
        body: dict = {"state": state, "description": description[:140], "context": context}
        if target_url:
            body["target_url"] = target_url
        r = httpx.post(f"{self.base}/statuses/{sha}", headers=self.headers, json=body, timeout=30)
        r.raise_for_status()
        return r.json()

    def get_commit_diff(self, sha: str) -> str:
        """Fetch the unified diff for a single commit."""
        r = httpx.get(
            f"{self.base}/commits/{sha}",
            headers={**self.headers, "Accept": "application/vnd.github.v3.diff"},
            timeout=60,
        )
        r.raise_for_status()
        return r.text

    def get_commit_files(self, sha: str) -> list[dict]:
        data = self._get(f"/commits/{sha}")
        return data.get("files", [])

    # ── Issues ────────────────────────────────────────────────────────────────

    def create_issue(self, title: str, body: str, labels: list[str] | None = None) -> dict:
        """Open a GitHub issue. Used for regression alerts — never for auto-merge."""
        return self._post("/issues", {"title": title, "body": body, "labels": labels or []})

    def get_default_branch(self) -> str:
        data = self._get("")
        return data.get("default_branch", "main")

    def get_open_prs(self) -> list[dict]:
        return self._get("/pulls", state="open", per_page=50)  # type: ignore[return-value]

    # ── Labels ───────────────────────────────────────────────────────────────

    def set_labels(self, pr_number: int, labels: list[str]) -> None:
        self._post(f"/issues/{pr_number}/labels", {"labels": labels})
        self._ensure_labels_exist(labels)

    def _ensure_labels_exist(self, labels: list[str]) -> None:
        LABEL_META = {
            "ai:reviewed":            {"color": "0075ca", "description": "AI review passed quality threshold"},
            "ai:needs-human-review":  {"color": "e4e669", "description": "AI flagged issues requiring human attention"},
            "ai:auto-fixed":          {"color": "0e8a16", "description": "AI applied suggested fixes to this PR"},
            "ai:quality-gate-failed": {"color": "d93f0b", "description": "Code quality below minimum threshold after AI review"},
        }
        for label in labels:
            meta = LABEL_META.get(label, {"color": "ededed", "description": ""})
            try:
                httpx.post(
                    f"{self.base}/labels",
                    headers=self.headers,
                    json={"name": label, **meta},
                    timeout=10,
                )
            except Exception:
                pass  # label already exists
