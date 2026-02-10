#!/bin/bash

PROJECT_ROOT="/Users/idongju/dev/secret/graph-rest-preform"

echo "Stopping all case services..."
docker compose -f "$PROJECT_ROOT/docker-compose.case1.yml" down 2>/dev/null || true
docker compose -f "$PROJECT_ROOT/docker-compose.case2.yml" down 2>/dev/null || true
docker compose -f "$PROJECT_ROOT/docker-compose.case3.yml" down 2>/dev/null || true

echo "✓ Case services stopped."
echo "  Infrastructure (Prometheus, Grafana, PostgreSQL) is still running."
echo ""
echo "To stop infrastructure: ./scripts/infra-down.sh"
