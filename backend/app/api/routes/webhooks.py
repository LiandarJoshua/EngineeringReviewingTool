"""GitHub webhook receiver + direct PR review trigger endpoint.

Handles four event types:
  pull_request  opened/synchronize/reopened  → PR review (existing)
  pull_request  closed + merged              → full repo health review
  push          default branch               → security + logic scan (commit status)
  issue_comment created, /review command     → targeted PR review bot

Guardrails (enforced here and in all downstream tasks):
  - AI NEVER auto-merges
  - AI NEVER sends APPROVE to GitHub
  - All automated comments state human sign-off is required
  - Bot only responds to /review on PRs, not plain issues
"""
import hashlib
import hmac
import logging
import re
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from pydantic import BaseModel

from app.config import get_settings

router   = APIRouter(prefix="/webhooks", tags=["webhooks"])
log      = logging.getLogger(__name__)
settings = get_settings()

# Maps /review command → skill names (None = all)
COMMAND_SKILL_MAP: dict[str, list[str] | None] = {
    "/review":          None,                          # all skills
    "/review security": ["security_scan"],
    "/review style":    ["style_check"],
    "/review logic":    ["logic_review"],
    "/review tests":    ["test_coverage"],
    "/re-review":       None,
}


# ── Pydantic models ───────────────────────────────────────────────────────────

class PRReviewRequest(BaseModel):
    repo_full_name:    str
    pr_number:         int
    head_sha:          str
    pr_title:          str = ""
    pr_description:    str = ""
    author:            str = ""
    base_branch:       str = "main"
    github_token:      str
    experience_level:  str = "mid"
    quality_threshold: int = 70


class PRReviewResponse(BaseModel):
    pr_review_id: str
    status:       str
    message:      str


# ── Main webhook endpoint ─────────────────────────────────────────────────────

@router.post("/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str]      = Header(None),
):
    body = await request.body()

    # HMAC signature validation
    secret = getattr(settings, "github_webhook_secret", None)
    if secret:
        expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(x_hub_signature_256 or "", expected):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload      = await request.json()
    github_token = getattr(settings, "github_token", None)

    if not github_token:
        log.warning("GITHUB_TOKEN not set — cannot process webhook events")
        return {"queued": False, "reason": "GITHUB_TOKEN not configured"}

    event = x_github_event or ""

    if event == "pull_request":
        return _handle_pull_request(payload, github_token)

    if event == "push":
        return _handle_push(payload, github_token)

    if event == "issue_comment":
        return await _handle_issue_comment(payload, github_token)

    return {"ignored": True, "event": event}


# ── Event handlers ────────────────────────────────────────────────────────────

def _handle_pull_request(payload: dict, github_token: str) -> dict:
    """Route PR events: open/update → PR review. Merged → full repo review."""
    action = payload.get("action", "")
    pr     = payload.get("pull_request", {})
    repo   = payload.get("repository", {}).get("full_name", "")

    # Existing: PR opened/updated → PIV review
    if action in ("opened", "synchronize", "reopened"):
        _queue_pr_review(
            repo_full_name=repo,
            pr_number=pr.get("number"),
            head_sha=pr.get("head", {}).get("sha", ""),
            pr_title=pr.get("title", ""),
            pr_description=pr.get("body", "") or "",
            author=pr.get("user", {}).get("login", ""),
            base_branch=pr.get("base", {}).get("ref", "main"),
            github_token=github_token,
        )
        return {"queued": True, "event": "pr_review", "pr": pr.get("number"), "action": action}

    # New: PR merged → queue full 11-stage repo health review
    if action == "closed" and pr.get("merged"):
        repo_url = pr.get("base", {}).get("repo", {}).get("clone_url", "") or f"https://github.com/{repo}"
        merger   = pr.get("merged_by", {}).get("login", "unknown")
        log.info("PR #%s merged by %s — queuing full repo review for %s", pr.get("number"), merger, repo)
        _queue_full_review(repo_url=repo_url, triggered_by=merger)
        return {"queued": True, "event": "post_merge_review", "pr": pr.get("number"), "merger": merger}

    return {"ignored": True, "action": action}


