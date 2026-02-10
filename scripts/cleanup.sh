#!/bin/bash

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Stopping and removing all services..."
docker compose -f "$PROJECT_ROOT/docker-compose.case1.yml" down -v --rmi local 2>/dev/null || true
docker compose -f "$PROJECT_ROOT/docker-compose.case2.yml" down -v --rmi local 2>/dev/null || true
docker compose -f "$PROJECT_ROOT/docker-compose.case3.yml" down -v --rmi local 2>/dev/null || true
docker compose -f "$PROJECT_ROOT/docker-compose.base.yml" down -v --rmi local

echo "Removing network..."
docker network rm fleet-net 2>/dev/null || true

echo ""
echo "✓ All cleaned up!"
echo "  - All containers stopped and removed"
echo "  - Volumes deleted"
echo "  - Local images removed"
echo "  - Network removed"
