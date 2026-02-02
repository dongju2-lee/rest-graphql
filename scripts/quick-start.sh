#!/bin/bash

# Quick Start Script - REST vs GraphQL 성능 비교 시스템

set -e

# 프로젝트 루트로 이동
cd "$(dirname "$0")/.."

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 REST vs GraphQL 성능 비교 시스템 - 빠른 시작"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. 시스템 상태 확인
echo "📊 Step 1: 시스템 상태 확인..."
if docker info > /dev/null 2>&1; then
    echo "✅ Docker 실행 중"
else
    echo "❌ Docker가 실행되지 않았습니다."
    echo "   Docker Desktop을 실행하고 다시 시도하세요."
    exit 1
fi
echo ""

# 2. 기존 컨테이너 정리
echo "🧹 Step 2: 기존 컨테이너 정리..."
docker-compose -f docker-compose.full.yml down > /dev/null 2>&1 || true
echo "✅ 정리 완료"
echo ""

# 3. 빌드
echo "🔨 Step 3: Docker 이미지 빌드 (약 2-3분 소요)..."
docker-compose -f docker-compose.full.yml build --parallel
echo "✅ 빌드 완료"
echo ""

# 4. 실행
echo "🚀 Step 4: 시스템 시작 (약 30초 소요)..."
docker-compose -f docker-compose.full.yml up -d
echo "✅ 시스템 시작 완료"
echo ""

# 5. Health Check
echo "⏳ Step 5: 서비스 헬스체크 중..."
echo ""

# Docker 컨테이너 헬스체크 함수
check_container() {
    local name=$1
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        local status=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "none")
        if [ "$status" = "healthy" ]; then
            echo "   ✅ $name"
            return 0
        elif [ "$status" = "none" ]; then
            # healthcheck가 없는 경우, running 상태 확인
            if docker ps --filter "name=$name" --filter "status=running" | grep -q "$name"; then
                echo "   ✅ $name (running)"
                return 0
            fi
        fi
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "   ❌ $name (unhealthy or not running)"
    return 1
}

# HTTP 헬스체크 함수
check_http() {
    local name=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo "   ✅ $name"
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "   ❌ $name (타임아웃)"
    return 1
}

# 각 서비스 헬스체크
echo "   🔍 GraphQL Services..."
check_container "graphql-user-service" &
check_container "graphql-robot-service" &
check_container "graphql-site-service" &
wait

echo ""
echo "   🔍 GraphQL Gateway..."
check_http "Apollo Router           " "http://localhost:14000/" &
wait

echo ""
echo "   🔍 REST Services..."
check_container "rest-user-service" &
check_container "rest-robot-service" &
check_container "rest-site-service" &
wait

echo ""
echo "   🔍 REST Gateway..."
check_http "NGINX Gateway           " "http://localhost:24000/health" &
wait

echo ""
echo "   🔍 Monitoring..."
check_http "Prometheus              " "http://localhost:39090/-/healthy" &
check_http "Grafana                 " "http://localhost:33000/api/health" &
wait

echo ""
echo "✅ 모든 서비스 준비 완료!"
echo ""

# 6. 접속 정보 출력
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 시스템이 성공적으로 시작되었습니다!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 접속 주소:"
echo ""
echo "  📊 GraphQL (GraphiQL UI - Swagger 같은 것)"
echo "     → http://localhost:14000"
echo ""
echo "  📊 REST API (Swagger UI)"
echo "     → http://localhost:24000"
echo "     → http://localhost:28000/docs (User Service)"
echo "     → http://localhost:28001/docs (Robot Service)"
echo "     → http://localhost:28002/docs (Site Service)"
echo ""
echo "  📈 Grafana (모니터링 대시보드)"
echo "     → http://localhost:33000"
echo "     → ID: admin, PW: admin"
echo ""
echo "  📉 Prometheus (메트릭)"
echo "     → http://localhost:39090"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 다음 단계:"
echo ""
echo "  1. GraphQL 테스트:"
echo "     → http://localhost:14000 (GraphiQL UI)"
echo ""
echo "  2. REST 테스트:"
echo "     → http://localhost:28000/docs (User Service Swagger)"
echo "     → http://localhost:28001/docs (Robot Service Swagger)"
echo "     → http://localhost:28002/docs (Site Service Swagger)"
echo ""
echo "  3. 모니터링:"
echo "     → http://localhost:33000 (Grafana - admin/admin)"
echo ""
echo "  4. 종료:"
echo "     → ./scripts/stop-all.sh"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎉 준비 완료! 브라우저에서 http://localhost:14000 을 열어보세요!"
echo ""
