#!/usr/bin/env python3
"""
Sage Router  —  /api/v1/sage

SecureSage AI consultant endpoints (Google Gemini proxy).
Ports the following Flask route from api.py:
    POST /api/sage/chat  →  POST /api/v1/sage/chat
"""

import os
import logging

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sage", tags=["SecureSage"])

_SYSTEM_CONTEXT = (
    "You are SecureSage, an expert AI security consultant specialising in deepfake detection, "
    "digital forensics, and media authenticity verification. "
    "Provide clear, accurate, and professional guidance to help users understand and act on "
    "detection results. Do not speculate beyond the evidence presented."
)


# ---------------------------------------------------------------------------
# POST /api/v1/sage/chat
# ---------------------------------------------------------------------------

@router.post(
    "/chat",
    summary="SecureSage AI consultant chat",
    description=(
        "Forward a message to the SecureSage AI consultant powered by Google Gemini. "
        "Body: { message, context? }"
    ),
)
async def sage_chat(body: dict):
    """
    Forward a user message to the SecureSage Gemini-powered AI consultant.
    Returns the assistant's response text.
    """
    message = (body.get('message') or '').strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    gemini_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
    if not gemini_key:
        raise HTTPException(
            status_code=503,
            detail="SecureSage AI is not configured. Set GOOGLE_API_KEY in environment.",
        )

    try:
        import google.generativeai as genai  # type: ignore

        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-pro')

        # Prepend context if provided by the frontend
        context = (body.get('context') or '').strip()
        full_prompt = _SYSTEM_CONTEXT
        if context:
            full_prompt += f"\n\nContext: {context}"
        full_prompt += f"\n\nUser: {message}"

        response = model.generate_content(full_prompt)
        reply = response.text if response.text else "I was unable to generate a response at this time."

        return {'response': reply, 'model': 'gemini-pro'}

    except Exception as exc:
        logger.exception("Sage chat error: %s", exc)
        raise HTTPException(status_code=500, detail=f"SecureSage error: {exc}")