def _handle_push(payload: dict, github_token: str) -> dict:
    """Push to default branch → lightweight security + logic scan with commit status."""
    ref      = payload.get("ref", "")
    repo     = payload.get("repository", {})
    default  = repo.get("default_branch", "main")

    # Only scan pushes to the default branch
    if ref != f"refs/heads/{default}":
        return {"ignored": True, "reason": f"push to {ref}, not default branch"}

    head_sha = payload.get("after", "")
    pusher   = payload.get("pusher", {}).get("name", "unknown")
    repo_full_name = repo.get("full_name", "")

    if not head_sha or head_sha == "0" * 40:
        return {"ignored": True, "reason": "branch deleted push"}

    log.info("Push to %s by %s — queuing security scan for %s", default, pusher, repo_full_name)

    try:
        from app.tasks import run_push_security_scan
        run_push_security_scan.apply_async(
            kwargs={
                "repo_full_name": repo_full_name,
                "head_sha": head_sha,
                "pusher": pusher,
                "ref": ref,
                "github_token": github_token,
            },
            queue="reviews",
        )
    except Exception as e:
        log.error("Failed to queue push security scan: %s", e)

    return {"queued": True, "event": "push_security_scan", "sha": head_sha[:8], "pusher": pusher}


async def _handle_issue_comment(payload: dict, github_token: str) -> dict:
    """Parse /review commands from PR comments. Ignores plain issue comments."""
    action  = payload.get("action", "")
    if action != "created":
        return {"ignored": True, "reason": "not a new comment"}

    issue   = payload.get("issue", {})
    comment = payload.get("comment", {})
    repo    = payload.get("repository", {}).get("full_name", "")

    # Only respond to comments on PRs (issues have no pull_request key)
    if "pull_request" not in issue:
        return {"ignored": True, "reason": "comment on issue, not PR"}

    # Skip bot comments to prevent loops
    commenter = comment.get("user", {}).get("login", "")
    commenter_type = comment.get("user", {}).get("type", "")
    if commenter_type == "Bot" or "[bot]" in commenter:
        return {"ignored": True, "reason": "bot comment"}

    body = (comment.get("body") or "").strip().lower()

    # Find matching command
    skill_names: list[str] | None | bool = False  # False = no command matched
    for cmd, skills in COMMAND_SKILL_MAP.items():
        if body.startswith(cmd):
            skill_names = skills
            break

    if skill_names is False:
        return {"ignored": True, "reason": "no /review command found"}

    pr_number = issue.get("number")
    log.info("/review command from %s on PR #%s in %s", commenter, pr_number, repo)

    # Acknowledge immediately so the user knows we're working on it
    skill_label = _skill_label(skill_names)
    ack_body = _build_ack_comment(commenter, skill_label)
    await _post_ack_comment(github_token, repo, pr_number, ack_body)

    # Fetch PR head SHA (needed for inline comments)
    try:
        from app.integrations.github_client import GitHubClient
        gh     = GitHubClient(github_token, repo)
        pr_data = gh.get_pr(pr_number)
        head_sha = pr_data.get("head", {}).get("sha", "")
    except Exception as e:
        log.error("Could not fetch PR #%s details: %s", pr_number, e)
        return {"queued": False, "reason": "could not fetch PR details"}

    try:
        from app.tasks import run_targeted_pr_review
        run_targeted_pr_review.apply_async(
            kwargs={
                "repo_full_name": repo,
                "pr_number": pr_number,
                "head_sha": head_sha,
                "github_token": github_token,
                "skill_names": skill_names,  # None = all, list = targeted
                "triggered_by": commenter,
            },
            queue="reviews",
        )
    except Exception as e:
        log.error("Failed to queue targeted PR review: %s", e)
        return {"queued": False, "reason": str(e)}

    return {"queued": True, "event": "comment_bot", "pr": pr_number, "skills": skill_names, "by": commenter}


# ── Direct trigger endpoint ───────────────────────────────────────────────────

@router.post("/pr-review", response_model=PRReviewResponse)
async def trigger_pr_review(req: PRReviewRequest, background_tasks: BackgroundTasks):
    """Manual trigger — called by GitHub Actions workflow or the PR Reviews UI."""
    import uuid
    pr_review_id = str(uuid.uuid4())

    background_tasks.add_task(
        _run_pr_review_task,
        pr_review_id=pr_review_id,
        repo_full_name=req.repo_full_name,
        pr_number=req.pr_number,
        head_sha=req.head_sha,
        pr_title=req.pr_title,
        pr_description=req.pr_description,
        author=req.author,
        base_branch=req.base_branch,
        github_token=req.github_token,
        experience_level=req.experience_level,
        quality_threshold=req.quality_threshold,
    )

    return PRReviewResponse(
        pr_review_id=pr_review_id,
        status="queued",
        message=f"PR #{req.pr_number} review queued — results will be posted as GitHub comments",
    )


