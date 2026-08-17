"""Export a run's shortlist.

Two formats, both driven off the same query:

- CSV bytes, which Google Sheets imports directly (File > Import, or drag
  into Drive). This needs no credentials, so it works for the demo today.
- A real Google Sheet, if a service-account JSON is configured. Left as an
  explicit branch rather than a stub so the missing-credential case fails
  loudly instead of silently producing nothing.

- A ZIP of the shortlisted candidates' PDFs, for handing the batch to a
  hiring manager in one file.
"""

import asyncio
import csv
import io
import zipfile

from app.config import GOOGLE_CREDENTIALS_PATH, SHEET_SHARE_WITH
from app.db.session import get_pool
from app.services import storage

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

COLUMNS = ["rank", "candidate_name", "candidate_email", "score", "rationale", "file_name"]


async def _fetch_shortlist(run_id: str) -> list[dict]:
    """Shortlisted candidates, best first — same ordering the results page uses."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT candidate_name, candidate_email, file_name, storage_path,
               COALESCE(adjusted_score, score) AS score,
               COALESCE(comparison_note, rationale) AS rationale
        FROM candidates
        WHERE run_id = $1 AND status = 'shortlisted'
        ORDER BY COALESCE(adjusted_score, score) DESC
        """,
        run_id,
    )
    return [dict(r) for r in rows]


async def export_csv(run_id: str) -> bytes:
    """Shortlist as CSV bytes, ready to open in Google Sheets or Excel."""
    rows = await _fetch_shortlist(run_id)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(COLUMNS)
    for rank, row in enumerate(rows, start=1):
        writer.writerow(
            [
                rank,
                row["candidate_name"] or "",
                row["candidate_email"] or "",
                round(row["score"], 1) if row["score"] is not None else "",
                row["rationale"] or "",
                row["file_name"],
            ]
        )
    # utf-8-sig: Excel misreads plain UTF-8 accents without the BOM.
    return buffer.getvalue().encode("utf-8-sig")


def _sheet_rows(run_id: str, title: str, rows: list[dict]) -> list[list]:
    header = [f"Shortlist — {title}", "", "", "", "", ""]
    body = [
        [
            rank,
            r["candidate_name"] or "",
            r["candidate_email"] or "",
            round(r["score"], 1) if r["score"] is not None else "",
            r["rationale"] or "",
            r["file_name"],
        ]
        for rank, r in enumerate(rows, start=1)
    ]
    return [header, COLUMNS, *body]


def _push_sync(title: str, values: list[list]) -> str:
    """Create a sheet, write the shortlist, share it, return its URL.

    Runs entirely in a worker thread: the Google client libraries are
    synchronous and would otherwise block the event loop for the whole
    round trip.
    """
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
    sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)

    created = sheets.spreadsheets().create(body={"properties": {"title": title}}).execute()
    spreadsheet_id = created["spreadsheetId"]

    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="A1",
        valueInputOption="RAW",
        body={"values": values},
    ).execute()

    # Bold the two header rows and freeze them, so the sheet is readable
    # as-is rather than needing manual formatting before it's shared on.
    sheets.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "repeatCell": {
                        "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 2},
                        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                        "fields": "userEnteredFormat.textFormat.bold",
                    }
                },
                {
                    "updateSheetProperties": {
                        "properties": {"sheetId": 0, "gridProperties": {"frozenRowCount": 2}},
                        "fields": "gridProperties.frozenRowCount",
                    }
                },
                {"autoResizeDimensions": {"dimensions": {"sheetId": 0, "dimension": "COLUMNS"}}},
            ]
        },
    ).execute()

    # Without this the sheet belongs to the service account, which has no
    # UI — nobody could actually open it.
    for email in SHEET_SHARE_WITH:
        drive.permissions().create(
            fileId=spreadsheet_id,
            body={"type": "user", "role": "writer", "emailAddress": email},
            sendNotificationEmail=False,
        ).execute()

    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"


async def push_to_google_sheet(run_id: str) -> str:
    """Write the shortlist into a new Google Sheet and return its URL."""
    if not GOOGLE_CREDENTIALS_PATH:
        raise RuntimeError("GOOGLE_CREDENTIALS_PATH is not configured")

    pool = await get_pool()
    title = await pool.fetchval("SELECT title FROM runs WHERE id = $1", run_id) or "CV Screener"
    rows = await _fetch_shortlist(run_id)
    values = _sheet_rows(run_id, title, rows)
    return await asyncio.to_thread(_push_sync, f"Shortlist — {title}", values)


async def export_cvs_zip(run_id: str) -> bytes:
    """Every shortlisted candidate's PDF in one ZIP.

    Names each entry by rank and candidate so the files are meaningful
    outside this system, rather than the uuid the storage key uses.
    """
    rows = await _fetch_shortlist(run_id)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for rank, row in enumerate(rows, start=1):
            safe_name = (row["candidate_name"] or "unnamed").replace("/", "-").replace("\\", "-")
            try:
                archive.writestr(f"{rank:02d}_{safe_name}.pdf", storage.read_cv(row["storage_path"]))
            except Exception:
                # One unreadable object shouldn't cost the user the whole zip.
                archive.writestr(f"{rank:02d}_{safe_name}_MISSING.txt", row["storage_path"])
    return buffer.getvalue()
