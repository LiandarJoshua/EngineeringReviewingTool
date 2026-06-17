from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models import User, Repository, Review, Finding, DeveloperProgress


# --- Users ---

async def get_or_create_user(db: AsyncSession, email: str, experience_level: str = "mid") -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email=email, experience_level=experience_level)
        db.add(user)
        await db.flush()
    return user


# --- Repositories ---

async def get_or_create_repo(db: AsyncSession, user_id: UUID, repo_url: str) -> Repository:
    result = await db.execute(
        select(Repository).where(Repository.user_id == user_id, Repository.repo_url == repo_url)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        repo = Repository(user_id=user_id, repo_url=repo_url)
        db.add(repo)
        await db.flush()
    return repo


async def update_repo_metadata(db: AsyncSession, repo_id: UUID, stack: dict) -> None:
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if repo:
        repo.language = stack.get("language")
        repo.framework = stack.get("framework")
        repo.package_manager = stack.get("package_manager")
        repo.repo_name = stack.get("repo_name", repo.repo_url.split("/")[-1])


# --- Reviews ---

async def create_review_record(db: AsyncSession, repo_id: UUID) -> Review:
    review = Review(repository_id=repo_id, status="pending")
    db.add(review)
    await db.flush()
    return review


async def update_review_status(db: AsyncSession, review_id: UUID, status: str) -> None:
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if review:
        review.status = status


async def update_review_scores(db: AsyncSession, review_id: UUID, scores: dict, raw_output: dict) -> None:
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if review:
        review.overall_score = scores.get("overall")
        review.security_score = scores.get("security")
        review.architecture_score = scores.get("architecture")
        review.testing_score = scores.get("testing")
        review.scalability_score = scores.get("scalability")
        review.debt_score = scores.get("debt")
        review.raw_output = raw_output
        review.status = "complete"


async def get_review_by_id(db: AsyncSession, review_id: UUID) -> Optional[Review]:
    result = await db.execute(select(Review).where(Review.id == review_id))
    return result.scalar_one_or_none()


async def list_reviews(db: AsyncSession, limit: int = 20, offset: int = 0) -> List[dict]:
    q = (
        select(Review, Repository.repo_url, Repository.repo_name, User.email)
        .join(Repository, Review.repository_id == Repository.id)
        .join(User, Repository.user_id == User.id)
        .order_by(Review.generated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(q)
    rows = result.all()
    return [
        {
            "id": str(r.Review.id),
            "status": r.Review.status,
            "overall_score": r.Review.overall_score,
            "security_score": r.Review.security_score,
            "architecture_score": r.Review.architecture_score,
            "testing_score": r.Review.testing_score,
            "scalability_score": r.Review.scalability_score,
            "debt_score": r.Review.debt_score,
            "repo_url": r.repo_url,
            "repo_name": r.repo_name or r.repo_url.split("/")[-1],
            "user_email": r.email,
            "created_at": r.Review.generated_at.isoformat() if r.Review.generated_at else None,
        }
        for r in rows
    ]


# --- Findings ---

async def bulk_insert_findings(db: AsyncSession, review_id: UUID, findings: List[dict]) -> None:
    for f in findings:
        raw_cwe = f.get("cwe_reference") or f.get("cwe")
        cwe_str = str(raw_cwe) if raw_cwe is not None else None

        raw_line = f.get("line_number")
        line_int = int(raw_line) if raw_line is not None and str(raw_line).isdigit() else None

        finding = Finding(
            review_id=review_id,
            agent_name=f.get("agent_name"),
            severity=str(f.get("severity", "info")).lower(),
            category=f.get("category"),
            issue=f.get("issue"),
            recommendation=f.get("recommendation"),
            file_path=f.get("file_path"),
            line_number=line_int,
            cwe_reference=cwe_str,
        )
        db.add(finding)


async def get_findings(
    db: AsyncSession, review_id: UUID,
    severity: Optional[str] = None, agent: Optional[str] = None,
    limit: int = 100, offset: int = 0,
) -> List[Finding]:
    q = select(Finding).where(Finding.review_id == review_id)
    if severity:
        q = q.where(Finding.severity == severity)
    if agent:
        q = q.where(Finding.agent_name == agent)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


# --- Developer Progress ---

async def record_progress(db: AsyncSession, user_id: UUID, repo_id: UUID, review_id: UUID, scores: dict) -> None:
    result = await db.execute(
        select(func.count()).select_from(DeveloperProgress)
        .where(DeveloperProgress.user_id == user_id, DeveloperProgress.repository_id == repo_id)
    )
    review_number = (result.scalar() or 0) + 1

    progress = DeveloperProgress(
        user_id=user_id,
        repository_id=repo_id,
        review_id=review_id,
        review_number=review_number,
        security_score=scores.get("security"),
        architecture_score=scores.get("architecture"),
        testing_score=scores.get("testing"),
        scalability_score=scores.get("scalability"),
        debt_score=scores.get("debt"),
        overall_score=scores.get("overall"),
    )
    db.add(progress)


async def get_past_review_scores(user_id: str, repo_id: str, limit: int = 5) -> List[dict]:
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DeveloperProgress)
            .where(
                DeveloperProgress.user_id == UUID(user_id),
                DeveloperProgress.repository_id == UUID(repo_id),
            )
            .order_by(DeveloperProgress.review_number)
            .limit(limit)
        )
        rows = result.scalars().all()
        return [
            {
                "review_number": r.review_number,
                "security": r.security_score,
                "architecture": r.architecture_score,
                "testing": r.testing_score,
                "scalability": r.scalability_score,
                "overall": r.overall_score,
            }
            for r in rows
        ]
