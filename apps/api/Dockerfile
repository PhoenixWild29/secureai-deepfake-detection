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

CMD ["sh", "-c", "uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
