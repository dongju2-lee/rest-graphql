#!/bin/bash

# Stop All Services

set -e

# 프로젝트 루트로 이동
cd "$(dirname "$0")/.."

echo "🛑 Stopping all services..."

# Stop full stack
docker-compose -f docker-compose.full.yml down 2>/dev/null || true

echo "✅ All services stopped!"
