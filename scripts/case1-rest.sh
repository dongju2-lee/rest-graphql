#!/bin/bash
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Starting Case 1: REST Gateway..."
docker compose -f "$PROJECT_ROOT/docker-compose.case1.yml" up -d --build

echo "Waiting for services to be healthy..."
for i in {1..30}; do
  if curl -sf http://localhost:10000/health > /dev/null 2>&1; then
    echo "✓ REST Gateway is ready!"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "ERROR: Gateway failed to start in time"
    exit 1
  fi
  echo "Waiting... ($i/30)"
  sleep 2
done

echo ""
echo "✓ Case 1 (REST) ready!"
echo "  Gateway: http://localhost:10000"
echo "  Health:  http://localhost:10000/health"
echo ""
echo "Example endpoints:"
echo "  curl http://localhost:10000/api/fleet/dashboard"
echo "  curl http://localhost:10000/api/robots/robot-001/monitor"
echo "  curl http://localhost:10000/api/alerts/critical"
