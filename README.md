# REST vs GraphQL Performance Comparison

로봇 모니터링 시스템을 통한 REST API와 GraphQL Federation 성능 비교 프로젝트

## 📋 프로젝트 개요

**동일한 데이터, 동일한 비즈니스 로직, 동일한 latency 시뮬레이션** 환경에서 REST API와 GraphQL의 성능을 RPS(Requests Per Second) 기준으로 비교합니다.

### 핵심 비교 포인트

| 구분 | REST (Microservice) | GraphQL (Federation) |
|------|---------------------|----------------------|
| Over-fetching | 모든 필드 반환 | 요청된 필드만 반환 |
| Cross-service Join | 서비스가 내부적으로 다른 서비스 호출 | Apollo Router가 자동 조합 |
| N+1 문제 | 서비스 내부에서 배치 처리 | DataLoader로 자동 해결 |
| 네트워크 호출 | **항상 1회** (서비스 내부 오케스트레이션) | 항상 1회 |
| 내부 통신 | httpx async client | Federation subgraph 호출 |

### 데이터 모델

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    User     │     │    Robot    │     │    Site     │
├─────────────┤     ├─────────────┤     ├─────────────┤
│ id          │◄────│ owner_id    │     │ id          │
│ name        │     │ site_id     │────►│ name        │
│ email       │     │ name        │     │ location    │
│ role        │     │ model       │     │ timezone    │
│ phone       │     │ status      │     │ capacity    │
│ address     │     │ battery     │     └─────────────┘
│ bio         │     │ location    │
└─────────────┘     └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │  Telemetry  │
                   ├─────────────┤
                   │ robot_id    │
                   │ cpu         │
                   │ memory      │
                   │ disk        │
                   │ temperature │
                   │ error_count │
                   └─────────────┘

User: 100명 | Robot: 500대 | Site: 5개 | Telemetry: 500개 (로봇당 1개)
```

### 기술 스택

| 구분 | GraphQL | REST |
|------|---------|------|
| Framework | FastAPI + Strawberry | FastAPI |
| Gateway | Apollo Router (Federation 2.0) | NGINX |
| 최적화 | DataLoader (자동 배치) | 내부 오케스트레이션 (httpx) |
| 모니터링 | Prometheus + Grafana + cAdvisor |
| 부하 테스트 | Locust + Prometheus metrics |

---

## 🚀 빠른 시작

### 필수 요구사항

- Docker Desktop
- 최소 6GB RAM (권장: 8GB)
- Docker Compose v2.0+

### 실행

```bash
./scripts/quick-start.sh
```

**실행 내용:**
- REST API (FastAPI × 3 + NGINX)
- GraphQL API (Strawberry × 3 + Apollo Router)
- 모니터링 (Prometheus + Grafana + cAdvisor)

**총 11개 컨테이너** (약 6GB RAM 사용)

### 접속 주소

| Service | URL | 설명 |
|---------|-----|------|
| **GraphQL API** | http://localhost:14000 | Apollo Router (GraphiQL UI) |
| **REST API** | http://localhost:24000 | NGINX Gateway |
| **Grafana** | http://localhost:33000 | admin / admin |
| **Prometheus** | http://localhost:39090 | 메트릭 조회 |
| **REST Swagger** | http://localhost:28000/docs | User Service |
| | http://localhost:28001/docs | Robot Service |
| | http://localhost:28002/docs | Site Service |

---

## 📊 부하 테스트

### 실행

```bash
./scripts/start-loadtest.sh [OPTIONS] <api_type>
```

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `rest` / `graph` / `all` | 테스트 대상 | all |
| `-u, --users` | 동시 사용자 수 | 100 |
| `-r, --rate` | 초당 사용자 증가율 | 10 |
| `-t, --time` | 테스트 시간(초), headless 모드 | - |

### 예시

```bash
# Web UI 모드 (브라우저에서 시작/중지)
./scripts/start-loadtest.sh all -u 50 -r 5

# Headless 모드 (자동 실행)
./scripts/start-loadtest.sh all -u 100 -r 10 -t 300  # 5분간 100명
```

### Locust Web UI

| API | URL |
|-----|-----|
| GraphQL | http://localhost:48089 |
| REST | http://localhost:58089 |

### Grafana 대시보드

http://localhost:33000/d/container-metrics

**REST vs GraphQL 성능 비교:**
- RPS (Requests Per Second)
- Response Time (p50)
- Active Users
- CPU / Memory / Network 사용량

### 종료

```bash
./scripts/stop-loadtest.sh  # 부하 테스트만 종료
./scripts/stop-all.sh       # 모든 컨테이너 종료
```

---

## 🧪 테스트 시나리오

### 시나리오 및 호출 비율

| 시나리오 | 설명 | 비율 | GraphQL | REST |
|----------|------|------|---------|------|
| API-1 | 사용자 목록 조회 | 37.5% | 1 query | 1 call |
| API-2 | 사용자 + 로봇 조회 | 25% | 1 query | 1 call |
| API-3 | 전체 로봇 + Telemetry | 12.5% | 1 query | 1 call |
| API-4 | 사이트 대시보드 | 12.5% | 1 query | 1 call |
| Robot Detail | 로봇 + owner + site + telemetry | 12.5% | 1 query | 1 call |

**핵심:** 모든 시나리오에서 클라이언트는 1번만 호출. 서비스가 내부적으로 다른 서비스 호출 (마이크로서비스 오케스트레이션)

### API별 호출 흐름

**API-1: 사용자 목록**
```
REST:     Client → NGINX → user-service                         [1 call]
GraphQL:  Client → Apollo → user-service                        [1 query]
```

**API-2: 사용자 + 로봇**
```
REST:     Client → NGINX → user-service → robot-service         [1 call]
                                          (internal httpx call)

