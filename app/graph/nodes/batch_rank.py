"""batch_rank node — compares a group of CVs against each other directly.

Fixes score_cv's real limitation: isolated scores have no anchor against
other candidates. Fanned out per group via Send (~18 candidates each),
runs concurrently. Same side-effect pattern as score_cv: writes straight
to each candidate's DB row, no DB read needed to find survivors since
GraphState.candidates already holds every score in memory.
"""

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import OPENAI_API_KEY, RANK_MODEL
from app.db.queries import save_batch_rank
from app.graph.prompts import BATCH_RANK_PROMPT
from app.graph.state import CandidateState
from app.services.usage_log import record


class Ranking(BaseModel):
    candidate_id: str
    adjusted_score: float = Field(description="0-100, calibrated against the rest of this group")
    comparison_note: str = Field(description="1 sentence on how this candidate compares to the others")


class BatchRankResult(BaseModel):
    rankings: list[Ranking]


# Stronger model than score_cv: only a handful of calls per run, and this is
# the step where comparative judgment actually decides the shortlist.
llm = ChatOpenAI(model=RANK_MODEL, api_key=OPENAI_API_KEY).with_structured_output(
    BatchRankResult, include_raw=True
)


def _format_group(group: list[CandidateState]) -> str:
    return "\n\n".join(
        f"Candidate ID: {c['candidate_id']}\n"
        f"First-pass score: {c['score']}\n"
        f"First-pass rationale: {c['rationale']}\n"
        f"CV text:\n{c['extracted_text']}"
        for c in group
    )


async def batch_rank(payload: dict) -> dict:
    """Rank one group of candidates, persist each result, return the state patch.

    payload = {"group": list[CandidateState] (~18), "job_description": str,
               "criteria": str}
    """
    group: list[CandidateState] = payload["group"]

    user_message = (
        f"Job description:\n{payload['job_description']}\n\n"
        f"Hiring criteria:\n{payload['criteria']}\n\n"
        f"Candidates:\n{_format_group(group)}"
    )
    response = await llm.ainvoke(
        [
            {"role": "system", "content": BATCH_RANK_PROMPT},
            {"role": "user", "content": user_message},
        ]
    )
    result: BatchRankResult = response["parsed"]
    record("batch_rank", RANK_MODEL, getattr(response["raw"], "usage_metadata", None))
    rankings_by_id = {r.candidate_id: r for r in result.rankings}

    updated = []
    for candidate in group:
        ranking = rankings_by_id.get(candidate["candidate_id"])
        if ranking is None:
            # Local model skipped this one — fall back to its first-pass
            # score instead of crashing the whole ~18-candidate group.
            adjusted_score = candidate["score"]
            comparison_note = "Not compared — missing from batch ranking output."
        else:
            adjusted_score = ranking.adjusted_score
            comparison_note = ranking.comparison_note

        await save_batch_rank(candidate["candidate_id"], adjusted_score, comparison_note)
        updated.append({**candidate, "adjusted_score": adjusted_score, "comparison_note": comparison_note})

    return {"candidates": updated}
