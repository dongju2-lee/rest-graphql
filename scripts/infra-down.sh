#!/bin/bash

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Stopping all case services..."
docker compose -f "$PROJECT_ROOT/docker-compose.case1.yml" down 2>/dev/null || true
docker compose -f "$PROJECT_ROOT/docker-compose.case2.yml" down 2>/dev/null || true
docker compose -f "$PROJECT_ROOT/docker-compose.case3.yml" down 2>/dev/null || true

echo "Stopping infrastructure services..."
docker compose -f "$PROJECT_ROOT/docker-compose.base.yml" down

echo "✓ Infrastructure stopped."
