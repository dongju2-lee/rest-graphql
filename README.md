# REST vs GraphQL Performance Comparison

로봇 모니터링 시스템을 통한 REST API와 GraphQL Federation 성능 비교 프로젝트

## 📋 프로젝트 개요

이 프로젝트는 **동일한 비즈니스 로직**을 REST API와 GraphQL로 구현하여 성능을 정량적으로 비교합니다.

### 핵심 목표

- **Over-fetching 비교**: REST는 모든 필드 반환 vs GraphQL은 요청된 필드만
- **Cross-service Join**: REST는 여러 요청 vs GraphQL은 단일 쿼리
- **N+1 문제 해결**: REST는 수동 최적화 vs GraphQL은 DataLoader 자동 배치
- **Complex Aggregation**: REST는 클라이언트 조합 vs GraphQL은 서버 조합

### 기술 스택

#### GraphQL (프로덕션 수준)
- **Framework**: FastAPI + Strawberry GraphQL
- **Federation**: Apollo Router (Federation 2.0)
- **최적화**: DataLoader (자동 배치, N+1 해결)
- **Architecture**: Clean Architecture (schema, models, data, core, utils)

#### REST (간단한 구현)
- **Framework**: FastAPI
- **Gateway**: NGINX
- **최적화**: 수동 batch 엔드포인트

#### Infrastructure
- **Monitoring**: Prometheus + Grafana + cAdvisor
- **Load Testing**: Locust
- **Containerization**: Docker + Docker Compose

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                     Monitoring Stack                             │
│  Prometheus (39090) + Grafana (33000) + cAdvisor (38080)       │
└─────────────────────────────────────────────────────────────────┘
           │                                    │
           ▼                                    ▼
┌──────────────────────────┐      ┌──────────────────────────┐
│    GraphQL Stack          │      │     REST Stack           │
│                           │      │                          │
│  Apollo Router (14000)    │      │  NGINX Gateway (24000)   │
│         │                 │      │         │                │
│    ┌────┴────┐            │      │    ┌────┴────┐           │
│    │ User    │            │      │    │ User    │           │
│    │ Robot   │            │      │    │ Robot   │           │
│    │ Site    │            │      │    │ Site    │           │
│    └─────────┘            │      │    └─────────┘           │
│  (Federation 2.0)         │      │  (Independent APIs)      │
└──────────────────────────┘      └──────────────────────────┘
```

## 🚀 빠른 시작

### 필수 요구사항

- Docker Desktop
- 최소 8GB RAM (권장: 16GB)
- Docker Compose v2.0+

### 1. 전체 스택 실행

```bash
# 모든 서비스 시작 (11 컨테이너)
./scripts/start-all.sh

# 또는 수동으로
docker-compose -f docker-compose.full.yml up -d --build
```

### 2. 개별 스택 실행 (메모리 절약)

```bash
# GraphQL만 실행
./scripts/start-graphql.sh

# REST만 실행
./scripts/start-rest.sh

# 모니터링만 실행
./scripts/start-monitoring.sh
```

### 3. 접속 주소

| Service | URL | 비고 |
|---------|-----|------|
| **GraphQL API** | http://localhost:14000 | Apollo Router |
| **REST API** | http://localhost:24000 | NGINX Gateway |
| **Grafana** | http://localhost:33000 | admin / admin |
| **Prometheus** | http://localhost:39090 | 메트릭 조회 |
| **cAdvisor** | http://localhost:38080 | 컨테이너 모니터링 |
| **Locust (GraphQL)** | http://localhost:48089 | 부하 테스트 |
| **Locust (REST)** | http://localhost:58089 | 부하 테스트 |

## 📊 성능 테스트 실행

### 1. Locust 시작

```bash
# GraphQL 부하 테스트
cd load-test
docker-compose -f docker-compose.loadtest.yml up locust-graphql -d

