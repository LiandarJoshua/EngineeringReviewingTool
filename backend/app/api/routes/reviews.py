from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_auth
from app.storage import postgres_store, minio_store
from app.tasks import run_review

router = APIRouter(prefix="/reviews", tags=["reviews"])


class ReviewCreateResponse(BaseModel):
    review_id: str
    job_id: str
    status: str


class ReviewResponse(BaseModel):
    id: str
    status: str
    overall_score: Optional[float]
    security_score: Optional[float]
    architecture_score: Optional[float]
    testing_score: Optional[float]
    scalability_score: Optional[float]
    debt_score: Optional[float]
    coaching_report: Optional[dict] = None


class ReviewListItem(BaseModel):
    id: str
    status: str
    overall_score: Optional[float]
    security_score: Optional[float]
    architecture_score: Optional[float]
    testing_score: Optional[float]
    scalability_score: Optional[float]
    debt_score: Optional[float]
    repo_url: str
    repo_name: str
    user_email: str
    created_at: Optional[str]


class FindingResponse(BaseModel):
    id: str
    agent_name: Optional[str]
    severity: Optional[str]
    category: Optional[str]
    issue: Optional[str]
    recommendation: Optional[str]
    file_path: Optional[str]
    line_number: Optional[int]


@router.get("/", response_model=List[ReviewListItem])
async def list_reviews(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Return most recent reviews across all users."""
    return await postgres_store.list_reviews(db, limit=limit, offset=offset)


@router.post("/", response_model=ReviewCreateResponse)
async def create_review(
    repo_url: str = Form(...),
    user_email: str = Form(...),
    experience_level: str = Form("mid"),
    requirements_pdf: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    """Submit a repository for review. Returns job_id immediately."""
    user = await postgres_store.get_or_create_user(db, user_email, experience_level)
    repo = await postgres_store.get_or_create_repo(db, user.id, repo_url)
    review = await postgres_store.create_review_record(db, repo.id)

    pdf_path = None
    if requirements_pdf:
        pdf_bytes = await requirements_pdf.read()
        object_name = f"requirements/{review.id}/{requirements_pdf.filename}"
        pdf_path = minio_store.upload_bytes(pdf_bytes, object_name, content_type="application/pdf")

    task = run_review.delay(
        str(review.id), repo_url, str(user.id), pdf_path
    )

    return {"review_id": str(review.id), "job_id": task.id, "status": "queued"}


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: UUID, db: AsyncSession = Depends(get_db)):
    review = await postgres_store.get_review_by_id(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    raw = review.raw_output or {}
    return {
        "id": str(review.id),
        "status": review.status,
        "overall_score": review.overall_score,
        "security_score": review.security_score,
        "architecture_score": review.architecture_score,
        "testing_score": review.testing_score,
        "scalability_score": review.scalability_score,
        "debt_score": review.debt_score,
        "coaching_report": raw.get("coaching_report"),
    }


@router.get("/{review_id}/findings", response_model=List[FindingResponse])
async def get_findings(
    review_id: UUID,
    severity: Optional[str] = None,
    agent: Optional[str] = None,
    page: int = 1,
    size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    findings = await postgres_store.get_findings(
        db, review_id, severity=severity, agent=agent,
        limit=size, offset=(page - 1) * size,
    )
    return [
        {
            "id": str(f.id), "agent_name": f.agent_name, "severity": f.severity,
            "category": f.category, "issue": f.issue, "recommendation": f.recommendation,
            "file_path": f.file_path, "line_number": f.line_number,
        }
        for f in findings
    ]


@router.post("/{review_id}/cancel")
async def cancel_review(review_id: UUID, db: AsyncSession = Depends(get_db), _: str = Depends(require_auth)):
    """Cancel a running or pending review."""
    review = await postgres_store.get_review_by_id(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.status not in ("pending", "running"):
        raise HTTPException(status_code=400, detail=f"Review is already {review.status}")

    from app.storage.redis_cache import mark_cancelled, get_task_id
    mark_cancelled(str(review_id))

    task_id = get_task_id(str(review_id))
    if task_id:
        from app.worker import celery_app
        celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")

    await postgres_store.update_review_status(db, review_id, "cancelled")
    await db.commit()
    return {"status": "cancelled", "review_id": str(review_id)}


@router.delete("/{review_id}")
async def delete_review(review_id: UUID, db: AsyncSession = Depends(get_db), _: str = Depends(require_auth)):
    """Permanently delete a review and all its findings."""
    from sqlalchemy import delete as sql_delete
    from app.db.models import Review

    review = await postgres_store.get_review_by_id(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.status in ("pending", "running"):
        from app.storage.redis_cache import mark_cancelled, get_task_id
        mark_cancelled(str(review_id))
        task_id = get_task_id(str(review_id))
        if task_id:
            from app.worker import celery_app
            celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")

    await db.execute(sql_delete(Review).where(Review.id == review_id))
    await db.commit()
    return {"deleted": True, "review_id": str(review_id)}


@router.post("/{review_id}/coaching")
async def generate_coaching(
    review_id: UUID,
    experience_level: str = "mid",
    db: AsyncSession = Depends(get_db),
):
    """Generate or regenerate the coaching report for a completed review."""
    from app.tasks import run_coaching

    review = await postgres_store.get_review_by_id(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.status not in ("complete", "failed"):
        raise HTTPException(status_code=400, detail="Review must be complete before generating coaching")

    # Get the user_id via repository
    from sqlalchemy import select
    from app.db.models import Repository
    repo = (await db.execute(select(Repository).where(Repository.id == review.repository_id))).scalar_one_or_none()
    user_id = str(repo.user_id) if repo else ""

    task = run_coaching.delay(str(review_id), user_id, experience_level)
    return {"job_id": task.id, "status": "generating", "review_id": str(review_id)}


@router.get("/users/{user_id}/progress")
async def get_progress(user_id: str, repo_id: str, db: AsyncSession = Depends(get_db)):
    scores = await postgres_store.get_past_review_scores(user_id, repo_id)
    return {"user_id": user_id, "repo_id": repo_id, "history": scores}
