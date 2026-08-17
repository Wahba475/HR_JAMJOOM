-- Run this once in the Neon SQL editor to set up the schema.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE run_status AS ENUM ('pending', 'processing', 'completed', 'failed');
-- 'failed' distinguishes a CV whose scoring gave up after retries from one
-- that was never reached, so a partial run is auditable rather than silent.
CREATE TYPE candidate_status AS ENUM ('pending', 'scored', 'rejected', 'shortlisted', 'failed');

CREATE TABLE runs (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title           text NOT NULL,
    job_description text NOT NULL,
    criteria        text NOT NULL,
    target_count    int NOT NULL,
    status          run_status NOT NULL DEFAULT 'pending',
    total_cvs       int NOT NULL DEFAULT 0,
    processed_cvs   int NOT NULL DEFAULT 0,
    error           text,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE candidates (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id            uuid NOT NULL REFERENCES runs(id),
    file_name         text NOT NULL,
    storage_path      text NOT NULL,
    candidate_name    text,
    candidate_email   text,
    status            candidate_status NOT NULL DEFAULT 'pending',
    score             float,
    rationale         text,
    adjusted_score    float,
    comparison_note   text,
    error             text,
    attempts          int NOT NULL DEFAULT 0,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_candidates_run_id ON candidates(run_id);
CREATE INDEX idx_candidates_run_status ON candidates(run_id, status);
CREATE INDEX idx_runs_created ON runs(created_at DESC);
