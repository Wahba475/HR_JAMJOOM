"""Builds and compiles the CV filtering graph.

extract_text -> score_cv, fanned out per CV via Send. score_cv -> batch_rank,
fanned out per group of survivors. Every CV takes the identical
extract_text -> score_cv path — nothing is dropped mid-graph. Only batch_rank
operates on groups instead of individuals.

Barrier nodes (`texts_ready`, `scores_ready`) sit between each fan-out stage.
They exist because a conditional edge is evaluated once per *source task*, not
once after a Send fan-out finishes: hanging fan_out_score directly off
extract_text would re-run the router for all 200 branches, and hanging
fan_out_batches off score_cv fired it as soon as the first CV was scored, while
the other 199 still had score=None. A plain edge into a single node instead
converges every branch first, so the router downstream of it runs exactly once
against complete state.
"""

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.graph.nodes.batch_rank import batch_rank
from app.graph.nodes.extract_text import extract_text
from app.graph.nodes.finalize_run import finalize_run
from app.graph.nodes.score_cv import score_cv
from app.graph.state import GraphState


def fan_out_extract(state: GraphState):
    """Send every candidate to extract_text, one call each, concurrently."""
    return [Send("extract_text", c) for c in state["candidates"]]


def barrier(state: GraphState) -> dict:
    """Join point for a Send fan-out. Writes nothing; its only job is to give
    the next router a single source task to hang off."""
    return {}


def fan_out_score(state: GraphState):
    """Send every extracted candidate to score_cv, one call each."""
    return [
        Send(
            "score_cv",
            {
                "candidate": c,
                "run_id": state["run_id"],
                "job_description": state["job_description"],
                "criteria": state["criteria"],
            },
        )
        for c in state["candidates"]
    ]


def fan_out_batches(state: GraphState):
    """Take everyone score_cv finished, group them, send one call per group."""
    # Unscored candidates are skipped rather than sorted: a failed score_cv
    # leaves score=None, and None has no ordering against a float.
    scored = [c for c in state["candidates"] if c.get("score") is not None]
    survivors = sorted(scored, key=lambda c: c["score"], reverse=True)
    survivors = survivors[: state["target_count"] * 3]

    group_size = 12
    groups = [survivors[i : i + group_size] for i in range(0, len(survivors), group_size)]

    return [
        Send(
            "batch_rank",
            {
                "group": g,
                "job_description": state["job_description"],
                "criteria": state["criteria"],
            },
        )
        for g in groups
    ]


builder = StateGraph(GraphState)
builder.add_node("extract_text", extract_text)
builder.add_node("texts_ready", barrier)
builder.add_node("score_cv", score_cv)
builder.add_node("scores_ready", barrier)
builder.add_node("batch_rank", batch_rank)
builder.add_node("finalize_run", finalize_run)

builder.add_conditional_edges(START, fan_out_extract, ["extract_text"])
builder.add_edge("extract_text", "texts_ready")
builder.add_conditional_edges("texts_ready", fan_out_score, ["score_cv"])
builder.add_edge("score_cv", "scores_ready")
builder.add_conditional_edges("scores_ready", fan_out_batches, ["batch_rank"])
builder.add_edge("batch_rank", "finalize_run")
builder.add_edge("finalize_run", END)

compiled = builder.compile()
