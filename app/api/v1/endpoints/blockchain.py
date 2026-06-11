#!/usr/bin/env python3
"""
Blockchain Router  —  /api/v1/blockchain

Solana blockchain provenance endpoints.
Ports the following Flask route from api.py:
    POST /api/blockchain/submit  →  POST /api/v1/blockchain/submit
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/blockchain", tags=["Blockchain"])


# ---------------------------------------------------------------------------
# POST /api/v1/blockchain/submit
# ---------------------------------------------------------------------------

@router.post(
    "/submit",
    summary="Submit detection result to Solana blockchain",
    description=(
        "Record an immutable provenance seal for a detection result on the Solana blockchain. "
        "Body: { analysis_id, is_fake, confidence, timestamp }"
    ),
)
async def blockchain_submit(body: dict):
    """
    Submit a detection result to Solana for immutable provenance recording.
    Returns the transaction signature on success.
    """
    analysis_id = body.get('analysis_id')
    if not analysis_id:
        raise HTTPException(status_code=400, detail="analysis_id is required")

    try:
        from integration.integrate import submit_to_solana
        result = submit_to_solana(body)
        return JSONResponse(content={'success': True, 'blockchain_result': result})
    except Exception as exc:
        logger.exception("Blockchain submit failed for %s: %s", analysis_id, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Blockchain submission failed: {exc}",
        )
