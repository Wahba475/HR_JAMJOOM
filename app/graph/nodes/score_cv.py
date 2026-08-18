"""score_cv node — one LLM call per CV, scored against the job posting.

Same Send fan-out pattern as extract_text, runs concurrently. As a side
effect, writes its result straight to that candidate's DB row and bumps
runs.processed_cvs — this is what makes the progress bar move in real
time instead of jumping from 0 to 100% at the end.
"""


from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import OPENAI_API_KEY, RUN_SEED, SCORE_MODEL
from app.db.queries import save_candidate_score
from app.graph.prompts import SCORE_PROMPT
from app.graph.state import CandidateState
from app.services.usage_log import record


class ScoreResult(BaseModel):
    candidate_name: str = Field(default="", description="Full name as it appears on the CV")
    candidate_email: str = Field(default="", description="Email address as it appears on the CV")
    score: float = Field(description="Match score, 0-100")
    rationale: str = Field(description="1-2 sentences citing specific matches or gaps")


# include_raw keeps the AIMessage alongside the parsed model; without it the
# structured-output wrapper discards the response metadata that carries token
# counts, and the run can't be costed.
llm = ChatOpenAI(
    model=SCORE_MODEL, api_key=OPENAI_API_KEY, temperature=0, seed=RUN_SEED
).with_structured_output(ScoreResult, include_raw=True)


async def score_cv(payload: dict) -> dict:
    """Score one candidate, persist the result, return the state patch.

    payload = {"candidate": CandidateState, "run_id": str,
               "job_description": str, "criteria": str}
    """
    candidate: CandidateState = payload["candidate"]

    user_message = (
        f"Job description:\n{payload['job_description']}\n\n"
        f"Hiring criteria:\n{payload['criteria']}\n\n"
        f"Candidate CV text:\n{candidate['extracted_text']}"
    )
    response = await llm.ainvoke(
        [
            {"role": "system", "content": SCORE_PROMPT},
            {"role": "user", "content": user_message},
        ]
    )
    result: ScoreResult = response["parsed"]
    record("score_cv", SCORE_MODEL, getattr(response["raw"], "usage_metadata", None))

    updated: CandidateState = {
        **candidate,
        "candidate_name": result.candidate_name or None,
        "candidate_email": result.candidate_email or None,
        "score": result.score,
        "rationale": result.rationale,
    }

    await save_candidate_score(
        candidate_id=candidate["candidate_id"],
        run_id=payload["run_id"],
        candidate_name=updated["candidate_name"],
        candidate_email=updated["candidate_email"],
        score=updated["score"],
        rationale=updated["rationale"],
    )

    return {"candidates": [updated]}
