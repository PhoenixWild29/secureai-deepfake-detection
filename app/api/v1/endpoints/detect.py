#!/usr/bin/env python3
"""
Detection Router  —  /api/v1/detect

FastAPI router handling all video deepfake detection endpoints.
Ports detection logic from api.py (Flask) to async FastAPI handlers.

Endpoints:
    POST   /api/v1/detect               Upload and analyze a video file
    POST   /api/v1/detect/url           Analyze a video from a URL
    POST   /api/v1/detect/batch         Batch-analyze multiple video files
    GET    /api/v1/detect/status/{id}   Poll analysis status
    GET    /api/v1/detect/results/{id}  Retrieve full results
"""

import os
import uuid
import time
import json
import logging
import asyncio
from datetime import datetime
from typing import Any, Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from app.core.ratelimit import limiter, DETECT_LIMIT, DETECT_BATCH_LIMIT
from werkzeug.utils import secure_filename

from app.api.websockets import sio
# SECURITY: require a valid Bearer JWT on every state-changing detect route.
from app.dependencies.auth import get_current_user
from app.core.config import detection_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/detect", tags=["Detection"])

# Thread pool for CPU-bound ML inference (blocking calls run here)
_executor = ThreadPoolExecutor(max_workers=int(os.getenv('WORKER_THREADS', '2')))

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
RESULTS_FOLDER = os.getenv('RESULTS_FOLDER', 'results')

# SECURITY: cap upload size to prevent memory-exhaustion / DoS via huge uploads.
# Sourced from central config (DETECTION_MAX_FILE_SIZE env / 500 MB default).
MAX_UPLOAD_SIZE_BYTES = detection_settings.detection.max_file_size_bytes
# Read uploads in bounded chunks so we never load an unbounded body into memory.
_UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MiB

# Rate limiting (slowapi): each detect route is decorated with
# @limiter.limit(...) — limits are env-configurable via RATE_LIMIT_DETECT /
# RATE_LIMIT_DETECT_BATCH, with Redis-backed shared storage in production via
# RATE_LIMIT_STORAGE_URI. See app/core/ratelimit.py.


def _enforce_content_length(content_length: Optional[str]) -> None:
    """SECURITY: reject obviously-oversized uploads up front via Content-Length.

    This is a cheap early rejection; the streaming reader below is the
    authoritative cap (Content-Length can be absent or spoofed).
    """
    if content_length:
        try:
            declared = int(content_length)
        except (TypeError, ValueError):
            return
        if declared > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"Upload too large: {declared} bytes exceeds the "
                    f"{MAX_UPLOAD_SIZE_BYTES}-byte limit."
                ),
            )


async def _save_upload_capped(video: UploadFile, filepath: str) -> None:
    """Stream an UploadFile to disk, enforcing MAX_UPLOAD_SIZE_BYTES.

    SECURITY: replaces unbounded ``await video.read()`` so a single request
    cannot exhaust memory or disk. Aborts with HTTP 413 once the cap is hit and
    removes the partial file.
    """
    written = 0
    with open(filepath, 'wb') as fh:
        while True:
            chunk = await video.read(_UPLOAD_CHUNK_SIZE)
            if not chunk:
                break
            written += len(chunk)
            if written > MAX_UPLOAD_SIZE_BYTES:
                fh.close()
                if os.path.exists(filepath):
                    os.remove(filepath)
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"Upload too large: exceeds the "
                        f"{MAX_UPLOAD_SIZE_BYTES}-byte limit."
                    ),
                )
            fh.write(chunk)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _make_json_serializable(obj: Any) -> Any:
    """Recursively convert numpy/custom types to native Python for JSON serialization."""
    try:
        import numpy as np
        if isinstance(obj, dict):
            return {k: _make_json_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_make_json_serializable(x) for x in obj]
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except ImportError:
        pass
    if isinstance(obj, bool):
        return obj
    return obj


def _run_analysis_core(filepath: str, model_type: str = 'enhanced'):
    """
    Run the full detection pipeline synchronously.
    Designed to run inside a ThreadPoolExecutor — blocks until complete.

    Returns:
        tuple: (result, forensic_metrics, security_analysis, elapsed_seconds)
    """
    from ai_model.detect import detect_fake
    from ai_model.morpheus_security import analyze_video_security

    start = time.time()
    result = detect_fake(filepath, model_type)

    try:
        from utils.forensic_metrics import calculate_forensic_metrics
        forensic_metrics = calculate_forensic_metrics(filepath, result, num_frames=16)
    except Exception as exc:
        logger.warning("Forensic metrics calculation failed: %s", exc)
        fake_prob = (
            result.get('confidence', 0.5)
            if result.get('is_fake', False)
            else (1 - result.get('confidence', 0.5))
        )
        forensic_metrics = {
            'spatial_artifacts': fake_prob,
            'temporal_consistency': 0.7,
            'spectral_density': fake_prob * 0.7,
            'vocal_authenticity': 1.0 - (fake_prob * 0.6),
            'audio_analyzed': False,
            'audio_pipeline_status': 'video_only',
            'spatial_entropy_heatmap': [],
        }

    security_analysis = analyze_video_security(filepath, result)
    return result, forensic_metrics, security_analysis, time.time() - start