# ── Task dispatch helpers ─────────────────────────────────────────────────────

def _queue_pr_review(**kwargs) -> None:
    try:
        from app.tasks import run_pr_review
        run_pr_review.apply_async(kwargs=kwargs, queue="reviews")
        log.info("PR review task queued for PR #%s", kwargs.get("pr_number"))
    except Exception as e:
        log.error("Failed to queue PR review task: %s", e)


def _queue_full_review(repo_url: str, triggered_by: str = "") -> None:
    """Queue a full 11-stage repo review after a PR merge."""
    try:
        from app.tasks import run_review
        from app.storage.postgres_store import get_or_create_user, get_or_create_repo, create_review_record
        import asyncio

        async def _setup():
            from app.db.session import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                user   = await get_or_create_user(db, f"{triggered_by}@github" if triggered_by else "auto@system")
                repo   = await get_or_create_repo(db, user.id, repo_url)
                review = await create_review_record(db, repo.id)
                await db.commit()
                return str(review.id), str(user.id)

        loop = asyncio.new_event_loop()
        try:
            review_id, user_id = loop.run_until_complete(_setup())
        finally:
            loop.close()

        run_review.apply_async(
            kwargs={"review_id": review_id, "repo_url": repo_url, "user_id": user_id},
            queue="reviews",
        )
        log.info("Full repo review queued after merge: review_id=%s", review_id)
    except Exception as e:
        log.error("Failed to queue post-merge review: %s", e)


async def _run_pr_review_task(pr_review_id: str, **kwargs) -> None:
    try:
        from app.integrations.github_client import GitHubClient
        from app.integrations.pr_context import build_pr_context
        from app.agents.pr_review_loop import run as piv_run

        gh        = GitHubClient(kwargs["github_token"], kwargs["repo_full_name"])
        diff_text = gh.get_pr_diff(kwargs["pr_number"])
        files     = gh.get_pr_files(kwargs["pr_number"])
        pr_meta   = gh.get_pr(kwargs["pr_number"])

        file_contents = {}
        for f in files[:30]:
            content = gh.get_file_content(f["filename"], kwargs["head_sha"])
            if content:
                file_contents[f["filename"]] = content

        pr_context = build_pr_context(diff_text, pr_meta, file_contents)
        pr_context["pr_review_id"] = pr_review_id

        result = piv_run(
            pr_context=pr_context,
            github_token=kwargs["github_token"],
            repo_full_name=kwargs["repo_full_name"],
            experience_level=kwargs.get("experience_level", "mid"),
            quality_threshold=kwargs.get("quality_threshold", 70),
        )
        log.info("PR review complete: %s", result)
    except Exception as e:
        log.error("PR review task failed (id=%s): %s", pr_review_id, e)


# ── Comment bot helpers ───────────────────────────────────────────────────────

def _skill_label(skill_names: list[str] | None) -> str:
    if skill_names is None:
        return "full review (all checks)"
    labels = {
        "security_scan": "security scan",
        "style_check":   "style check",
        "logic_review":  "logic & bug review",
        "test_coverage": "test coverage check",
    }
    return " + ".join(labels.get(s, s) for s in skill_names)


def _build_ack_comment(commenter: str, skill_label: str) -> str:
    return f"""🤖 **AI Review Triggered** by @{commenter}

Running **{skill_label}** on this PR. Inline comments will appear shortly.

---
> ⚠️ **Human-in-the-loop reminder:** This AI acts as a junior partner — it catches syntax errors, style issues, and known patterns. Architecture decisions, business logic, and merge approval remain with the human team. The AI **never auto-merges or auto-approves**.

*Available commands: `/review` · `/review security` · `/review style` · `/review logic` · `/review tests`*
"""


async def _post_ack_comment(github_token: str, repo: str, pr_number: int, body: str) -> None:
    try:
        from app.integrations.github_client import GitHubClient
        gh = GitHubClient(github_token, repo)
        gh.post_comment(pr_number, body)
    except Exception as e:
        log.warning("Could not post ack comment on PR #%s: %s", pr_number, e)
