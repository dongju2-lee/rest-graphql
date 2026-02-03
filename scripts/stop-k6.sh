#!/bin/bash

# Stop k6 Load Testing
set -e

# 프로젝트 루트로 이동
cd "$(dirname "$0")/.."

echo "🛑 k6 테스트 종료 중..."

docker-compose -f k6-test/docker-compose.k6.yml down

echo "✅ k6 테스트 종료 완료!"
echo ""
echo "💡 결과는 Grafana에서 확인하세요:"
echo "   http://localhost:33000"
echo ""
