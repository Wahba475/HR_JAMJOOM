"""finalize_run node — shortlists the top candidates, rejects the rest.

Runs once after every batch_rank branch finishes — not fanned out via
Send, since it operates on the whole run at once rather than per-candidate
or per-group. No LLM call here, pure database logic.
"""

from app.db.session import get_pool
from app.graph.state import GraphState


async def finalize_run(state: GraphState) -> dict:
    """Shortlist the top target_count candidates, reject the rest, close out the run."""
    pool = await get_pool()
    async with pool.acquire() as conn, conn.transaction():
        await conn.execute(
            """
            UPDATE candidates SET status = 'shortlisted'
            WHERE id IN (
                SELECT id FROM candidates
                WHERE run_id = $1 AND status = 'scored'
                ORDER BY COALESCE(adjusted_score, score) DESC
                LIMIT $2
            )
            """,
            state["run_id"], state["target_count"],
        )
        await conn.execute(
            "UPDATE candidates SET status = 'rejected' WHERE run_id = $1 AND status = 'scored'",
            state["run_id"],
        )
        await conn.execute(
            "UPDATE runs SET status = 'completed' WHERE id = $1",
            state["run_id"],
        )

    return {}
