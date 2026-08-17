"""All real logic for runs: DB queries, storage calls, kicking off the graph."""

import asyncio
from uuid import uuid4

from fastapi import BackgroundTasks

from app.db.session import get_pool
from app.graph.graph import compiled
from app.graph.state import GraphState, new_candidate
from app.services import storage


async def create_run(title: str, job_description: str, criteria: str, target_count: int) -> str:
    """Insert a new run row, status defaults to pending."""
    pool = await get_pool()
    run_id = await pool.fetchval(
        """
        INSERT INTO runs (title, job_description, criteria, target_count, status)
        VALUES ($1, $2, $3, $4, 'pending')
        RETURNING id
        """,
        title, job_description, criteria, target_count,
    )
    return str(run_id)


UPLOAD_CONCURRENCY = 16


async def save_cvs(run_id: str, uploads: list[tuple[str, bytes]]) -> int:
    """Upload each CV to storage, then insert its candidate row. Storage first, DB second.

    Uploads run concurrently and the rows go in as one executemany. Done
    serially — one round trip to object storage plus one INSERT per file —
    200 CVs took about 3.5 minutes of pure network latency before the
    pipeline could even start, which is longer than the scoring itself.
    boto3 is blocking, so each PUT goes to a worker thread.
    """
    pool = await get_pool()
    semaphore = asyncio.Semaphore(UPLOAD_CONCURRENCY)

    async def upload_one(file_name: str, file_bytes: bytes) -> tuple[str, str, str, str]:
        candidate_id = str(uuid4())
        async with semaphore:
            storage_path = await asyncio.to_thread(
                storage.save_cv, run_id, candidate_id, file_bytes
            )
        return candidate_id, run_id, file_name, storage_path

    rows = await asyncio.gather(*(upload_one(name, data) for name, data in uploads))

    async with pool.acquire() as conn, conn.transaction():
        await conn.executemany(
            """
            INSERT INTO candidates (id, run_id, file_name, storage_path, status)
            VALUES ($1, $2, $3, $4, 'pending')
            """,
            rows,
        )
        await conn.execute(
            "UPDATE runs SET total_cvs = total_cvs + $2 WHERE id = $1", run_id, len(rows)
        )
    return len(rows)


async def start_run(run_id: str, background_tasks: BackgroundTasks) -> None:
    """Seed GraphState from pending candidates, flip to processing, run the graph in the background."""
    pool = await get_pool()
    run = await pool.fetchrow(
        "SELECT job_description, criteria, target_count FROM runs WHERE id = $1", run_id
    )
    pending = await pool.fetch(
        "SELECT id, file_name, storage_path FROM candidates WHERE run_id = $1 AND status = 'pending'",
        run_id,
    )

    initial_state: GraphState = {
        "run_id": run_id,
        "job_description": run["job_description"],
        "criteria": run["criteria"],
        "target_count": run["target_count"],
        "candidates": [
            new_candidate(str(row["id"]), row["file_name"], row["storage_path"]) for row in pending
        ],
    }

    await pool.execute("UPDATE runs SET status = 'processing' WHERE id = $1", run_id)
    # Not awaited here — finalize_run flips runs.status to completed once the
    # graph finishes, so the endpoint returns immediately and the frontend
    # polls get_run_status() for progress in the meantime.
    # Send fans out one branch per CV but does not throttle them; without
    # max_concurrency LangGraph runs every branch at once (the semaphore is
    # only created when this key is present), which would burst 200 requests.
    background_tasks.add_task(compiled.ainvoke, initial_state, {"max_concurrency": 20})


async def get_run_status(run_id: str) -> dict:
    """Read-only status, polled by the frontend for the progress bar."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT status, total_cvs, processed_cvs FROM runs WHERE id = $1", run_id
    )
    return {"status": row["status"], "total_cvs": row["total_cvs"], "processed_cvs": row["processed_cvs"]}


async def get_run_results(run_id: str) -> list[dict]:
    """Shortlisted candidates, best first, each with a presigned URL for its CV."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT candidate_name, candidate_email, storage_path,
               COALESCE(adjusted_score, score) AS score,
               COALESCE(comparison_note, rationale) AS rationale
        FROM candidates
        WHERE run_id = $1 AND status = 'shortlisted'
        ORDER BY COALESCE(adjusted_score, score) DESC
        """,
        run_id,
    )
    return [
        {
            "candidate_name": row["candidate_name"],
            "candidate_email": row["candidate_email"],
            "score": row["score"],
            "rationale": row["rationale"],
            "cv_url": storage.get_view_url(row["storage_path"]),
        }
        for row in rows
    ]
