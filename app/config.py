"""Env-driven config.

Secrets are read from the environment only — never defaulted to a real
value — so a misconfigured deploy fails at boot instead of silently
running against the wrong database or with no auth.
"""

import os

from dotenv import load_dotenv

load_dotenv(".ENV")
load_dotenv()  # standard .env too, if present

# --- Database ---------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

# --- Object storage ---------------------------------------------------
# Endpoint/credentials/region use the standard AWS_* names, so boto3 picks
# them up itself; only the bucket needs reading here.
BUCKET_NAME = os.getenv("BUCKET_NAME", "cv1")

# --- LLM --------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("GPT_API_KEY")
SCORE_MODEL = os.getenv("SCORE_MODEL", "gpt-4.1-mini")
RANK_MODEL = os.getenv("RANK_MODEL", "gpt-5.4-mini")
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "4"))
# Sent with every LLM call so repeat runs over the same CVs stay comparable.
# OpenAI treats seed as best-effort, so this narrows variance rather than
# eliminating it.
RUN_SEED = int(os.getenv("RUN_SEED", "42"))

# Local Ollama fallback, kept so the pipeline can run without a paid key.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")

# --- Google Sheets export ---------------------------------------------
# Path to the service-account JSON. Kept outside the project tree so the
# private key can't be swept into a commit.
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
# The spreadsheet to write into. It must be created by a human and shared
# with the service account as Editor — service accounts have no Drive
# storage quota, so they cannot create or own a spreadsheet themselves.
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

# --- Throughput -------------------------------------------------------
GRAPH_CONCURRENCY = int(os.getenv("GRAPH_CONCURRENCY", "20"))
UPLOAD_CONCURRENCY = int(os.getenv("UPLOAD_CONCURRENCY", "16"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
MAX_FILES_PER_REQUEST = int(os.getenv("MAX_FILES_PER_REQUEST", "500"))

# --- Security ---------------------------------------------------------
# Comma-separated. Empty disables auth, which is only acceptable locally;
# require_production_config() rejects that combination.
API_KEYS = {k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()}
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


def require_production_config() -> None:
    """Refuse to boot a production deploy that is missing hard requirements.

    Called at app startup. Better to crash on deploy than to serve an
    unauthenticated endpoint that spends money on someone else's uploads.
    """
    missing = []
    if not DATABASE_URL:
        missing.append("DATABASE_URL")
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")

    if ENVIRONMENT == "production":
        if not API_KEYS:
            missing.append("API_KEYS (auth cannot be disabled in production)")
        if any(o == "*" for o in CORS_ORIGINS):
            missing.append("CORS_ORIGINS (wildcard not allowed in production)")

    if missing:
        raise RuntimeError("Missing required configuration: " + ", ".join(missing))
