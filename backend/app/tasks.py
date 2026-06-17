import asyncio
from datetime import datetime, timedelta
from app.worker import celery_app
from app.agents.state import ALL_STAGES


@celery_app.task(bind=True, name="app.tasks.run_review")
def run_review(self, review_id: str, repo_url: str, user_id: str, pdf_path: str = None):
    from app.agents.orchestrator import build_review_graph
    from app.storage.redis_cache import publish_progress, is_cancelled, set_task_id

    # Store task id so cancel endpoint can revoke it
    set_task_id(review_id, self.request.id)

    graph = build_review_graph()
    initial_state = {
        "review_id": review_id,
        "repo_id": "",
        "repo_url": repo_url,
        "user_id": user_id,
        "requirements_pdf_path": pdf_path,
        "local_path": "",
        "stack": {},
        "parsed_files": [],
        "architecture_findings": [],
        "security_findings": [],
        "scalability_findings": [],
        "testing_findings": [],
        "debt_findings": [],
        "requirements_alignment": [],
        "coaching_report": {},
        "prioritized_findings": [],
        "final_report": {},
        "scores": {},
        "stage_status": {stage: "pending" for stage in ALL_STAGES},
        "errors": [],
    }

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    final_state = None
    try:
        for event in graph.stream(initial_state):
            if is_cancelled(review_id):
                _mark_cancelled_in_db(review_id)
                return {"status": "cancelled", "review_id": review_id}
            stage = list(event.keys())[0]
            loop.run_until_complete(publish_progress(review_id, stage, "complete"))
            final_state = list(event.values())[0]
    finally:
        loop.close()

    if final_state:
        _persist_results(review_id, final_state)

    return {"status": "complete", "review_id": review_id}


def _mark_cancelled_in_db(review_id: str) -> None:
    from uuid import UUID
    from app.db.session import AsyncSessionLocal
    from app.storage.postgres_store import update_review_status

    async def _write():
        async with AsyncSessionLocal() as db:
            await update_review_status(db, UUID(review_id), "cancelled")
            await db.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_write())
    finally:
        loop.close()


def _persist_results(review_id: str, state: dict) -> None:
    from uuid import UUID
    from sqlalchemy import select, desc
    from app.db.session import AsyncSessionLocal
    from app.db.models import DeveloperProgress
    from app.storage.postgres_store import (
        update_review_scores, bulk_insert_findings, record_progress
    )

    async def _write():
        async with AsyncSessionLocal() as db:
            new_scores = state.get("scores", {})
            await update_review_scores(db, UUID(review_id), new_scores, state.get("final_report", {}))
            await bulk_insert_findings(db, UUID(review_id), state.get("prioritized_findings", []))
            if state.get("user_id") and state.get("repo_id"):
                await record_progress(
                    db, UUID(state["user_id"]), UUID(state["repo_id"]),
                    UUID(review_id), new_scores,
                )

            # Regression detection — compare new overall score to previous
            if state.get("repo_id") and new_scores.get("overall") is not None:
                prev = await db.execute(
                    select(DeveloperProgress)
                    .where(DeveloperProgress.repository_id == UUID(state["repo_id"]))
                    .order_by(desc(DeveloperProgress.recorded_at))
                    .offset(1).limit(1)
                )
                prev_entry = prev.scalar_one_or_none()
                if prev_entry and prev_entry.overall_score is not None:
                    drop = prev_entry.overall_score - new_scores["overall"]
                    if drop >= 10:
                        _flag_regression(
                            repo_url=state.get("repo_url", ""),
                            new_score=new_scores["overall"],
                            prev_score=prev_entry.overall_score,
                            drop=drop,
                            scores=new_scores,
                        )

            await db.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_write())
    finally:
        loop.close()


