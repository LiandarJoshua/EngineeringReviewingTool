"""PIV Loop: Context → Review → Inline Comments → Auto-suggest fixes → Self-correct.

Guardrails (hard-coded, cannot be disabled):
  - AI NEVER auto-merges
  - AI NEVER sends "APPROVE" to GitHub
  - Auto-suggest (suggestion blocks) only for HIGH confidence, non-security issues
  - Critical / security issues always routed to human reviewer
  - Maximum 3 self-correction iterations
"""
import logging
from typing import Any

log = logging.getLogger(__name__)

# ── Confidence tiers ──────────────────────────────────────────────────────────
# HIGH  → post as "suggested change" block (author can apply with 1 click)
# MEDIUM → post as inline comment with recommendation
# LOW   → collected into summary, labelled "needs-human-review"

AUTO_SUGGEST_CATEGORIES = {
    "style", "formatting", "naming", "unused_import",
    "missing_type_hint", "docstring", "whitespace",
}

HUMAN_ONLY_CATEGORIES = {
    "security", "authentication", "authorization",
    "architecture", "business_logic", "data_model",
}

QUALITY_THRESHOLD = 70   # minimum score to pass
MAX_ITERATIONS    = 3


def run(
    pr_context: dict,
    github_token: str,
    repo_full_name: str,
    experience_level: str = "mid",
    quality_threshold: int = QUALITY_THRESHOLD,
    skill_names: list[str] | None = None,
) -> dict:
    """Entry point — called from Celery task.

    skill_names: if provided, only run those skills (e.g. ["security_scan"]).
    None = run all four skills.
    """
    from app.integrations.github_client import GitHubClient

    gh = GitHubClient(github_token, repo_full_name)
    pr_number = pr_context["pr_number"]
    head_sha  = pr_context["head_sha"]

    iteration       = 0
    all_findings    = []
    score           = 0
    suggestions_made = 0

    while iteration < MAX_ITERATIONS:
        iteration += 1
        log.info("PIV iteration %d for PR #%d", iteration, pr_number)

        # ── Step 1: run agents on current diff ───────────────────────────────
        findings = _run_agents(pr_context, experience_level, skill_names)
        score    = _compute_score(findings)

        all_findings = findings  # replace with latest pass

        # ── Step 2: post inline comments (first iteration only avoids spam) ──
        if iteration == 1:
            inline = _build_inline_comments(findings, pr_context)
            suggestions_made = len([c for c in inline if "```suggestion" in c["body"]])
            _post_review_comments(gh, pr_number, head_sha, inline, score)

        # ── Step 3: self-correction check ────────────────────────────────────
        blocking = _blocking_issues(findings)
        if score >= quality_threshold and not blocking:
            log.info("Quality threshold met at iteration %d (score=%.1f)", iteration, score)
            break

        if iteration < MAX_ITERATIONS:
            # Let review author see suggestions and try another pass after they apply them
            # We don't commit on their behalf — we only suggest
            log.info("Score %.1f < threshold %d, will re-review after fixes are applied", score, quality_threshold)
            break  # post result; author applies suggestions; re-run triggers on next push

    # ── Step 4: post summary comment ─────────────────────────────────────────
    summary = _build_summary(all_findings, score, iteration, suggestions_made, quality_threshold)
    gh.post_comment(pr_number, summary)

    # ── Step 5: apply labels & guardrails ────────────────────────────────────
    labels = []
    review_event = "COMMENT"

    if _blocking_issues(all_findings) or score < quality_threshold:
        labels.append("ai:needs-human-review")
        if score < quality_threshold:
            labels.append("ai:quality-gate-failed")
        review_event = "REQUEST_CHANGES"
    else:
        labels.append("ai:reviewed")

    if suggestions_made > 0:
        labels.append("ai:auto-fixed")

    gh.set_labels(pr_number, labels)

    return {
        "pr_number":       pr_number,
        "score":           score,
        "findings_count":  len(all_findings),
        "suggestions_made": suggestions_made,
        "iterations":      iteration,
        "passed":          score >= quality_threshold and not _blocking_issues(all_findings),
        "labels":          labels,
    }


# ── Internal helpers ──────────────────────────────────────────────────────────

def _run_agents(
    pr_context: dict,
    experience_level: str,
    skill_names: list[str] | None = None,
) -> list[dict]:
    """Run PR review skills and merge their findings.

    skill_names: restrict to named skills. None = all.
    """
    from app.agents.llm_client import get_ollama_llm
    from app.agents.skills import (
        SecurityScanSkill,
        StyleCheckSkill,
        LogicReviewSkill,
        TestCoverageSkill,
    )

    llm = get_ollama_llm()
    all_skills = [
        SecurityScanSkill(),
        StyleCheckSkill(),
        LogicReviewSkill(),
        TestCoverageSkill(),
    ]
    skills = [s for s in all_skills if skill_names is None or s.name in skill_names]

    all_findings = []
    for skill in skills:
        try:
            log.info("Running skill: %s", skill.name)
            findings = skill.run(pr_context, llm)
            log.info("Skill %s returned %d findings", skill.name, len(findings))
            all_findings.extend(findings)
        except Exception as e:
            log.error("Skill %s failed: %s", skill.name, e)

    return all_findings


