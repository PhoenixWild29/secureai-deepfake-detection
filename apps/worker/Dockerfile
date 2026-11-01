# Build context must be the repository root:
#   docker build -f apps/worker/Dockerfile -t secureai-worker .
#
# apps/worker/Dockerfile.dockerignore replaces the root .dockerignore for this
# file. The context is packages/ and apps/worker, not the legacy weights.
#
# The worker package depends on ../../packages/shared and ../../packages/detector.
# Those relative paths only resolve when the monorepo layout is preserved.
FROM python:3.12-slim-bookworm

WORKDIR /srv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MEDIA_ROOT=/srv/media

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY packages /build/packages
COPY apps/worker /build/apps/worker

RUN pip install --no-cache-dir -r /build/apps/worker/requirements.txt \
    && pip install --no-cache-dir /build/apps/worker \
    && rm -rf /build \
    && useradd --create-home --shell /usr/sbin/nologin --uid 10001 appuser \
    && mkdir -p /srv/media \
    && chown -R appuser:appuser /srv

USER appuser

CMD ["python", "-m", "worker"]
