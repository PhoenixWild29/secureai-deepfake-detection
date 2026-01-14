#!/bin/bash
# Fix common production issue: bind-mounted uploads/results are not writable by the container user.

set -euo pipefail

echo "=========================================="
echo "🔧 Fix Backend Permissions (uploads/results)"
echo "=========================================="
echo ""

if ! command -v docker >/dev/null 2>&1; then
  echo "❌ docker not found"
  exit 1
fi

BACKEND_CONTAINER="${BACKEND_CONTAINER:-secureai-backend}"

if ! docker ps --format '{{.Names}}' | grep -q "^${BACKEND_CONTAINER}$"; then
  echo "❌ Backend container '${BACKEND_CONTAINER}' is not running."
  echo "   Start it first: docker compose -f docker-compose.https.yml up -d secureai-backend"
  exit 1
fi

echo "1) Detecting container user id (app)..."
APP_UID="$(docker exec "${BACKEND_CONTAINER}" id -u app 2>/dev/null || true)"
APP_GID="$(docker exec "${BACKEND_CONTAINER}" id -g app 2>/dev/null || true)"

if [[ -z "${APP_UID}" || -z "${APP_GID}" ]]; then
  echo "⚠️  Could not resolve 'app' user in container. Falling back to container current user."
  APP_UID="$(docker exec "${BACKEND_CONTAINER}" id -u)"
  APP_GID="$(docker exec "${BACKEND_CONTAINER}" id -g)"
fi

echo "   Using UID:GID = ${APP_UID}:${APP_GID}"
echo ""

echo "2) Fixing host directory ownership + perms..."
for d in uploads results logs run test_videos; do
  if [[ ! -d "$d" ]]; then
    echo "   Creating ./${d}"
    mkdir -p "$d"
  fi
  echo "   chown -R ${APP_UID}:${APP_GID} ./${d}"
  chown -R "${APP_UID}:${APP_GID}" "$d" || true
  echo "   chmod -R u+rwX,g+rwX ./${d}"
  chmod -R u+rwX,g+rwX "$d" || true
done
echo ""

echo "3) Restarting backend..."
if docker compose version >/dev/null 2>&1; then
  docker compose -f docker-compose.https.yml restart secureai-backend
else
  docker-compose -f docker-compose.https.yml restart secureai-backend
fi
echo ""

echo "4) Quick health check..."
curl -s -k https://guardian.secureai.dev/api/health || true
echo ""
echo ""

echo "✅ Done. Re-try scanning a video."
echo "If it still 500s, run:"
echo "  docker logs ${BACKEND_CONTAINER} --tail 200"