def _flag_regression(repo_url: str, new_score: float, prev_score: float, drop: float, scores: dict) -> None:
    """Open a GitHub issue when repo health score drops by ≥10 points."""
    import re
    from app.config import get_settings
    settings = get_settings()
    token = getattr(settings, "github_token", "")
    if not token or not repo_url:
        return

    # Derive owner/repo from URL (https://github.com/owner/repo)
    match = re.search(r"github\.com[/:]([^/]+/[^/\s\.]+)", repo_url)
    if not match:
        return

    repo_full_name = match.group(1).rstrip(".git")
    try:
        from app.integrations.github_client import GitHubClient
        gh = GitHubClient(token, repo_full_name)

        def _grade(s: float) -> str:
            return "A" if s >= 80 else "B" if s >= 65 else "C" if s >= 50 else "D"

        body = f"""## ⚠️ Code Health Regression Detected

The overall code health score has dropped **{drop:.0f} points** since the last review.

| | Previous | Current |
|--|--|--|
| **Overall** | {prev_score:.0f}/100 ({_grade(prev_score)}) | {new_score:.0f}/100 ({_grade(new_score)}) |
| Security | — | {scores.get('security', 0):.0f}/100 |
| Architecture | — | {scores.get('architecture', 0):.0f}/100 |
| Testing | — | {scores.get('testing', 0):.0f}/100 |
| Scalability | — | {scores.get('scalability', 0):.0f}/100 |
| Technical Debt | — | {scores.get('debt', 0):.0f}/100 |

### What to do

1. Open the [Engineering Review Platform](http://localhost:3000) and review the latest findings
2. Focus on any new **critical** or **high** severity findings
3. Address root causes before the next release

---
> 🤖 **This issue was opened automatically by the AI Engineering Review system.**
> All fixes and merge decisions require **explicit human approval**.
> The AI never auto-merges or auto-resolves issues.

*Close this issue once the regression has been investigated and addressed.*
"""
        gh.create_issue(
            title=f"⚠️ Code health regression: {prev_score:.0f} → {new_score:.0f} ({drop:.0f} point drop)",
            body=body,
            labels=["ai:regression", "needs-attention"],
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to create regression issue: %s", e)


@celery_app.task(bind=True, name="app.tasks.run_coaching")
def run_coaching(self, review_id: str, user_id: str, experience_level: str = "mid"):
    """Generate a coaching report from stored findings and scores."""
    from uuid import UUID
    from app.db.session import AsyncSessionLocal
    from app.storage.postgres_store import get_review_by_id, get_findings
    from app.agents.stage_09_coaching import run as coaching_run
    import asyncio

    async def _load():
        async with AsyncSessionLocal() as db:
            review = await get_review_by_id(db, UUID(review_id))
            findings = await get_findings(db, UUID(review_id), limit=200)
            return review, findings

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        review, findings = loop.run_until_complete(_load())
    finally:
        loop.close()

    if not review:
        return {"status": "error", "message": "Review not found"}

    scores = {
        "security":     review.security_score,
        "architecture": review.architecture_score,
        "testing":      review.testing_score,
        "scalability":  review.scalability_score,
        "debt":         review.debt_score,
        "overall":      review.overall_score,
    }

    # Build a minimal state for the coaching stage
    all_findings = [
        {
            "severity":       f.severity,
            "category":       f.category,
            "issue":          f.issue,
            "recommendation": f.recommendation,
            "agent_name":     f.agent_name,
        }
        for f in findings
    ]

    state = {
        "review_id":           review_id,
        "user_id":             user_id,
        "repo_id":             str(review.repository_id),
        "experience_level":    experience_level,
        "scores":              scores,
        "architecture_findings": [f for f in all_findings if f.get("agent_name") == "architecture"],
        "security_findings":   [f for f in all_findings if f.get("agent_name") in ("semgrep", "bandit", "security_llm")],
        "scalability_findings": [f for f in all_findings if f.get("agent_name") == "scalability"],
        "testing_findings":    [f for f in all_findings if f.get("agent_name") == "testing"],
        "debt_findings":       [f for f in all_findings if f.get("agent_name") == "debt"],
    }

    result = coaching_run(state)
    coaching_report = result.get("coaching_report", {})

    # Merge into raw_output
    async def _save():
        from sqlalchemy import select
        from app.db.models import Review
        async with AsyncSessionLocal() as db:
            r = (await db.execute(select(Review).where(Review.id == UUID(review_id)))).scalar_one_or_none()
            if r:
                raw = dict(r.raw_output or {})
                raw["coaching_report"] = coaching_report
                r.raw_output = raw
                await db.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_save())
    finally:
        loop.close()

    return {"status": "complete", "review_id": review_id}


@celery_app.task(bind=True, name="app.tasks.run_pr_review", queue="reviews")
def run_pr_review(
    self,
    repo_full_name: str,
    pr_number: int,
    head_sha: str,
    github_token: str,
    pr_title: str = "",
    pr_description: str = "",
    author: str = "",
    base_branch: str = "main",
    experience_level: str = "mid",
    quality_threshold: int = 70,
):
    """PIV loop: fetch PR diff → review agents → inline comments → self-correction."""
    from app.integrations.github_client import GitHubClient
    from app.integrations.pr_context import build_pr_context
    from app.agents.pr_review_loop import run as piv_run

    gh = GitHubClient(github_token, repo_full_name)

    # Fetch PR metadata and diff
    pr_meta    = gh.get_pr(pr_number)
    diff_text  = gh.get_pr_diff(pr_number)
    pr_files   = gh.get_pr_files(pr_number)

    file_contents = {}
    for f in pr_files[:25]:
        content = gh.get_file_content(f["filename"], head_sha)
        if content:
            file_contents[f["filename"]] = content

    pr_context = build_pr_context(diff_text, pr_meta, file_contents)

    result = piv_run(
        pr_context=pr_context,
        github_token=github_token,
        repo_full_name=repo_full_name,
        experience_level=experience_level,
        quality_threshold=quality_threshold,
        skill_names=None,  # all skills by default
    )
    return {"status": "complete", **result}


