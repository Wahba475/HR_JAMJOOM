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
from datetime import datetime
import io
import zipfile

from app.config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SHEET_ID
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


SHEET_HEADERS = ["Rank", "Candidate", "Email", "Score", "Why they matched", "CV"]

# Presigned links live in a document people keep, so a one-hour expiry
# would leave a sheet full of dead links by the afternoon. Seven days is
# the maximum SigV4 allows.
LINK_TTL_SECONDS = 7 * 24 * 3600


def _sheet_rows(title: str, rows: list[dict]) -> list[list]:
    body = []
    for rank, r in enumerate(rows, start=1):
        url = storage.get_view_url(r["storage_path"], expires_in=LINK_TTL_SECONDS)
        # HYPERLINK keeps the cell clickable while showing a readable label,
        # instead of dumping a 700-character signed URL into the cell.
        link = f'=HYPERLINK("{url}", "Open CV")'
        body.append(
            [
                rank,
                r["candidate_name"] or "—",
                r["candidate_email"] or "—",
                round(r["score"], 1) if r["score"] is not None else "",
                r["rationale"] or "",
                link,
            ]
        )
    return [SHEET_HEADERS, *body]


def _push_sync(title: str, values: list[list]) -> str:
    """Add a tab to the configured spreadsheet, write the shortlist, return its URL.

    Writes into a spreadsheet the *user* owns rather than creating one.
    A service account has no Drive storage quota, so anything it creates
    itself fails with a 403 — the account can edit files shared with it,
    but cannot own them.

    Runs entirely in a worker thread: the Google client libraries are
    synchronous and would otherwise block the event loop for the whole
    round trip.
    """
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
    sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)

    spreadsheet_id = GOOGLE_SHEET_ID

    # One tab per run, so past shortlists stay intact.
    tab_title = f"{title[:60]} {datetime.now():%d %b %H:%M}"
    added = (
        sheets.spreadsheets()
        .batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": tab_title}}}]},
        )
        .execute()
    )
    sheet_id = added["replies"][0]["addSheet"]["properties"]["sheetId"]

    # USER_ENTERED, not RAW: RAW would store the HYPERLINK formula as literal
    # text and the CV column would show formula source instead of links.
    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{tab_title}'!A1",
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()

    rows = len(values)
    header_bg = {"red": 0.15, "green": 0.19, "blue": 0.28}
    band_bg = {"red": 0.96, "green": 0.97, "blue": 0.99}

    sheets.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                # Header row: dark fill, white bold text, centred.
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": header_bg,
                                "textFormat": {
                                    "bold": True,
                                    "fontSize": 11,
                                    "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                                },
                                "verticalAlignment": "MIDDLE",
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment)",
                    }
                },
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "gridProperties": {"frozenRowCount": 1, "rowCount": max(rows, 2)},
                        },
                        "fields": "gridProperties(frozenRowCount,rowCount)",
                    }
                },
                # Wrap the rationale so long text stays inside its cell
                # rather than spilling across the CV column.
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": 4, "endColumnIndex": 5},
                        "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP", "verticalAlignment": "TOP"}},
                        "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)",
                    }
                },
                # Centre rank, score and the CV link.
                *[
                    {
                        "repeatCell": {
                            "range": {"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": c, "endColumnIndex": c + 1},
                            "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
                            "fields": "userEnteredFormat.horizontalAlignment",
                        }
                    }
                    for c in (0, 3, 5)
                ],
                # Zebra striping, so a long shortlist stays readable.
                {
                    "addBanding": {
                        "bandedRange": {
                            "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": rows},
                            "rowProperties": {
                                "firstBandColor": {"red": 1, "green": 1, "blue": 1},
                                "secondBandColor": band_bg,
                            },
                        }
                    }
                },
                # Green-to-red scale on Score, so the spread is visible at a glance.
                {
                    "addConditionalFormatRule": {
                        "index": 0,
                        "rule": {
                            "ranges": [{"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": 3, "endColumnIndex": 4}],
                            "gradientRule": {
                                "minpoint": {"color": {"red": 0.96, "green": 0.80, "blue": 0.80}, "type": "MIN"},
                                "maxpoint": {"color": {"red": 0.72, "green": 0.88, "blue": 0.75}, "type": "MAX"},
                            },
                        },
                    }
                },
                # Fixed widths beat autoResize here: the rationale column is
                # long free text and autoResize would make it enormous.
                *[
                    {
                        "updateDimensionProperties": {
                            "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
                            "properties": {"pixelSize": w},
                            "fields": "pixelSize",
                        }
                    }
                    for i, w in enumerate([60, 200, 260, 70, 520, 90])
                ],
            ]
        },
    ).execute()


    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}"


async def push_to_google_sheet(run_id: str) -> str:
    """Write the shortlist into a new Google Sheet and return its URL."""
    if not GOOGLE_CREDENTIALS_PATH:
        raise RuntimeError("GOOGLE_CREDENTIALS_PATH is not configured")
    if not GOOGLE_SHEET_ID:
        raise RuntimeError(
            "GOOGLE_SHEET_ID is not configured. Create a Google Sheet, share it "
            "as Editor with the service account, and set its id."
        )

    pool = await get_pool()
    title = await pool.fetchval("SELECT title FROM runs WHERE id = $1", run_id) or "CV Screener"
    rows = await _fetch_shortlist(run_id)
    values = _sheet_rows(title, rows)
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
