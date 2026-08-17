"""Parses/validates requests, calls one service function, shapes the response.

No direct DB or graph calls here — that's run_service.py's job.
"""

from fastapi import BackgroundTasks, Response, UploadFile
from pydantic import BaseModel

from app.services import run_service, sheets_export


class CreateRunRequest(BaseModel):
    title: str
    job_description: str
    criteria: str
    target_count: int


async def create_run(body: CreateRunRequest) -> dict:
    run_id = await run_service.create_run(
        body.title, body.job_description, body.criteria, body.target_count
    )
    return {"run_id": run_id}


async def upload_cvs(run_id: str, files: list[UploadFile]) -> dict:
    uploads = [(f.filename, await f.read()) for f in files]
    count = await run_service.save_cvs(run_id, uploads)
    return {"uploaded": count}


async def start_run(run_id: str, background_tasks: BackgroundTasks) -> dict:
    await run_service.start_run(run_id, background_tasks)
    return {"status": "started"}


async def get_run_status(run_id: str) -> dict:
    return await run_service.get_run_status(run_id)


async def get_run_results(run_id: str) -> list[dict]:
    return await run_service.get_run_results(run_id)


async def export_sheet(run_id: str) -> Response:
    csv_bytes = await sheets_export.export_csv(run_id)
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="shortlist_{run_id[:8]}.csv"'},
    )


async def push_sheet(run_id: str) -> dict:
    url = await sheets_export.push_to_google_sheet(run_id)
    return {"sheet_url": url}


async def download_cvs(run_id: str) -> Response:
    zip_bytes = await sheets_export.export_cvs_zip(run_id)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="cvs_{run_id[:8]}.zip"'},
    )