@celery_app.task(bind=True, name="app.tasks.run_targeted_pr_review", queue="reviews")
def run_targeted_pr_review(
    self,
    repo_full_name: str,
    pr_number: int,
    head_sha: str,
    github_token: str,
    skill_names: list[str],
    triggered_by: str = "",
):
    """Targeted PR review triggered by a /review comment. Runs only specified skills."""
    from app.integrations.github_client import GitHubClient
    from app.integrations.pr_context import build_pr_context
    from app.agents.pr_review_loop import run as piv_run

    gh = GitHubClient(github_token, repo_full_name)
    pr_meta   = gh.get_pr(pr_number)
    diff_text = gh.get_pr_diff(pr_number)
    pr_files  = gh.get_pr_files(pr_number)

    file_contents = {}
    for f in pr_files[:25]:
        content = gh.get_file_content(f["filename"], head_sha)
        if content:
            file_contents[f["filename"]] = content

    pr_context = build_pr_context(diff_text, pr_meta, file_contents)

    result = piv_run(
        pr_context=pr_context,
        github_token=github_token,
        repo_full_name=repo_full_name,
        skill_names=skill_names,
    )
    return {"status": "complete", "triggered_by": triggered_by, **result}


@celery_app.task(bind=True, name="app.tasks.run_push_security_scan", queue="reviews")
def run_push_security_scan(
    self,
    repo_full_name: str,
    head_sha: str,
    pusher: str,
    ref: str,
    github_token: str,
):
    """Security + logic scan triggered by a push to the default branch.
    Posts a ✅/❌ commit status. Never blocks or auto-reverts — humans decide.
    """
    from app.integrations.github_client import GitHubClient
    from app.agents.skills import SecurityScanSkill, LogicReviewSkill
    from app.agents.llm_client import get_ollama_llm

    gh = GitHubClient(github_token, repo_full_name)
    branch = ref.replace("refs/heads/", "")

    gh.post_commit_status(head_sha, "pending", "AI security scan in progress…", "ai/security-scan")

    try:
        diff_text = gh.get_commit_diff(head_sha)
        files     = gh.get_commit_files(head_sha)
        changed   = [f["filename"] for f in files]

        pr_context = {
            "pr_number": 0,
            "head_sha": head_sha,
            "pr_title": f"Push to {branch} by {pusher}",
            "pr_description": "",
            "diff_summary": diff_text[:12000],
            "changed_files": changed,
            "stack": {},
        }

        llm = get_ollama_llm()
        findings = []
        for skill in [SecurityScanSkill(), LogicReviewSkill()]:
            try:
                findings.extend(skill.run(pr_context, llm))
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("Skill %s failed: %s", skill.name, e)

        critical_or_high = [f for f in findings if f.get("severity") in ("critical", "high")]
        security_issues  = [f for f in findings if f.get("category") in ("security", "authentication", "authorization")]

        if critical_or_high or security_issues:
            count = len(critical_or_high)
            gh.post_commit_status(
                head_sha, "failure",
                f"⚠️ {count} critical/high issue(s) found — human review required",
                "ai/security-scan",
            )
        else:
            gh.post_commit_status(
                head_sha, "success",
                f"✓ {len(findings)} finding(s), none critical — human review still recommended",
                "ai/security-scan",
            )

        return {"status": "complete", "findings": len(findings), "blocking": len(critical_or_high)}

    except Exception as e:
        gh.post_commit_status(head_sha, "error", "Security scan failed — check logs", "ai/security-scan")
        raise


@celery_app.task(name="app.tasks.check_scheduled_scans")
def check_scheduled_scans():
    """Runs every hour via Celery Beat. Fires reviews for any due scheduled scans."""
    from sqlalchemy import select
    from app.db.models import ScheduledScan, User, Repository, Review

    async def _run():
        from app.db.session import AsyncSessionLocal
        from app.storage.postgres_store import get_or_create_user, get_or_create_repo, create_review_record
        async with AsyncSessionLocal() as db:
            now = datetime.utcnow()
            due = (
                await db.execute(
                    select(ScheduledScan).where(
                        ScheduledScan.is_active == True,
                        ScheduledScan.next_run_at <= now,
                    )
                )
            ).scalars().all()

            fired = 0
            for scan in due:
                user = await get_or_create_user(db, scan.user_email or "scheduled@system", "mid")
                repo = await get_or_create_repo(db, user.id, scan.repo_url)
                review = await create_review_record(db, repo.id)
                await db.flush()

                run_review.apply_async(
                    kwargs={
                        "review_id": str(review.id),
                        "repo_url": scan.repo_url,
                        "user_id": str(user.id),
                    },
                    queue="reviews",
                )

                scan.last_run_at = now
                scan.next_run_at = now + timedelta(hours=scan.interval_hours)
                fired += 1

            await db.commit()
            return fired

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        fired = loop.run_until_complete(_run())
    finally:
        loop.close()
    return {"fired": fired}
