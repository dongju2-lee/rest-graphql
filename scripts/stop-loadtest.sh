#!/bin/bash

# Stop Load Testing
set -e

# 프로젝트 루트로 이동
cd "$(dirname "$0")/.."

echo "🛑 부하 테스트 종료 중..."

docker-compose -f load-test/docker-compose.loadtest.yml down

echo "✅ 부하 테스트 종료 완료!"