async def _emit_progress(analysis_id: str, progress: int, status_msg: str, message: str) -> None:
    """Emit a Socket.IO progress event to the analysis room (fire-and-forget)."""
    try:
        await sio.emit(
            'progress',
            {
                'type': 'progress',
                'analysis_id': analysis_id,
                'progress': progress,
                'status': status_msg,
                'message': message,
            },
            room=analysis_id,
        )
    except Exception as exc:
        # No subscribers is normal — don't pollute logs
        logger.debug("Progress emit skipped for %s: %s", analysis_id, exc)


def _save_result(analysis_id: str, result: dict) -> None:
    """Persist analysis result as JSON to the results folder."""
    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    path = os.path.join(RESULTS_FOLDER, f"{analysis_id}.json")
    with open(path, 'w') as fh:
        json.dump(result, fh, indent=2, default=str)


def _load_result(analysis_id: str) -> Optional[dict]:
    """Load a previously saved analysis result, or None if not found."""
    path = os.path.join(RESULTS_FOLDER, f"{analysis_id}.json")
    if os.path.exists(path):
        with open(path, 'r') as fh:
            return json.load(fh)
    return None


# ---------------------------------------------------------------------------
# POST /api/v1/detect  —  upload and analyze a video file
# ---------------------------------------------------------------------------

@router.post(
    "",
    summary="Analyze uploaded video",
    description=(
        "Upload a video file and analyze it for deepfake manipulation. "
        "Emits real-time Socket.IO progress events to the analysis room."
    ),
)
@limiter.limit(DETECT_LIMIT)
async def analyze_video(
    request: Request,  # required by slowapi rate limiter
    video: UploadFile = File(..., description="Video file (mp4, avi, mov, mkv, webm)"),
    model_type: str = Form(default='enhanced', description="Detection model: enhanced | ensemble | fast"),
    analysis_id: Optional[str] = Form(default=None, description="Pre-assigned analysis ID for Socket.IO room"),
    content_length: Optional[str] = Header(default=None),
    current_user: dict = Depends(get_current_user),  # SECURITY: require valid Bearer JWT
):
    """Upload and analyze a single video file for deepfake manipulation."""

    # SECURITY: early-reject oversized uploads using the declared Content-Length.
    _enforce_content_length(content_length)

    if not video.filename:
        raise HTTPException(status_code=400, detail="No video file provided")
    if not _allowed_file(video.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Validate / generate analysis ID
    if analysis_id:
        safe = analysis_id.replace('-', '').replace('_', '')
        if not safe.isalnum() or len(analysis_id) > 120:
            raise HTTPException(status_code=400, detail="Invalid analysis_id format")
        unique_id = analysis_id
    else:
        unique_id = str(uuid.uuid4())

    # Ensure directories exist and are writable
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    if not os.access(UPLOAD_FOLDER, os.W_OK):
        raise HTTPException(status_code=500, detail=f"Upload directory not writable: {UPLOAD_FOLDER}")

    # Save uploaded file to disk
    filename = secure_filename(video.filename)
    ext = filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)

    # SECURITY: stream to disk with a hard size cap (no unbounded read into memory).
    await _save_upload_capped(video, filepath)

    try:
        await _emit_progress(unique_id, 10, 'UPLOADING_MEDIA...', '[UPLOAD] Transferring file to secure node')

        # Optional: AIStore distributed storage
        try:
            from ai_model.aistore_integration import store_video_distributed
            store_video_distributed(filepath, {'analysis_id': unique_id, 'filename': filename})
        except Exception:
            pass  # AIStore is optional

        await _emit_progress(unique_id, 20, 'SEQUENCING_LOCAL_BUFFER...', '[INFERENCE] Mapping media to tensor space')
        await _emit_progress(unique_id, 35, 'RUNNING_MODELS...', '[INFERENCE] Running ensemble detection models')

        # Run the CPU-bound detection pipeline in the thread pool
        loop = asyncio.get_event_loop()
        try:
            result, forensic_metrics, security_analysis, elapsed = await loop.run_in_executor(
                _executor, _run_analysis_core, filepath, model_type
            )
        except Exception as exc:
            logger.exception("Detection pipeline failed for %s: %s", unique_id, exc)
            await sio.emit('error', {'analysis_id': unique_id, 'error': str(exc)}, room=unique_id)
            raise HTTPException(status_code=500, detail=f"Detection failed: {exc}")

        await _emit_progress(unique_id, 85, 'COMPILING_RESULTS...', '[REPORT] Generating forensic report')

        # Build and persist final response
        response = _make_json_serializable({
            **result,
            'analysis_id': unique_id,
            'filename': filename,
            'forensic_metrics': forensic_metrics,
            'security_analysis': security_analysis,
            'analysis_time': f"{elapsed:.2f} seconds",
            'timestamp': datetime.now().isoformat(),
        })
        _save_result(unique_id, response)

        await sio.emit('complete', {'type': 'complete', 'analysis_id': unique_id, 'result': response}, room=unique_id)
        await _emit_progress(unique_id, 100, 'COMPLETE', '[COMPLETE] Analysis finished')

        return JSONResponse(content=response)
    finally:
        # SECURITY/hygiene: always remove the uploaded temp file (success or failure).
        # Results are persisted separately under RESULTS_FOLDER, so this is safe.
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except OSError as cleanup_exc:
            logger.warning("Failed to remove temp upload %s: %s", filepath, cleanup_exc)


