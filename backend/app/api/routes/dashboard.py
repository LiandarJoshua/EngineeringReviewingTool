"""Org-level aggregate stats for the team dashboard."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.db.session import get_db
from app.db.models import Review, Finding, Repository, User, FindingFeedback

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Aggregate stats across all reviews in the system."""

    # Total counts
    total_reviews = (await db.execute(select(func.count()).select_from(Review))).scalar() or 0
    complete_reviews = (
        await db.execute(select(func.count()).select_from(Review).where(Review.status == "complete"))
    ).scalar() or 0
    total_findings = (await db.execute(select(func.count()).select_from(Finding))).scalar() or 0
    total_repos = (await db.execute(select(func.count()).select_from(Repository))).scalar() or 0

    # Average scores across all complete reviews
    avg_q = await db.execute(
        select(
            func.avg(Review.overall_score),
            func.avg(Review.security_score),
            func.avg(Review.architecture_score),
            func.avg(Review.testing_score),
            func.avg(Review.scalability_score),
            func.avg(Review.debt_score),
        ).where(Review.status == "complete")
    )
    avgs = avg_q.one()

    def _r(v):
        return round(float(v), 1) if v is not None else None

    # Findings by severity
    sev_rows = (
        await db.execute(
            select(Finding.severity, func.count().label("n"))
            .group_by(Finding.severity)
        )
    ).all()
    by_severity = {row.severity: row.n for row in sev_rows}

    # Findings by category (top 8)
    cat_rows = (
        await db.execute(
            select(Finding.category, func.count().label("n"))
            .group_by(Finding.category)
            .order_by(desc("n"))
            .limit(8)
        )
    ).all()
    by_category = [{"category": row.category, "count": row.n} for row in cat_rows]

    # Feedback stats
    fb_rows = (
        await db.execute(
            select(FindingFeedback.action, func.count().label("n"))
            .group_by(FindingFeedback.action)
        )
    ).all()
    feedback_summary = {row.action: row.n for row in fb_rows}

    # Top 10 repos by latest overall score
    repo_rows = (
        await db.execute(
            select(
                Repository.repo_name,
                Repository.repo_url,
                Review.overall_score,
                Review.security_score,
                Review.generated_at,
            )
            .join(Review, Review.repository_id == Repository.id)
            .where(Review.status == "complete", Review.overall_score.isnot(None))
            .order_by(Repository.id, desc(Review.generated_at))
            .distinct(Repository.id)
            .limit(10)
        )
    ).all()

    repos = [
        {
            "repo_name": r.repo_name or r.repo_url.split("/")[-1],
            "repo_url": r.repo_url,
            "overall_score": _r(r.overall_score),
            "security_score": _r(r.security_score),
            "last_reviewed": r.generated_at.isoformat() if r.generated_at else None,
        }
        for r in repo_rows
    ]

    # Score distribution (how many reviews in each grade bucket)
    grade_rows = (
        await db.execute(
            select(Review.overall_score)
            .where(Review.status == "complete", Review.overall_score.isnot(None))
        )
    ).scalars().all()

    grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0}
    for score in grade_rows:
        if score >= 80:
            grade_dist["A"] += 1
        elif score >= 65:
            grade_dist["B"] += 1
        elif score >= 50:
            grade_dist["C"] += 1
        else:
            grade_dist["D"] += 1

    return {
        "totals": {
            "reviews": total_reviews,
            "complete_reviews": complete_reviews,
            "findings": total_findings,
            "repos": total_repos,
        },
        "averages": {
            "overall": _r(avgs[0]),
            "security": _r(avgs[1]),
            "architecture": _r(avgs[2]),
            "testing": _r(avgs[3]),
            "scalability": _r(avgs[4]),
            "debt": _r(avgs[5]),
        },
        "by_severity": by_severity,
        "by_category": by_category,
        "feedback_summary": feedback_summary,
        "grade_distribution": grade_dist,
        "top_repos": repos,
    }
