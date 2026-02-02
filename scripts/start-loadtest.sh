#!/bin/bash

# Load Test Runner for REST vs GraphQL Performance Comparison
set -e

# 프로젝트 루트로 이동
cd "$(dirname "$0")/.."

# 기본값
API_TYPE="all"
USERS=100
SPAWN_RATE=10
DURATION=""  # 빈값이면 Web UI 모드, 값이 있으면 headless 모드

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Help 함수
show_help() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 REST vs GraphQL 부하 테스트"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "사용법: $0 [OPTIONS] <api_type>"
    echo ""
    echo "API Types:"
    echo "  rest      REST API만 테스트 (포트 58089)"
    echo "  graph     GraphQL API만 테스트 (포트 48089)"
    echo "  all       둘 다 테스트 (기본값)"
    echo ""
    echo "Options:"
    echo "  -u, --users <num>       동시 사용자 수 (기본: 100)"
    echo "  -r, --rate <num>        초당 사용자 증가율 (기본: 10)"
    echo "  -t, --time <seconds>    테스트 시간 (초). 지정시 headless 모드"
    echo "  -h, --help              도움말 표시"
    echo ""
    echo "예시:"
    echo "  $0 rest                 REST만 테스트 (Web UI)"
    echo "  $0 graph -u 200         GraphQL 200명 동시 테스트 (Web UI)"
    echo "  $0 all -u 50 -r 5       둘 다 50명, 초당 5명씩 (Web UI)"
    echo "  $0 rest -t 60           REST 60초 테스트 (headless)"
    echo "  $0 all -u 100 -t 600    둘 다 100명, 10분간 테스트"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    exit 0
}

# 인자 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--users)
            USERS="$2"
            shift 2
            ;;
        -r|--rate)
            SPAWN_RATE="$2"
            shift 2
            ;;
        -t|--time)
            DURATION="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            ;;
        rest|graph|all)
            API_TYPE="$1"
            shift
            ;;
        *)
            echo -e "${RED}오류: 알 수 없는 옵션 '$1'${NC}"
            echo "도움말: $0 --help"
            exit 1
            ;;
    esac
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 부하 테스트 시작"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "  API Type:    ${GREEN}${API_TYPE}${NC}"
echo -e "  Users:       ${GREEN}${USERS}${NC}"
echo -e "  Spawn Rate:  ${GREEN}${SPAWN_RATE}/sec${NC}"
if [[ -n "$DURATION" ]]; then
    echo -e "  Duration:    ${GREEN}${DURATION}s${NC} (headless 모드)"
else
    echo -e "  Mode:        ${GREEN}Web UI${NC}"
fi
echo ""

# 네트워크 확인
echo "📡 네트워크 확인 중..."
if ! docker network ls | grep -q graphql-network; then
    echo -e "${RED}⚠️  graphql-network가 없습니다. quick-start.sh를 먼저 실행하세요!${NC}"
    exit 1
fi
if ! docker network ls | grep -q rest-network; then
    echo -e "${RED}⚠️  rest-network가 없습니다. quick-start.sh를 먼저 실행하세요!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 네트워크 확인 완료${NC}"
echo ""

# 기존 Locust 컨테이너 정리
echo "🧹 기존 Locust 컨테이너 정리..."
docker-compose -f load-test/docker-compose.loadtest.yml down 2>/dev/null || true
echo ""

# Locust 이미지 빌드 (변경사항 있을 때만)
echo "🔨 Locust 이미지 빌드 중..."
docker-compose -f load-test/docker-compose.loadtest.yml build --quiet
echo ""

# Locust 시작
echo "🚀 Locust 컨테이너 시작 중..."

if [[ -n "$DURATION" ]]; then
    # Headless 모드 (duration 지정됨)
    LOCUST_OPTS="--headless -u ${USERS} -r ${SPAWN_RATE} -t ${DURATION}s"

    start_graphql_headless() {
        echo -e "  ${BLUE}→ GraphQL Locust (headless) 시작...${NC}"
        docker-compose -f load-test/docker-compose.loadtest.yml run --rm \
            -p 49646:9646 \
            locust-graphql \
            locust -f /app/locustfile_graphql.py --host=http://apollo-router:4000 ${LOCUST_OPTS}
    }

    start_rest_headless() {
        echo -e "  ${BLUE}→ REST Locust (headless) 시작...${NC}"
        docker-compose -f load-test/docker-compose.loadtest.yml run --rm \
            -p 59646:9646 \
            locust-rest \
            locust -f /app/locustfile_rest.py --host=http://nginx-gateway:80 ${LOCUST_OPTS}
    }

    case $API_TYPE in
        rest)
            start_rest_headless
            ;;
        graph)
            start_graphql_headless
            ;;
        all)
            echo -e "  ${YELLOW}→ GraphQL + REST 동시 실행...${NC}"
            start_graphql_headless &
            PID_GRAPHQL=$!
            start_rest_headless &
            PID_REST=$!

            # 둘 다 완료될 때까지 대기
            wait $PID_GRAPHQL
            wait $PID_REST
            ;;
    esac

    echo ""
    echo -e "${GREEN}✅ 부하 테스트 완료!${NC}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📈 결과 확인: http://localhost:33000 (Grafana)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
else
    # Web UI 모드 (duration 미지정)
    start_graphql() {
        echo -e "  ${BLUE}→ GraphQL Locust 시작...${NC}"
        docker-compose -f load-test/docker-compose.loadtest.yml up -d locust-graphql
    }

    start_rest() {
        echo -e "  ${BLUE}→ REST Locust 시작...${NC}"
        docker-compose -f load-test/docker-compose.loadtest.yml up -d locust-rest
    }

    case $API_TYPE in
        rest)
            start_rest
            ;;
        graph)
            start_graphql
            ;;
        all)
            start_graphql
            start_rest
            ;;
    esac

    echo ""
    echo -e "${GREEN}✅ Locust 시작 완료!${NC}"
    echo ""

    # 접속 정보 출력
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🌐 Locust Web UI"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    if [[ "$API_TYPE" == "graph" || "$API_TYPE" == "all" ]]; then
        echo -e "  📊 GraphQL: ${GREEN}http://localhost:48089${NC}"
    fi
    if [[ "$API_TYPE" == "rest" || "$API_TYPE" == "all" ]]; then
        echo -e "  📊 REST:    ${GREEN}http://localhost:58089${NC}"
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💡 사용 방법"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  1. 위 URL을 브라우저에서 열기"
    echo "  2. 설정값 입력:"
    echo -e "     - Number of users: ${YELLOW}${USERS}${NC}"
    echo -e "     - Spawn rate: ${YELLOW}${SPAWN_RATE}${NC}"
    echo "  3. 'Start swarming' 클릭"
    echo ""
    echo "  📈 Grafana 대시보드:"
    echo "     - Container Metrics: http://localhost:33000/d/container-metrics"
    echo "     - Load Test Metrics: http://localhost:33000/d/loadtest-metrics"
    echo "  🛑 종료: ./scripts/stop-loadtest.sh"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
fi
