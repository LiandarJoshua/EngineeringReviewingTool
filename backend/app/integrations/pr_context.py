"""Parse a GitHub PR diff into a structured context for review agents."""
import re
from typing import Optional


def parse_diff(diff_text: str) -> list[dict]:
    """Split a unified diff into per-file records with added/removed line info."""
    files = []
    current: Optional[dict] = None
    current_hunk_header = ""

    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            if current:
                files.append(current)
            current = {"path": "", "added_lines": [], "removed_lines": [], "hunks": []}

        elif line.startswith("+++ b/") and current is not None:
            current["path"] = line[6:]

        elif line.startswith("@@") and current is not None:
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            current_hunk_header = line
            if m:
                current["_new_start"] = int(m.group(2))
                current["_line_cursor"] = int(m.group(2)) - 1
                current["hunks"].append({"header": line, "lines": []})

        elif current is not None and line.startswith("+") and not line.startswith("+++"):
            cursor = current.get("_line_cursor", 0) + 1
            current["_line_cursor"] = cursor
            current["added_lines"].append({"line": cursor, "content": line[1:]})
            if current["hunks"]:
                current["hunks"][-1]["lines"].append({"type": "add", "line": cursor, "content": line[1:]})

        elif current is not None and line.startswith("-") and not line.startswith("---"):
            current["removed_lines"].append({"content": line[1:]})
            if current["hunks"]:
                current["hunks"][-1]["lines"].append({"type": "remove", "content": line[1:]})

        elif current is not None and not line.startswith("\\"):
            cursor = current.get("_line_cursor", 0) + 1
            current["_line_cursor"] = cursor
            if current["hunks"]:
                current["hunks"][-1]["lines"].append({"type": "context", "line": cursor, "content": line[1:] if line.startswith(" ") else line})

    if current:
        files.append(current)

    return [f for f in files if f["path"] and _is_reviewable(f["path"])]


def build_pr_context(diff_text: str, pr_meta: dict, file_contents: dict[str, str]) -> dict:
    """Build a review-ready context from a PR diff."""
    files = parse_diff(diff_text)

    # Attach full file content where available
    for f in files:
        f["full_content"] = file_contents.get(f["path"], "")

    added_summary = "\n\n".join(
        f"### {f['path']}\n" + "\n".join(
            f"+{l['line']:4d}: {l['content']}" for l in f["added_lines"][:80]
        )
        for f in files[:20]
    )

    return {
        "pr_number":     pr_meta.get("number"),
        "pr_title":      pr_meta.get("title", ""),
        "pr_description": pr_meta.get("body", ""),
        "author":        pr_meta.get("user", {}).get("login", ""),
        "base_branch":   pr_meta.get("base", {}).get("ref", "main"),
        "head_sha":      pr_meta.get("head", {}).get("sha", ""),
        "changed_files": files,
        "files_count":   len(files),
        "additions":     sum(len(f["added_lines"]) for f in files),
        "deletions":     sum(len(f["removed_lines"]) for f in files),
        "diff_summary":  added_summary[:8000],   # cap for LLM context
        "raw_diff":      diff_text[:16000],
    }


def _is_reviewable(path: str) -> bool:
    SKIP = {".lock", ".sum", ".png", ".jpg", ".svg", ".ico", ".woff", ".ttf", ".eot", ".bin", ".zip"}
    return not any(path.endswith(ext) for ext in SKIP)
