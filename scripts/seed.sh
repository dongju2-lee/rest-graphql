#!/bin/bash
set -e

PROJECT_ROOT="/Users/idongju/dev/secret/graph-rest-preform"

echo "Running seed data script..."

docker run --rm \
  --network fleet-net \
  -e DATABASE_URL=postgresql+asyncpg://fleet:fleet123@postgres:5432/robot_fleet \
  -v "$PROJECT_ROOT/shared:/app/shared" \
  -w /app \
  python:3.11-slim \
  bash -c "pip install -q sqlalchemy asyncpg && python -m shared.db.seed"

echo "✓ Seed data complete!"
