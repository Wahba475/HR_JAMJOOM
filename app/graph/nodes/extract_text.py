"""extract_text node — pulls the text layer straight out of one CV's PDF.

No LLM here. PyMuPDF reads embedded text, so it works regardless of the
CV's visual layout. Doesn't handle scanned image-only PDFs (would need
OCR) — assume real digital PDFs for v1.

Fanned out per CV via Send, runs concurrently, writes nothing to the DB —
only fills extracted_text into the in-memory graph state.
"""

import pymupdf as fitz

from app.graph.state import CandidateState
from app.services.storage import read_cv


def extract_text(candidate: CandidateState) -> dict:
    """Read one CV's PDF (from object storage) and fill in its extracted_text.

    Called once per candidate via Send, so `candidate` here is a single
    CandidateState, not the full run state.
    """
    try:
        pdf_bytes = read_cv(candidate["storage_path"])
        with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
            text = "\n".join(page.get_text() for page in pdf)
    except Exception:
        # Bad/corrupt PDF shouldn't crash the whole run — leave it empty,
        # score_cv will just have nothing to work with for this one CV.
        text = ""

    return {"candidates": [{**candidate, "extracted_text": text}]}
