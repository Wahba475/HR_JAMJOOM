"""URL-to-function mapping. No parsing, no logic here — see run_controller.py."""

from fastapi import APIRouter, BackgroundTasks, UploadFile

from app.controllers import run_controller
from app.controllers.run_controller import CreateRunRequest

router = APIRouter()


@router.post("/runs")
async def create_run(body: CreateRunRequest):
    return await run_controller.create_run(body)


@router.post("/runs/{run_id}/cvs")
async def upload_cvs(run_id: str, files: list[UploadFile]):
    return await run_controller.upload_cvs(run_id, files)


@router.post("/runs/{run_id}/start")
async def start_run(run_id: str, background_tasks: BackgroundTasks):
    return await run_controller.start_run(run_id, background_tasks)


@router.get("/runs/{run_id}")
async def get_run_status(run_id: str):
    return await run_controller.get_run_status(run_id)


@router.get("/runs/{run_id}/results")
async def get_run_results(run_id: str):
    return await run_controller.get_run_results(run_id)


@router.post("/runs/{run_id}/export")
async def export_sheet(run_id: str):
    return await run_controller.export_sheet(run_id)


@router.get("/runs/{run_id}/export")
async def export_sheet_get(run_id: str):
    return await run_controller.export_sheet(run_id)


@router.post("/runs/{run_id}/sheet")
async def push_sheet(run_id: str):
    return await run_controller.push_sheet(run_id)


@router.get("/runs/{run_id}/cvs/download")
async def download_cvs(run_id: str):
    return await run_controller.download_cvs(run_id)
