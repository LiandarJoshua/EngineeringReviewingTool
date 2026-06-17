"""Scheduled repo health scan management."""
import uuid
from datetime import datetime, timedelta
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import ScheduledScan
from app.api.deps import require_auth

router = APIRouter(prefix="/schedules", tags=["schedules"])

VALID_INTERVALS = {
    "daily": 24,
    "weekly": 168,
    "monthly": 720,
}


class ScheduleCreate(BaseModel):
    repo_url: str
    user_email: str = ""
    interval: str = "weekly"   # daily | weekly | monthly


class ScheduleResponse(BaseModel):
    id: str
    repo_url: str
    repo_name: str
    user_email: str
    interval_hours: int
    interval_label: str
    is_active: bool
    last_run_at: str | None
    next_run_at: str | None
    created_at: str


def _to_response(s: ScheduledScan) -> ScheduleResponse:
    hours = s.interval_hours or 168
    label = next((k for k, v in VALID_INTERVALS.items() if v == hours), f"every {hours}h")
    return ScheduleResponse(
        id=str(s.id),
        repo_url=s.repo_url,
        repo_name=s.repo_name or s.repo_url.split("/")[-1].replace(".git", ""),
        user_email=s.user_email or "",
        interval_hours=hours,
        interval_label=label,
        is_active=s.is_active,
        last_run_at=s.last_run_at.isoformat() if s.last_run_at else None,
        next_run_at=s.next_run_at.isoformat() if s.next_run_at else None,
        created_at=s.created_at.isoformat() if s.created_at else "",
    )


@router.post("/", response_model=ScheduleResponse, status_code=201)
async def create_schedule(body: ScheduleCreate, db: AsyncSession = Depends(get_db), _: str = Depends(require_auth)):
    if body.interval not in VALID_INTERVALS:
        raise HTTPException(status_code=400, detail=f"interval must be one of {list(VALID_INTERVALS)}")

    hours = VALID_INTERVALS[body.interval]
    now = datetime.utcnow()
    scan = ScheduledScan(
        id=uuid.uuid4(),
        repo_url=body.repo_url,
        repo_name=body.repo_url.rstrip("/").split("/")[-1].replace(".git", ""),
        user_email=body.user_email,
        interval_hours=hours,
        is_active=True,
        next_run_at=now + timedelta(hours=hours),
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return _to_response(scan)


@router.get("/", response_model=List[ScheduleResponse])
async def list_schedules(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(ScheduledScan).order_by(ScheduledScan.created_at.desc()))).scalars().all()
    return [_to_response(s) for s in rows]


@router.patch("/{schedule_id}/toggle", response_model=ScheduleResponse)
async def toggle_schedule(schedule_id: UUID, db: AsyncSession = Depends(get_db), _: str = Depends(require_auth)):
    scan = (await db.execute(select(ScheduledScan).where(ScheduledScan.id == schedule_id))).scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Schedule not found")
    scan.is_active = not scan.is_active
    if scan.is_active:
        scan.next_run_at = datetime.utcnow() + timedelta(hours=scan.interval_hours)
    await db.commit()
    await db.refresh(scan)
    return _to_response(scan)


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: UUID, db: AsyncSession = Depends(get_db), _: str = Depends(require_auth)):
    scan = (await db.execute(select(ScheduledScan).where(ScheduledScan.id == schedule_id))).scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await db.delete(scan)
    await db.commit()
