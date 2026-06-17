import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, Text, DateTime,
    ForeignKey, Index, Boolean
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    experience_level = Column(String(50))  # junior, mid, senior, principal
    career_goal = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    repositories = relationship("Repository", back_populates="user", cascade="all, delete")
    progress = relationship("DeveloperProgress", back_populates="user", cascade="all, delete")


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    repo_url = Column(Text, nullable=False)
    repo_name = Column(String(255))
    language = Column(String(100))
    framework = Column(String(100))
    package_manager = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="repositories")
    files = relationship("File", back_populates="repository", cascade="all, delete")
    reviews = relationship("Review", back_populates="repository", cascade="all, delete")
    progress = relationship("DeveloperProgress", back_populates="repository", cascade="all, delete")


class File(Base):
    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"))
    file_path = Column(Text, nullable=False)
    file_type = Column(String(50))
    line_count = Column(Integer)
    complexity_score = Column(Float)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    repository = relationship("Repository", back_populates="files")

    __table_args__ = (
        Index("idx_files_repo", "repository_id"),
    )


class Review(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"))
    status = Column(String(50), default="pending")  # pending, running, complete, failed
    overall_score = Column(Float)
    security_score = Column(Float)
    architecture_score = Column(Float)
    testing_score = Column(Float)
    scalability_score = Column(Float)
    debt_score = Column(Float)
    raw_output = Column(JSONB)
    error_message = Column(Text)
    generated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    repository = relationship("Repository", back_populates="reviews")
    findings = relationship("Finding", back_populates="review", cascade="all, delete")
    progress = relationship("DeveloperProgress", back_populates="review", cascade="all, delete")

    __table_args__ = (
        Index("idx_reviews_status", "status"),
        Index("idx_reviews_repo", "repository_id"),
    )


class Finding(Base):
    __tablename__ = "findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"))
    agent_name = Column(String(100))
    severity = Column(String(20))  # critical, high, medium, low, info
    category = Column(String(100))
    issue = Column(Text)
    recommendation = Column(Text)
    file_path = Column(Text)
    line_number = Column(Integer)
    cwe_reference = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    review = relationship("Review", back_populates="findings")
    feedback = relationship("FindingFeedback", back_populates="finding", cascade="all, delete")

    __table_args__ = (
        Index("idx_findings_review", "review_id", "severity"),
    )


class FindingFeedback(Base):
    __tablename__ = "finding_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id = Column(UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), unique=True)
    action = Column(String(20), nullable=False)  # dismissed, confirmed, fixed
    reason = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    finding = relationship("Finding", back_populates="feedback")

    __table_args__ = (
        Index("idx_feedback_finding", "finding_id"),
    )


class ScheduledScan(Base):
    __tablename__ = "scheduled_scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_url = Column(Text, nullable=False)
    repo_name = Column(String(255))
    user_email = Column(String(255))
    interval_hours = Column(Integer, nullable=False, default=168)  # default: weekly
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime(timezone=True))
    next_run_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_scheduled_scans_active", "is_active", "next_run_at"),
    )


class DeveloperProgress(Base):
    __tablename__ = "developer_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    repository_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"))
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"))
    review_number = Column(Integer)
    security_score = Column(Float)
    architecture_score = Column(Float)
    testing_score = Column(Float)
    scalability_score = Column(Float)
    debt_score = Column(Float)
    overall_score = Column(Float)
    recorded_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="progress")
    repository = relationship("Repository", back_populates="progress")
    review = relationship("Review", back_populates="progress")

    __table_args__ = (
        Index("idx_progress_user_repo", "user_id", "repository_id"),
    )
