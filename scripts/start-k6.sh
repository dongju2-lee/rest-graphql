#!/bin/bash

# Start k6 Load Testing
set -e

# 프로젝트 루트로 이동
cd "$(dirname "$0")/.."

# 기본값
VUS=50
ITERATIONS=10000
DURATION="10m"

# 옵션 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--users)
            VUS="$2"
            shift 2
            ;;
        -i|--iterations)
            ITERATIONS="$2"
            shift 2
            ;;
        -d|--duration)
            DURATION="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -u, --users N        가상 사용자 수 (기본: 50)"
            echo "  -i, --iterations N   총 요청 수 (기본: 10000)"
            echo "  -d, --duration TIME  최대 실행 시간 (기본: 10m)"
            echo ""
            echo "Examples:"
            echo "  $0                           # 기본값: 50명, 10000번"
            echo "  $0 -u 100 -i 20000           # 100명, 20000번"
            echo "  $0 -u 200 -i 50000 -d 30m    # 200명, 50000번, 30분"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 k6 성능 테스트 시작 (정확한 요청 수 비교)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚙️  테스트 설정:"
echo "   - 가상 사용자: $VUS 명"
echo "   - 총 요청 수: $ITERATIONS 번"
echo "   - 최대 실행 시간: $DURATION"
echo ""

# 네트워크 확인 및 생성
echo "📡 네트워크 확인 중..."

# 필요한 네트워크 목록
NETWORKS=("graphql-network" "rest-network" "monitoring-network")
CREATED_ANY=false

for network in "${NETWORKS[@]}"; do
    if ! docker network ls | grep -q "$network"; then
        echo "   ⚠️  $network가 없습니다. 생성 중..."
        docker network create "$network"
        CREATED_ANY=true
    fi
done

if [ "$CREATED_ANY" = true ]; then
    echo ""
    echo "   💡 Tip: quick-start.sh를 실행하면 모든 서비스와 함께 네트워크가 관리됩니다."
    echo ""
fi

echo "✅ 네트워크 준비 완료"
echo ""

# Prometheus 확인
echo "📈 Prometheus 확인 중..."
if ! docker ps | grep -q prometheus; then
    echo "⚠️  경고: Prometheus가 실행되지 않았습니다."
    echo "   quick-start.sh를 먼저 실행하세요!"
    exit 1
fi
echo "✅ Prometheus 준비 완료"
echo ""

# k6 빌드
echo "🔨 k6 이미지 빌드 중..."
docker-compose -f k6-test/docker-compose.k6.yml build
echo "✅ 빌드 완료"
echo ""

# k6 실행
echo "🚀 k6 테스트 시작..."
echo ""

# 환경 변수 설정
export K6_VUS=$VUS
export K6_ITERATIONS=$ITERATIONS
export K6_DURATION=$DURATION

# GraphQL과 REST 동시 실행
docker-compose -f k6-test/docker-compose.k6.yml up -d

echo ""
echo "✅ k6 테스트 실행 중!"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 실시간 모니터링"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  1️⃣  GraphQL 로그 (실시간)"
echo "     docker logs -f k6-graphql"
echo ""
echo "  2️⃣  REST 로그 (실시간)"
echo "     docker logs -f k6-rest"
echo ""
echo "  3️⃣  Grafana 대시보드"
echo "     http://localhost:33000"
echo "     → Dashboards → k6 Performance Test"
echo ""
echo "  4️⃣  Prometheus 메트릭"
echo "     http://localhost:39090"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 Tip:"
echo ""
echo "  • 테스트는 약 2-5분 소요됩니다"
echo "  • 완료되면 컨테이너가 자동 종료됩니다"
echo "  • 결과는 Grafana에서 확인하세요!"
echo ""
echo "  종료: ./scripts/stop-k6.sh"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 로그 자동 표시
echo "📊 실시간 로그를 표시합니다..."
echo "   (테스트 완료 시 자동으로 종료됩니다)"
echo ""
sleep 1

# tmux 세션이 있으면 먼저 삭제
if command -v tmux &> /dev/null; then
    tmux kill-session -t k6-logs 2>/dev/null || true
fi

# 컨테이너가 종료될 때까지 로그 표시
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 GraphQL 테스트 로그"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker logs -f k6-graphql 2>&1 &
GRAPHQL_PID=$!

# GraphQL이 끝날 때까지 대기
wait $GRAPHQL_PID

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 REST 테스트 로그"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker logs k6-rest 2>&1

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ k6 테스트 완료!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 결과 비교:"
echo "   - GraphQL 로그: 위 참조"
echo "   - REST 로그: 위 참조"
echo ""
echo "📈 Grafana 대시보드:"
echo "   http://localhost:33000/d/container-metrics"
echo ""
echo "💡 Tip: Container Metrics 대시보드에서 리소스 사용량을 확인하세요!"
echo ""
