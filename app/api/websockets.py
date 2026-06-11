#!/usr/bin/env python3
"""
Socket.IO ASGI server for real-time analysis progress updates.

Uses python-socketio AsyncServer in ASGI mode to maintain full
compatibility with the frontend Socket.IO client (socket.io-client@4.x).

The ASGI app is mounted onto the FastAPI app in app/main.py:
    app.mount('/socket.io', socket_app)

Frontend connects via:
    const socket = io('http://host', { transports: ['polling', 'websocket'] })

Events emitted to rooms:
    - progress  { type, analysis_id, progress, status, message }
    - complete  { type, analysis_id, result }
    - error     { analysis_id, error }

Events received from clients:
    - subscribe   { analysis_id }
    - unsubscribe { analysis_id }
"""

import os
import logging
import socketio

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared Socket.IO AsyncServer
# Other modules (e.g. detect.py) import `sio` to emit progress events.
# ---------------------------------------------------------------------------
_cors_env = os.getenv('CORS_ORIGINS', '*')
_cors_origins = _cors_env.split(',') if ',' in _cors_env else _cors_env

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=_cors_origins,
    logger=False,
    engineio_logger=False,
    ping_timeout=int(os.getenv('SOCKETIO_PING_TIMEOUT', '60')),
    ping_interval=int(os.getenv('SOCKETIO_PING_INTERVAL', '25')),
)

# ASGI app — mounted at /socket.io in app/main.py
socket_app = socketio.ASGIApp(sio)


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------

@sio.event
async def connect(sid, environ, auth=None):
    """Client connected — log for diagnostics."""
    logger.info("Socket.IO client connected: %s", sid)


@sio.event
async def disconnect(sid):
    """Client disconnected."""
    logger.info("Socket.IO client disconnected: %s", sid)


# ---------------------------------------------------------------------------
# Room subscription events
# ---------------------------------------------------------------------------

@sio.event
async def subscribe(sid, data):
    """
    Subscribe a client to an analysis room so it receives progress/complete/error events.

    Frontend sends:
        socket.emit('subscribe', { analysis_id: '<uuid>' })
    """
    try:
        analysis_id = None
        if isinstance(data, dict):
            analysis_id = data.get('analysis_id') or data.get('analysisId')
        if not analysis_id:
            return {'ok': False, 'error': 'analysis_id is required'}

        await sio.enter_room(sid, str(analysis_id))
        logger.info("Client %s subscribed to room %s", sid, analysis_id)
        return {'ok': True, 'analysis_id': str(analysis_id)}
    except Exception as exc:
        logger.exception("Socket.IO subscribe error: %s", exc)
        return {'ok': False, 'error': str(exc)}


@sio.event
async def unsubscribe(sid, data):
    """
    Unsubscribe a client from an analysis room.

    Frontend sends:
        socket.emit('unsubscribe', { analysis_id: '<uuid>' })
    """
    try:
        analysis_id = None
        if isinstance(data, dict):
            analysis_id = data.get('analysis_id') or data.get('analysisId')
        if analysis_id:
            await sio.leave_room(sid, str(analysis_id))
        return {'ok': True}
    except Exception as exc:
        logger.exception("Socket.IO unsubscribe error: %s", exc)
        return {'ok': False, 'error': str(exc)}