# ---------------------------------------------------------------------------
# POST /api/v1/detect/url  —  analyze a video from a URL
# ---------------------------------------------------------------------------

@router.post(
    "/url",
    summary="Analyze video from URL",
    description="Download and analyze a video from a URL (YouTube, Vimeo, direct links).",
)
@limiter.limit(DETECT_LIMIT)
async def analyze_video_url(
    request: Request,  # required by slowapi rate limiter
    body: dict,
    current_user: dict = Depends(get_current_user),  # SECURITY: require valid Bearer JWT
):
    """Analyze a video reachable by URL. Supports YouTube, Vimeo, and direct mp4 links."""

    video_url = (body.get('url') or '').strip()
    if not video_url:
        raise HTTPException(status_code=400, detail="No video URL provided")

    analysis_id = (body.get('analysis_id') or '').strip()
    if analysis_id:
        safe = analysis_id.replace('-', '').replace('_', '')
        if not safe.isalnum() or len(analysis_id) > 120:
            raise HTTPException(status_code=400, detail="Invalid analysis_id format")
        unique_id = analysis_id
    else:
        unique_id = str(uuid.uuid4())

    # Validate URL and check for X/Twitter auth requirement
    try:
        from utils.video_downloader import download_video_from_url, is_valid_video_url
    except ImportError:
        raise HTTPException(status_code=500, detail="Video download not available. Install yt-dlp.")

    if not is_valid_video_url(video_url):
        raise HTTPException(
            status_code=400,
            detail="Invalid video URL. Supported: YouTube, Vimeo, direct video URLs.",
        )

    from urllib.parse import urlparse
    domain = urlparse(video_url).netloc.lower().replace('www.', '')
    is_x = domain.endswith('x.com') or domain.endswith('twitter.com')
    if is_x and not os.getenv('X_COOKIES_FILE', '').strip():
        return JSONResponse(
            status_code=400,
            content={
                'error': (
                    'X/Twitter requires authenticated media access. '
                    'Use the SecureAI Chrome extension or configure X_COOKIES_FILE.'
                ),
                'error_code': 'X_AUTH_REQUIRED',
                'platform': 'x',
            },
        )

    await _emit_progress(unique_id, 10, 'DOWNLOADING...', '[DOWNLOAD] Fetching video from URL')

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    loop = asyncio.get_event_loop()

    try:
        # BUGFIX: download_video_from_url returns a (filepath, filename) tuple —
        # previously the whole tuple was assigned to `filepath`, so the
        # os.path.exists() check below always failed and /url never worked.
        filepath, _downloaded_name = await loop.run_in_executor(
            _executor, download_video_from_url, video_url, UPLOAD_FOLDER
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to download video: {exc}")

    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=500, detail="Video download failed — file not saved.")

    try:
        await _emit_progress(unique_id, 30, 'RUNNING_MODELS...', '[INFERENCE] Running ensemble detection')

        try:
            result, forensic_metrics, security_analysis, elapsed = await loop.run_in_executor(
                _executor, _run_analysis_core, filepath, 'enhanced'
            )
        except Exception as exc:
            logger.exception("URL detection failed for %s: %s", unique_id, exc)
            raise HTTPException(status_code=500, detail=f"Detection failed: {exc}")

        response = _make_json_serializable({
            **result,
            'analysis_id': unique_id,
            'source_url': video_url,
            'forensic_metrics': forensic_metrics,
            'security_analysis': security_analysis,
            'analysis_time': f"{elapsed:.2f} seconds",
            'timestamp': datetime.now().isoformat(),
        })
        _save_result(unique_id, response)

        await sio.emit('complete', {'type': 'complete', 'analysis_id': unique_id, 'result': response}, room=unique_id)
        await _emit_progress(unique_id, 100, 'COMPLETE', '[COMPLETE] Analysis finished')

        return JSONResponse(content=response)
    finally:
        # SECURITY/hygiene: always remove the downloaded temp video after analysis.
        try:
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
        except OSError as cleanup_exc:
            logger.warning("Failed to remove downloaded temp file %s: %s", filepath, cleanup_exc)


