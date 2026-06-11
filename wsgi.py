#!/usr/bin/env python3
"""
ASGI entry point for production deployment (FastAPI / uvicorn / gunicorn + UvicornWorker).

Usage:
    uvicorn app.main:app --host 0.0.0.0 --port 8000
    gunicorn -k uvicorn.workers.UvicornWorker app.main:app

NOTE: api.py (Flask) is kept as a reference until FastAPI is fully validated.
"""
from app.main import app  # noqa: F401  — imported for gunicorn/uvicorn

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)