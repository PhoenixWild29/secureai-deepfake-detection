#!/usr/bin/env python3
"""
System Router  —  /api/v1/system

Health check, ML ensemble status, security audit, and dashboard stats.
Ports the following Flask routes from api.py:
    GET  /api/health            →  GET  /api/v1/system/health
    GET  /api/ensemble-status   →  GET  /api/v1/system/ensemble-status
    POST /api/security/audit    →  POST /api/v1/system/security-audit
    GET  /api/dashboard/stats   →  GET  /api/v1/system/dashboard-stats
"""

import os
import json
import logging
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/system", tags=["System"])


# ---------------------------------------------------------------------------
# GET /api/v1/system/health
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    summary="Health check",
    description="Lightweight liveness probe for load balancers and monitoring.",
)
async def health_check():
    """Return API health status."""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0',
        'framework': 'FastAPI',
    }


# ---------------------------------------------------------------------------
# GET /api/v1/system/ensemble-status
# ---------------------------------------------------------------------------

@router.get(
    "/ensemble-status",
    summary="ML ensemble loading status",
    description="Return current status of all ML model components. Frontend polls this on startup.",
)
async def ensemble_status():
    """Return the loading progress and readiness of the detection ensemble."""
    try:
        from ai_model.ensemble_detector import get_ensemble_status
        return JSONResponse(content=get_ensemble_status())
    except Exception as exc:
        logger.warning("ensemble-status error: %s", exc)
        return JSONResponse(content={
            'status': 'unknown',
            'ready': False,
            'progress_pct': 0,
            'models': {},
            'error': str(exc),
        })


# ---------------------------------------------------------------------------
# POST /api/v1/system/security-audit
# ---------------------------------------------------------------------------

@router.post(
    "/security-audit",
    summary="Security audit",
    description="Run a security audit of the current server environment.",
)
async def security_audit(body: dict = None):
    """Run Morpheus security analysis of the server environment."""
    try:
        from ai_model.morpheus_security import get_security_status
        status = get_security_status()
        return JSONResponse(content=status)
    except Exception as exc:
        logger.exception("Security audit error: %s", exc)
        return JSONResponse(status_code=500, content={'error': str(exc)})


# ---------------------------------------------------------------------------
# GET /api/v1/system/dashboard-stats
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard-stats",
    summary="Dashboard statistics",
    description="Return aggregated detection statistics for the dashboard.",
)
async def dashboard_stats():
    """Count and summarise all analysis results saved to the results folder."""
    results_folder = os.getenv('RESULTS_FOLDER', 'results')
    total = fake_count = real_count = 0

    if os.path.isdir(results_folder):
        for fname in os.listdir(results_folder):
            if not fname.endswith('.json'):
                continue
            try:
                with open(os.path.join(results_folder, fname)) as fh:
                    r = json.load(fh)
                total += 1
                if r.get('is_fake'):
                    fake_count += 1
                else:
                    real_count += 1
            except Exception:
                pass  # Skip corrupt result files

    return {
        'total_analyses': total,
        'fake_detected': fake_count,
        'authentic_detected': real_count,
        'last_updated': datetime.now().isoformat(),
    }
