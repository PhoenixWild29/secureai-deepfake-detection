# Build context must be the repository root:
#   docker build -f apps/worker/Dockerfile -t secureai-worker .
FROM python:3.12-slim-bookworm

WORKDIR /srv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    QUEUE_BACKEND=memory

COPY packages/shared /tmp/pkg-shared
COPY packages/detector /tmp/pkg-detector
COPY apps/worker /tmp/pkg-worker

RUN pip install --no-cache-dir /tmp/pkg-shared /tmp/pkg-detector /tmp/pkg-worker \
    && rm -rf /tmp/pkg-shared /tmp/pkg-detector /tmp/pkg-worker \
    && useradd --create-home --shell /usr/sbin/nologin --uid 10001 appuser

USER appuser

CMD ["python", "-m", "worker"]
