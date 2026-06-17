-- Create langfuse database for the LangFuse service
CREATE DATABASE langfuse;

-- Connect to engineering_review database (default from docker-entrypoint)
\c engineering_review;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    experience_level VARCHAR(50),  -- junior, mid, senior, principal
    career_goal TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    repo_url TEXT NOT NULL,
    repo_name VARCHAR(255),
    language VARCHAR(100),
    framework VARCHAR(100),
    package_manager VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    file_type VARCHAR(50),
    line_count INTEGER,
    complexity_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, running, complete, failed
    overall_score FLOAT,
    security_score FLOAT,
    architecture_score FLOAT,
    testing_score FLOAT,
    scalability_score FLOAT,
    debt_score FLOAT,
    raw_output JSONB,
    error_message TEXT,
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID REFERENCES reviews(id) ON DELETE CASCADE,
    agent_name VARCHAR(100),
    severity VARCHAR(20),  -- critical, high, medium, low, info
    category VARCHAR(100),
    issue TEXT,
    recommendation TEXT,
    file_path TEXT,
    line_number INTEGER,
    cwe_reference VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE developer_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    repository_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
    review_id UUID REFERENCES reviews(id) ON DELETE CASCADE,
    review_number INTEGER,
    security_score FLOAT,
    architecture_score FLOAT,
    testing_score FLOAT,
    scalability_score FLOAT,
    debt_score FLOAT,
    overall_score FLOAT,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

-- finding_feedback — stores developer responses to AI findings
CREATE TABLE finding_feedback (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id UUID UNIQUE REFERENCES findings(id) ON DELETE CASCADE,
    action     VARCHAR(20) NOT NULL,  -- dismissed | confirmed | fixed
    reason     TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- scheduled_scans — recurring repo health scan schedules
CREATE TABLE scheduled_scans (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_url       TEXT NOT NULL,
    repo_name      VARCHAR(255),
    user_email     VARCHAR(255),
    interval_hours INTEGER NOT NULL DEFAULT 168,
    is_active      BOOLEAN DEFAULT TRUE,
    last_run_at    TIMESTAMPTZ,
    next_run_at    TIMESTAMPTZ,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX idx_progress_user_repo    ON developer_progress(user_id, repository_id);
CREATE INDEX idx_findings_review       ON findings(review_id, severity);
CREATE INDEX idx_reviews_status        ON reviews(status);
CREATE INDEX idx_reviews_repo          ON reviews(repository_id);
CREATE INDEX idx_files_repo            ON files(repository_id);
CREATE INDEX idx_feedback_finding      ON finding_feedback(finding_id);
CREATE INDEX idx_scheduled_scans_active ON scheduled_scans(is_active, next_run_at);
