"""Shared state for the CV filtering graph.

One state, not two — GraphState is the outer container for a whole run;
CandidateState is just the shape of one entry inside its candidates list.
"""

from typing import Annotated, TypedDict


class CandidateState(TypedDict):
    """One CV as it moves through the graph."""

    candidate_id: str
    file_name: str
    storage_path: str
    extracted_text: str
    candidate_name: str | None
    candidate_email: str | None
    score: float | None
    rationale: str | None
    adjusted_score: float | None  # set by batch_rank
    comparison_note: str | None  # set by batch_rank


def merge_candidates(
    left: list[CandidateState], right: list[CandidateState]
) -> list[CandidateState]:
    """Upsert-by-id reducer for the candidates list.

    extract_text and score_cv both fan out over the same candidates and
    write back into this same field. A plain list-concat (operator.add)
    would duplicate every candidate each time a later stage re-fans over
    it — N from extract_text + N from score_cv = 2N. Merging by
    candidate_id instead keeps one row per candidate, patched in place as
    each stage fills in more fields.
    """
    merged = {c["candidate_id"]: dict(c) for c in left}
    for c in right:
        if c["candidate_id"] in merged:
            merged[c["candidate_id"]].update(c)
        else:
            merged[c["candidate_id"]] = dict(c)
    return list(merged.values())


class GraphState(TypedDict):
    """State for one run: the job posting plus every CV submitted to it."""

    run_id: str
    job_description: str
    criteria: str
    target_count: int
    candidates: Annotated[list[CandidateState], merge_candidates]


def new_candidate(candidate_id: str, file_name: str, storage_path: str) -> CandidateState:
    """Build a blank candidate entry so every entry starts with the same shape."""
    return {
        "candidate_id": candidate_id,
        "file_name": file_name,
        "storage_path": storage_path,
        "extracted_text": "",
        "candidate_name": None,
        "candidate_email": None,
        "score": None,
        "rationale": None,
        "adjusted_score": None,
        "comparison_note": None,
    }
