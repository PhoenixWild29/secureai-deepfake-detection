# Build context must be the repository root:
#   docker build -f apps/api/Dockerfile -t secureai-api .
#
# apps/api/Dockerfile.dockerignore replaces the root .dockerignore for this
# file. The context is packages/shared and apps/api, not the legacy weights.
#
# This is the rebuild API image. The repository-root Dockerfile is the legacy
# Flask image. Set the Railway Dockerfile path to apps/api/Dockerfile.
FROM python:3.12-slim-bookworm

WORKDIR /srv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY packages/shared /tmp/pkg-shared
COPY apps/api /srv

RUN pip install --no-cache-dir -r /srv/requirements.txt \
    && pip install --no-cache-dir /tmp/pkg-shared \
    && rm -rf /tmp/pkg-shared \
    && useradd --create-home --shell /usr/sbin/nologin --uid 10001 appuser \
    && chown -R appuser:appuser /srv

USER appuser

EXPOSE 8000

# docker_entrypoint.py execs uvicorn, so the server is PID 1 and receives
# SIGTERM. The check is public liveness only. start-period covers Alembic
# before the process listens.
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=3 CMD ["python", "-c", "import os,urllib.request; port=os.environ.get('PORT','8000').strip() or '8000'; urllib.request.urlopen('http://127.0.0.1:%s/health' % port, timeout=4)"]

CMD ["python", "docker_entrypoint.py"]
