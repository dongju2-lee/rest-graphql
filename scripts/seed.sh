#!/bin/bash
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
  if docker compose -f "$PROJECT_ROOT/docker-compose.base.yml" exec -T postgres pg_isready -U fleet > /dev/null 2>&1; then
    echo "PostgreSQL is ready!"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "ERROR: PostgreSQL is not running. Start infrastructure first: ./scripts/infra-up.sh"
    exit 1
  fi
  echo "Waiting... ($i/30)"
  sleep 2
done

echo "Running seed data script..."

docker run --rm \
  --network fleet-net \
  -e DATABASE_URL=postgresql+asyncpg://fleet:fleet123@postgres:5432/robot_fleet \
  -v "$PROJECT_ROOT/shared:/app/shared" \
  -w /app \
  python:3.11-slim \
  bash -c "pip install -q sqlalchemy asyncpg && python -m shared.db.seed"

echo "✓ Seed data complete!"
