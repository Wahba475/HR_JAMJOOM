"""Append-only LLM token usage log, for measuring real run cost.

Written as JSONL so a run can be costed after the fact without holding
anything in memory across the graph's parallel branches.
"""

import json
import os
import threading

USAGE_LOG_PATH = os.getenv("USAGE_LOG_PATH", "llm_usage.jsonl")

_lock = threading.Lock()


def record(node: str, model: str, usage: dict | None) -> None:
    """Log one call's token counts. Never raises — cost telemetry must not
    be able to fail a run."""
    if not usage:
        return
    try:
        with _lock, open(USAGE_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "node": node,
                        "model": model,
                        "input_tokens": usage.get("input_tokens", 0),
                        "output_tokens": usage.get("output_tokens", 0),
                    }
                )
                + "\n"
            )
    except Exception:
        pass