GraphQL:  Client → Apollo → user-service ─┐                     [1 query]
                          → robot-service ◄┘ (Federation)
```

**API-3: 로봇 + Telemetry**
```
REST:     Client → NGINX → robot-service                        [1 call]
                           (robots + telemetry combined)

GraphQL:  Client → Apollo → robot-service                       [1 query]
                            (DataLoader batched)
```

**API-4: 사이트 대시보드**
```
REST:     Client → NGINX → site-service ──┬→ robot-service      [1 call]
                                          ├→ user-service
                                          └→ telemetry
                                          (internal httpx calls)

GraphQL:  Client → Apollo → site-service ─┬→ robot-service      [1 query]
                                          ├→ user-service
                                          └→ telemetry
                                          (Federation + DataLoader)
```

**Robot Detail: 로봇 상세**
```
REST:     Client → NGINX → robot-service ─┬→ user-service       [1 call]
                                          └→ site-service
                                          (parallel internal calls)

GraphQL:  Client → Apollo → robot-service ─┬→ user-service      [1 query]
                                           ├→ site-service
                                           └→ telemetry
                                           (Federation)
```

---

## 📁 프로젝트 구조

```
graph-rest-preform/
├── backend/
│   ├── graphql/
│   │   ├── services/
│   │   │   ├── user-service/     # User Subgraph
│   │   │   ├── robot-service/    # Robot + Telemetry Subgraph
│   │   │   └── site-service/     # Site Subgraph
│   │   └── gateway/              # Apollo Router config
│   └── rest/
│       ├── services/
│       │   ├── user-service/
│       │   ├── robot-service/    # Robot + Telemetry
│       │   └── site-service/
│       └── gateway/              # NGINX config
├── monitoring/
│   ├── prometheus/               # Prometheus config
│   └── grafana/
│       ├── provisioning/         # Datasource 자동 설정
│       └── dashboards/           # 대시보드 JSON
├── load-test/
│   ├── locustfile_graphql.py     # GraphQL 테스트 시나리오
│   ├── locustfile_rest.py        # REST 테스트 시나리오
│   ├── prometheus_exporter.py    # Locust → Prometheus 메트릭
│   └── docker-compose.loadtest.yml
├── scripts/
│   ├── quick-start.sh            # 전체 스택 실행
│   ├── start-loadtest.sh         # 부하 테스트 실행
│   ├── stop-loadtest.sh          # 부하 테스트 종료
│   ├── stop-all.sh               # 전체 종료
│   └── README.md                 # 스크립트 상세 가이드
├── docker-compose.full.yml       # 통합 실행 파일
└── README.md
```

---

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Monitoring Stack                                │
│         Prometheus (39090) + Grafana (33000) + cAdvisor (38080)             │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┴───────────────────────────┐
        ▼                                                       ▼
┌───────────────────────────┐                   ┌───────────────────────────┐
│      GraphQL Stack        │                   │        REST Stack         │
│                           │                   │                           │
│   Apollo Router (14000)   │                   │   NGINX Gateway (24000)   │
│          │                │                   │          │                │
│    ┌─────┼─────┐          │                   │    ┌─────┼─────┐          │
│    ▼     ▼     ▼          │                   │    ▼     ▼     ▼          │
│  User  Robot  Site        │                   │  User  Robot  Site        │
│  8100  8101   8102        │                   │ 28000 28001  28002        │
│                           │                   │                           │
│  (Federation + DataLoader)│                   │  (Microservice + httpx)   │
└───────────────────────────┘                   └───────────────────────────┘
        ▲                                                       ▲
        │                                                       │
        └───────────────────────────┬───────────────────────────┘
                                    │
┌───────────────────────────────────┴─────────────────────────────────────────┐
│                              Load Test Stack                                 │
│              Locust GraphQL (48089) + Locust REST (58089)                   │
│                    Prometheus Metrics (49646, 59646)                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 수동 테스트

### GraphQL (http://localhost:14000)

```graphql
# API-1: 사용자 목록
query {
  users { id name email }
}

# API-2: 사용자 + 로봇
query {
  user(id: "1") {
    id name
    robots { id name status battery }
  }
}

# API-3: 로봇 + Telemetry
query {
  robots {
    id name status
    telemetry { cpu memory temperature }
  }
}

# API-4: 사이트 대시보드
query {
  site(id: "1") {
    id name location
    robots {
      id name status battery
      owner { name email }
      telemetry { cpu memory temperature }
    }
  }
}
```

### REST (http://localhost:24000)

```bash
# API-1: 사용자 목록
curl http://localhost:24000/api/users

# API-2: 사용자 + 로봇 (1번 호출, 서비스 내부 오케스트레이션)
curl http://localhost:24000/api/users/1/with-robots

# API-3: 로봇 + Telemetry (1번 호출, 내부 조합)
curl http://localhost:24000/api/robots/with-telemetry

# API-4: 사이트 대시보드 (1번 호출, 내부 조합)
curl http://localhost:24000/api/sites/1/dashboard

# Robot Detail (1번 호출, 서비스 내부 오케스트레이션)
curl http://localhost:24000/api/robots/1/full
```

---

## 🔍 트러블슈팅

### Docker 빌드 실패
```bash
docker-compose -f docker-compose.full.yml build --no-cache
```

### 포트 충돌
```bash
lsof -i :14000  # GraphQL
lsof -i :24000  # REST
```

### 컨테이너 상태 확인
```bash
docker-compose -f docker-compose.full.yml ps
docker-compose -f docker-compose.full.yml logs -f apollo-router
```

### 전체 초기화
```bash
./scripts/stop-all.sh
docker-compose -f docker-compose.full.yml down -v
./scripts/quick-start.sh
```

---

## 📄 라이센스

MIT License