def _compute_score(findings: list[dict]) -> float:
    """Score 0–100: deduct points per severity."""
    DEDUCT = {"critical": 25, "high": 12, "medium": 5, "low": 2, "info": 0}
    penalty = sum(DEDUCT.get(f.get("severity", "info"), 0) for f in findings)
    return max(0.0, 100.0 - penalty)


def _blocking_issues(findings: list[dict]) -> list[dict]:
    """Return issues that must have human sign-off before merge."""
    return [
        f for f in findings
        if f.get("severity") in ("critical", "high")
        or f.get("category") in HUMAN_ONLY_CATEGORIES
    ]


def _build_inline_comments(findings: list[dict], pr_context: dict) -> list[dict]:
    """Convert findings into GitHub inline review comments.
    High-confidence style issues become suggestion blocks (1-click apply).
    """
    comments = []
    for f in findings:
        if not f.get("file_path") or not f.get("line"):
            continue

        category   = f.get("category", "")
        confidence = f.get("confidence", "medium")
        suggested  = f.get("suggested_code", "").strip()

        # Determine icon
        icons = {"critical": "🚨", "high": "⚠️", "medium": "💡", "low": "📝", "info": "ℹ️"}
        icon  = icons.get(f.get("severity", "info"), "📝")

        body = f"{icon} **[{f.get('severity', 'info').upper()}]** {f.get('issue', '')}\n\n"
        body += f"> {f.get('recommendation', '')}"

        # Attach suggestion block for high-confidence non-security issues
        if (
            confidence == "high"
            and category in AUTO_SUGGEST_CATEGORIES
            and suggested
            and category not in HUMAN_ONLY_CATEGORIES
        ):
            body += f"\n\n```suggestion\n{suggested}\n```"

        if category in HUMAN_ONLY_CATEGORIES or f.get("severity") in ("critical", "high"):
            body += "\n\n> 🔒 **Requires human review before merge.**"

        comments.append({
            "path": f["file_path"],
            "line": int(f["line"]),
            "body": body,
        })

    return comments


def _post_review_comments(
    gh: Any,
    pr_number: int,
    head_sha: str,
    comments: list[dict],
    score: float,
) -> None:
    """Post findings as a PR review. Tries inline comments first; falls back to body-only."""
    blocking = score < QUALITY_THRESHOLD or any("🔒" in c["body"] for c in comments)
    event    = "REQUEST_CHANGES" if blocking else "COMMENT"
    header   = f"**AI Engineering Review** — Score: {score:.0f}/100\n\n"

    # Try inline comments (batches of 30)
    inline_ok = False
    for i in range(0, len(comments), 30):
        batch = comments[i:i + 30]
        try:
            gh.post_review(pr_number, head_sha, header if i == 0 else "", event if i == 0 else "COMMENT", batch)
            inline_ok = True
        except Exception as e:
            log.warning("Inline review batch %d failed (%s) — will include in body", i, e)
            break

    # Fallback: include all findings as a formatted body-only review
    if not inline_ok and comments:
        lines = [header, "### Findings\n"]
        for c in comments:
            lines.append(f"- `{c['path']}:{c['line']}` — {c['body'].splitlines()[0]}")
        body = "\n".join(lines)
        try:
            gh.post_review(pr_number, head_sha, body, event, [])
        except Exception as e:
            log.warning("Body-only review also failed: %s", e)


def _build_summary(
    findings: list[dict],
    score: float,
    iterations: int,
    suggestions_made: int,
    threshold: int,
) -> str:
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D"
    passed = score >= threshold and not _blocking_issues(findings)

    by_sev = {}
    for f in findings:
        s = f.get("severity", "info")
        by_sev[s] = by_sev.get(s, 0) + 1

    status_line = "✅ **Quality gate passed**" if passed else "❌ **Quality gate failed — human review required**"

    lines = [
        f"## AI Engineering Review — Grade {grade} ({score:.0f}/100)",
        "",
        status_line,
        "",
        "### Findings Summary",
        f"| Severity | Count |",
        f"|----------|-------|",
    ]
    for sev in ("critical", "high", "medium", "low", "info"):
        n = by_sev.get(sev, 0)
        if n:
            lines.append(f"| {sev.capitalize()} | {n} |")

    lines += [
        "",
        f"### Actions Taken",
        f"- 🔍 Completed {iterations} review pass(es)",
        f"- 💡 Posted {len(findings)} inline finding(s)",
        f"- ✨ {suggestions_made} suggestion block(s) added (click **Apply suggestion** to fix with 1 click)",
        "",
        "### Guardrails",
        "- 🔒 This AI **never auto-merges** — explicit human approval required",
        "- 🔒 Critical and security issues are always escalated to human reviewers",
        "- 🤖 AI acts as a junior partner — humans own architecture and business logic decisions",
        "",
    ]

    if _blocking_issues(findings):
        lines += [
            "### ⚠️ Blocking Issues",
            "The following findings must be addressed by a human engineer before merge:",
            "",
        ]
        for f in _blocking_issues(findings):
            lines.append(f"- `{f.get('file_path', '?')}:{f.get('line', '?')}` — {f.get('issue', '')}")

    lines += ["", "---", "*Generated by Engineering Review Platform · AI Junior Partner Mode*"]
    return "\n".join(lines)
