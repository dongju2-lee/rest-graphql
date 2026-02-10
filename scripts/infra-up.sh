#!/bin/bash
set -e

PROJECT_ROOT="/Users/idongju/dev/secret/graph-rest-preform"

echo "Starting infrastructure services..."
docker compose -f "$PROJECT_ROOT/docker-compose.base.yml" up -d

echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
  if docker compose -f "$PROJECT_ROOT/docker-compose.base.yml" exec -T postgres pg_isready -U fleet > /dev/null 2>&1; then
    echo "PostgreSQL is ready!"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "ERROR: PostgreSQL failed to start in time"
    exit 1
  fi
  echo "Waiting... ($i/30)"
  sleep 2
done

echo "Running seed data..."
docker run --rm \
  --network fleet-net \
  -e DATABASE_URL=postgresql+asyncpg://fleet:fleet123@postgres:5432/robot_fleet \
  -v "$PROJECT_ROOT/shared:/app/shared" \
  -w /app \
  python:3.11-slim \
  bash -c "pip install -q sqlalchemy asyncpg && python -m shared.db.seed"

echo ""
echo "✓ Infrastructure ready!"
echo "  Grafana:    http://localhost:13000 (admin/admin)"
echo "  Prometheus: http://localhost:19090"
echo "  PostgreSQL: localhost:15432"
echo ""
echo "Next steps:"
echo "  - Start a case: ./scripts/case1-rest.sh"
echo "  - Run k6 test: ./scripts/k6-duration.sh --case 1 --vus 2 --duration 10s"