# REST 부하 테스트
docker-compose -f docker-compose.loadtest.yml up locust-rest -d
```

### 2. Locust Web UI에서 테스트 설정

- **GraphQL**: http://localhost:48089
- **REST**: http://localhost:58089

테스트 설정 예시:
- **Number of users**: 10 (동시 사용자)
- **Spawn rate**: 2 (초당 증가율)
- **Host**: 자동 설정됨

### 3. Grafana에서 모니터링

http://localhost:33000 접속 후:
1. 좌측 메뉴 > Dashboards
2. "Container Metrics - REST vs GraphQL" 선택
3. 실시간 CPU, 메모리, 네트워크 확인

## 🧪 테스트 시나리오

### Scenario 1: Over-fetching (단순 쿼리)

**GraphQL** (필요한 필드만):
```graphql
query {
  users {
    id
    name
    email
  }
}
```

**REST** (모든 필드 반환):
```bash
curl http://localhost:24000/api/users
```

### Scenario 2: Cross-Service Join (1-hop)

**GraphQL** (단일 쿼리):
```graphql
query {
  user(id: "1") {
    id
    name
    robots {
      id
      name
      status
    }
  }
}
```

**REST** (2개 요청):
```bash
curl http://localhost:24000/api/users/1
curl http://localhost:24000/api/robots/by-owner/1
```

### Scenario 3: N+1 Problem

**GraphQL** (DataLoader 자동 배치):
```graphql
query {
  users {
    id
    name
    robots {
      id
      name
    }
  }
}
```
→ 내부적으로 `2개 쿼리` (users + batch robots)

**REST** (순진한 구현):
```bash
curl http://localhost:24000/api/users
# For each user:
curl http://localhost:24000/api/robots/by-owner/{user_id}
```
→ `101개 요청` (1 + 100)

### Scenario 4: Complex Aggregation

**GraphQL** (단일 쿼리, 서버 조합):
```graphql
query {
  site(id: "1") { name }
  usersBySite(siteId: 1) {
    id
    robots { id status }
  }
  robotsBySite(siteId: 1) {
    id
    owner { name }
  }
}
```

**REST** (여러 요청, 클라이언트 조합):
```bash
curl http://localhost:24000/api/sites/1
curl http://localhost:24000/api/users/by-site/1
curl http://localhost:24000/api/robots/by-site/1
# + 각 사용자별 robots 요청...
```

## 📁 프로젝트 구조

```
graph-rest-preform/
├── backend/
│   ├── graphql/                   # GraphQL 스택 (프로덕션 수준)
│   │   ├── services/
│   │   │   ├── user-service/      # User Subgraph
│   │   │   ├── robot-service/     # Robot Subgraph (DataLoader)
│   │   │   └── site-service/      # Site Subgraph
│   │   ├── gateway/               # Apollo Router
│   │   └── docker-compose.yml
│   └── rest/                      # REST 스택 (간단한 구현)
│       ├── services/
│       │   ├── user-service/
│       │   ├── robot-service/
│       │   └── site-service/
│       ├── gateway/               # NGINX
│       └── docker-compose.yml
├── monitoring/                    # 모니터링 스택
│   ├── prometheus/
│   ├── grafana/
│   └── docker-compose.monitoring.yml
├── load-test/                     # 부하 테스트
│   ├── locustfile_graphql.py
│   ├── locustfile_rest.py
│   └── docker-compose.loadtest.yml
├── scripts/                       # 실행 스크립트
│   ├── start-all.sh
│   ├── start-graphql.sh
│   ├── start-rest.sh
│   └── stop-all.sh
├── docs/                          # 문서
│   ├── cursor/                    # 설계 문서
│   └── 개발로그.md
├── docker-compose.full.yml        # 통합 실행
└── README.md
```

## 🎯 예상 결과

### GraphQL 예상 강점
- ✅ **Over-fetching 방지**: 40-60% 네트워크 절약
- ✅ **N+1 해결**: DataLoader로 자동 배치 (100배 성능 향상)
- ✅ **단일 엔드포인트**: 클라이언트 코드 단순화
- ✅ **타입 안전성**: 스키마 기반 자동 검증

### REST 예상 강점
- ✅ **단순성**: 학습 곡선 낮음
- ✅ **캐싱**: HTTP 캐싱 활용 용이
- ✅ **디버깅**: 표준 HTTP 도구 사용 가능
- ✅ **수동 최적화**: Batch 엔드포인트로 개선 가능

## 🛠️ 개발 가이드

### GraphQL Service 추가

```bash
cd backend/graphql/services
cp -r user-service new-service
# src/ 내부 수정:
# - core/config.py (포트, 설정)
# - models/ (도메인 모델)
# - data/repository.py (데이터 계층)
# - schema/ (GraphQL 타입, 쿼리)
```

### REST Service 추가

```bash
cd backend/rest/services
cp -r user-service new-service
# src/main.py 수정
```

## 📊 메트릭 수집

### Prometheus Queries

```promql
# CPU 사용률
rate(container_cpu_usage_seconds_total{name=~".*-service"}[1m]) * 100

# 메모리 사용량
container_memory_usage_bytes{name=~".*-service"} / 1024 / 1024

# 네트워크 I/O
rate(container_network_receive_bytes_total{name=~".*-service"}[1m])
```

### Locust 메트릭

- **RPS** (Requests Per Second)
- **Latency** (P50, P95, P99)
- **Failure Rate**

## 🔧 트러블슈팅

### Docker 빌드 실패
```bash
# 캐시 없이 재빌드
docker-compose -f docker-compose.full.yml build --no-cache
```

### 포트 충돌
```bash
# 사용 중인 포트 확인
lsof -i :14000
lsof -i :24000

# 해당 프로세스 종료 후 재시작
```

### 메모리 부족 (8GB RAM)
```bash
# 순차적으로 실행 (REST와 GraphQL을 번갈아)
./scripts/start-graphql.sh
# 테스트 후
docker-compose -f backend/graphql/docker-compose.yml down

./scripts/start-rest.sh
```

## 📝 참고 문서

- [프로젝트 목표 정리](./docs/cursor/프로젝트_목표_정리.md)
- [프로젝트 구조 V2](./docs/cursor/프로젝트_구조_v2.md)
- [API 설계 상세](./docs/cursor/API-설계-상세.md)
- [Docker Compose 경량 구조](./docs/cursor/docker-compose-경량.md)
- [개발 로그](./docs/개발로그.md)

## 🧹 정리

```bash
# 모든 컨테이너 중지 및 제거
./scripts/stop-all.sh

# 볼륨까지 완전 삭제
docker-compose -f docker-compose.full.yml down -v

# 이미지 삭제
docker system prune -a
```

## 📄 라이센스

MIT License

## 👥 기여

이슈 및 PR 환영합니다!

---

**Made with ❤️ for learning REST vs GraphQL performance characteristics**
