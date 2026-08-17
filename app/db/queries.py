"""Raw SQL against runs/candidates. No ORM."""

from app.db.session import get_pool


async def save_candidate_score(
    candidate_id: str,
    run_id: str,
    candidate_name: str | None,
    candidate_email: str | None,
    score: float,
    rationale: str,
) -> None:
    """Write one CV's score and bump the run's progress counter, atomically.

    This is the side effect that makes the progress bar move in real
    time — one commit per CV as soon as its LLM call returns.
    """
    pool = await get_pool()
    async with pool.acquire() as conn, conn.transaction():
        await conn.execute(
            """
            UPDATE candidates
            SET candidate_name = $2, candidate_email = $3,
                score = $4, rationale = $5, status = 'scored'
            WHERE id = $1
            """,
            candidate_id, candidate_name, candidate_email, score, rationale,
        )
        await conn.execute(
            "UPDATE runs SET processed_cvs = processed_cvs + 1 WHERE id = $1",
            run_id,
        )


async def save_batch_rank(candidate_id: str, adjusted_score: float, comparison_note: str) -> None:
    """Write one candidate's group-relative rank, once batch_rank scores it."""
    pool = await get_pool()
    await pool.execute(
        "UPDATE candidates SET adjusted_score = $2, comparison_note = $3 WHERE id = $1",
        candidate_id, adjusted_score, comparison_note,
    )