# ---------------------------------------------------------------------------
# POST /api/v1/detect/batch  —  batch-analyze multiple video files
# ---------------------------------------------------------------------------

@router.post(
    "/batch",
    summary="Batch analyze videos",
    description="Submit multiple video files for sequential deepfake detection.",
)
@limiter.limit(DETECT_BATCH_LIMIT)
async def batch_analyze(
    request: Request,  # required by slowapi rate limiter
    videos: list[UploadFile] = File(..., description="Video files to analyze"),
    model_type: str = Form(default='enhanced'),
    content_length: Optional[str] = Header(default=None),
    current_user: dict = Depends(get_current_user),  # SECURITY: require valid Bearer JWT
):
    """Batch-analyze multiple video files. Returns a batch_id and per-video results."""

    # SECURITY: reject batches whose total declared body exceeds the size cap.
    _enforce_content_length(content_length)

    if not videos:
        raise HTTPException(status_code=400, detail="No video files provided")

    batch_id = str(uuid.uuid4())
    results = []
    loop = asyncio.get_event_loop()

    for video in videos:
        if not video.filename or not _allowed_file(video.filename):
            results.append({
                'filename': video.filename,
                'status': 'skipped',
                'reason': 'unsupported file format',
            })
            continue

        analysis_id = str(uuid.uuid4())
        filename = secure_filename(video.filename)
        ext = filename.rsplit('.', 1)[1].lower()
        filepath = os.path.join(UPLOAD_FOLDER, f"{analysis_id}.{ext}")

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        # SECURITY: stream each item to disk with a per-file size cap.
        try:
            await _save_upload_capped(video, filepath)
        except HTTPException as size_exc:
            results.append({
                'filename': filename,
                'analysis_id': analysis_id,
                'status': 'skipped',
                'reason': size_exc.detail,
            })
            continue

        try:
            result, forensic_metrics, security_analysis, elapsed = await loop.run_in_executor(
                _executor, _run_analysis_core, filepath, model_type
            )
            response = _make_json_serializable({
                **result,
                'analysis_id': analysis_id,
                'filename': filename,
                'forensic_metrics': forensic_metrics,
                'security_analysis': security_analysis,
                'analysis_time': f"{elapsed:.2f} seconds",
                'timestamp': datetime.now().isoformat(),
            })
            _save_result(analysis_id, response)
            results.append({
                'filename': filename,
                'analysis_id': analysis_id,
                'status': 'complete',
                'result': response,
            })
        except Exception as exc:
            logger.exception("Batch item failed (%s): %s", filename, exc)
            results.append({
                'filename': filename,
                'analysis_id': analysis_id,
                'status': 'error',
                'error': str(exc),
            })
        finally:
            # SECURITY/hygiene: always remove each uploaded temp file.
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except OSError as cleanup_exc:
                logger.warning("Failed to remove temp upload %s: %s", filepath, cleanup_exc)

    return JSONResponse(content={'batch_id': batch_id, 'total': len(videos), 'results': results})


# ---------------------------------------------------------------------------
# GET /api/v1/detect/status/{analysis_id}  —  poll analysis status
# ---------------------------------------------------------------------------

@router.get(
    "/status/{analysis_id}",
    summary="Get analysis status",
    description="Poll the status of an in-progress or completed analysis.",
)
async def get_analysis_status(analysis_id: str):
    """Return current status for an analysis. Returns 'complete' if results exist."""
    result = _load_result(analysis_id)
    if result:
        return {'analysis_id': analysis_id, 'status': 'complete', 'result': result}
    return {'analysis_id': analysis_id, 'status': 'pending_or_not_found'}


# ---------------------------------------------------------------------------
# GET /api/v1/detect/results/{analysis_id}  —  retrieve full results
# ---------------------------------------------------------------------------

@router.get(
    "/results/{analysis_id}",
    summary="Get full analysis results",
    description="Retrieve the complete results for a finished analysis.",
)
async def get_analysis_results(analysis_id: str):
    """Return the full result payload for a completed analysis."""
    result = _load_result(analysis_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No results found for analysis_id: {analysis_id}",
        )
    return result
