#!/bin/bash

# Start Load Testing
set -e

# 프로젝트 루트로 이동
cd "$(dirname "$0")/.."

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 부하 테스트 시작"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 네트워크 확인
echo "📡 네트워크 확인 중..."
docker network ls | grep -q graphql-network || echo "⚠️  경고: graphql-network가 없습니다. quick-start.sh를 먼저 실행하세요!"
docker network ls | grep -q rest-network || echo "⚠️  경고: rest-network가 없습니다. quick-start.sh를 먼저 실행하세요!"
echo ""

# Locust 시작
echo "🚀 Locust 컨테이너 시작 중..."
docker-compose -f load-test/docker-compose.loadtest.yml up -d
echo "✅ Locust 시작 완료!"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 부하 테스트 준비 완료!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Locust 웹 UI:"
echo ""
echo "  📊 GraphQL 부하 테스트"
echo "     → http://localhost:48089"
echo ""
echo "  📊 REST 부하 테스트"
echo "     → http://localhost:58089"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 사용 방법:"
echo ""
echo "  1. 브라우저에서 http://localhost:48089 또는 58089 열기"
echo "  2. 설정:"
echo "     - Number of users: 100 (동시 사용자 수)"
echo "     - Spawn rate: 10 (초당 증가율)"
echo "  3. 'Start swarming' 클릭"
echo "  4. Grafana(http://localhost:33000)에서 실시간 모니터링"
echo ""
echo "  종료: ./scripts/stop-loadtest.sh"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
