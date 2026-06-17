"""Finding feedback — dismiss, confirm, or mark as fixed."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import Finding, FindingFeedback
from app.api.deps import require_auth

router = APIRouter(prefix="/findings", tags=["feedback"])

VALID_ACTIONS = {"dismissed", "confirmed", "fixed"}


class FeedbackRequest(BaseModel):
    action: str   # dismissed | confirmed | fixed
    reason: str = ""


class FeedbackResponse(BaseModel):
    finding_id: str
    action: str
    reason: str


@router.post("/{finding_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    finding_id: UUID,
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    if body.action not in VALID_ACTIONS:
        raise HTTPException(status_code=400, detail=f"action must be one of {VALID_ACTIONS}")

    finding = (await db.execute(select(Finding).where(Finding.id == finding_id))).scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    existing = (
        await db.execute(select(FindingFeedback).where(FindingFeedback.finding_id == finding_id))
    ).scalar_one_or_none()

    if existing:
        existing.action = body.action
        existing.reason = body.reason
    else:
        db.add(FindingFeedback(finding_id=finding_id, action=body.action, reason=body.reason))

    await db.commit()
    return FeedbackResponse(finding_id=str(finding_id), action=body.action, reason=body.reason)


@router.get("/{finding_id}/feedback", response_model=FeedbackResponse | None)
async def get_feedback(finding_id: UUID, db: AsyncSession = Depends(get_db)):
    fb = (
        await db.execute(select(FindingFeedback).where(FindingFeedback.finding_id == finding_id))
    ).scalar_one_or_none()
    if not fb:
        return None
    return FeedbackResponse(finding_id=str(finding_id), action=fb.action, reason=fb.reason)
