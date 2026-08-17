"""Creates the FastAPI app, includes the router. Nothing else."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.run_router import router

app = FastAPI(title="CV Filter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
