"""FastAPI entrypoint.

Run from this directory:

    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router
from secureai_shared.queue import JobQueue, build_queue


def create_app(queue: JobQueue | None = None) -> FastAPI:
    app = FastAPI(title="SecureAI API", version="0.1.0")
    app.state.queue = queue if queue is not None else build_queue()
    origins = [
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(router)
    return app


app = create_app()
