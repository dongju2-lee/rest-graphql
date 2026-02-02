# Scripts 사용법

## 🚀 실행

```bash
./scripts/quick-start.sh
```

**실행 내용:**
- REST API (FastAPI + NGINX)
- GraphQL API (Strawberry + Apollo Router)
- 모니터링 (Prometheus + Grafana + cAdvisor)

**총 11개 컨테이너** (약 6GB RAM 사용)

---

## 📊 부하 테스트

```bash
./scripts/start-loadtest.sh [OPTIONS] <api_type>
```

### API Type
| 옵션 | 설명 |
|------|------|
| `rest` | REST API만 테스트 |
| `graph` | GraphQL API만 테스트 |
| `all` | 둘 다 테스트 (기본값) |

### Options
| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `-u, --users` | 동시 사용자 수 | 100 |
| `-r, --rate` | 초당 사용자 증가율 | 10 |
| `-t, --time` | 테스트 시간(초), headless 모드 | - |

### 예시

```bash
# Web UI 모드 (-t 없이 실행)
./scripts/start-loadtest.sh rest              # REST만
./scripts/start-loadtest.sh graph -u 200      # GraphQL, 200명
./scripts/start-loadtest.sh all -u 50 -r 5    # 둘 다, 50명

# Headless 모드 (-t로 시간 지정, 자동 실행)
./scripts/start-loadtest.sh rest -t 60        # REST 60초
./scripts/start-loadtest.sh all -u 100 -t 300 # 100명, 5분
./scripts/start-loadtest.sh all -u 1 -r 1 -t 20   # 둘 다, 1명, 20초
```

### Locust Web UI (Web UI 모드에서만 사용 가능)
| API | URL |
|-----|-----|
| GraphQL | http://localhost:48089 |
| REST | http://localhost:58089 |

### Grafana 대시보드
- **REST vs GraphQL 성능 비교**: http://localhost:33000/d/container-metrics
  - Locust 메트릭 (RPS, Response Time, Active Users)
  - 컨테이너 메트릭 (CPU, Memory, Network)

### 테스트 시나리오 및 호출 비율

| 시나리오 | 설명 | 비율 | GraphQL | REST |
|----------|------|------|---------|------|
| API-1 | 사용자 목록 조회 | 37.5% | 1 query | 1 call |
| API-2 | 사용자 + 로봇 조회 | 25% | 1 query | 2 calls |
| API-3 | 전체 로봇 + Telemetry | 12.5% | 1 query | 2 calls |
| API-4 | 사이트 대시보드 | 12.5% | 1 query | 1 call |
| Robot Detail | 로봇 + owner + site + telemetry | 12.5% | 1 query | 3 calls |

**핵심:** 동일한 데이터를 가져오지만 REST는 더 많은 HTTP 호출 필요

### API 서비스 의존성

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              서비스 구조                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   [Client/Locust]                                                           │
│         │                                                                   │
│         ├──────────────────────┬────────────────────────────────────────    │
│         ▼                      ▼                                            │
│   ┌──────────────┐      ┌──────────────┐                                    │
│   │ NGINX Gateway│      │ Apollo Router│                                    │
│   │  (REST)      │      │  (GraphQL)   │                                    │
│   └──────┬───────┘      └──────┬───────┘                                    │
│          │                     │                                            │
│          ▼                     ▼                                            │
│   ┌────────────┐        ┌────────────┐                                      │
│   │user-service│        │user-service│                                      │
│   │robot-service│       │robot-service│  ◄── Federation으로 자동 연결        │
│   │site-service│        │site-service│                                      │
│   └────────────┘        └────────────┘                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### API별 호출 흐름

**API-1: 사용자 목록**
```
REST:     Client → NGINX → user-service                    [1 call]
GraphQL:  Client → Apollo → user-service                   [1 query]
```

**API-2: 사용자 + 로봇**
```
REST:     Client → NGINX → user-service                    [call 1]
                 → NGINX → robot-service                   [call 2]

GraphQL:  Client → Apollo → user-service ─┐                [1 query]
                          → robot-service ◄┘ (Federation)
```

**API-3: 로봇 + Telemetry**
```
REST:     Client → NGINX → robot-service (robots)          [call 1]
                 → NGINX → robot-service (telemetry batch) [call 2]

GraphQL:  Client → Apollo → robot-service ─┐               [1 query]
                            (DataLoader)  ◄┘ (batched)
```

**API-4: 사이트 대시보드**
```
REST:     Client → NGINX → site-service ──┬→ robot-service [internal]
                                          ├→ user-service  [internal]
                                          └→ telemetry     [internal]
                                                           [1 call]

GraphQL:  Client → Apollo → site-service ─┬→ robot-service [1 query]
                                          ├→ user-service  (Federation)
                                          └→ telemetry     (DataLoader)
```

**Robot Detail: 로봇 상세**
```
REST:     Client → NGINX → robot-service (robot+owner)     [call 1]
                 → NGINX → robot-service (telemetry)       [call 2]
                 → NGINX → site-service                    [call 3]

GraphQL:  Client → Apollo → robot-service ─┬→ user-service  [1 query]
                                           ├→ site-service  (Federation)
                                           └→ telemetry
```

#### REST vs GraphQL 차이점

| 구분 | REST | GraphQL |
|------|------|---------|
| 서비스 조합 | 클라이언트가 직접 여러 번 호출 | Apollo Router가 자동 조합 |
| N+1 문제 | batch endpoint로 해결 | DataLoader로 자동 해결 |
| Over-fetching | 모든 필드 반환 | 필요한 필드만 선택 |
| 네트워크 호출 | 시나리오당 1~3회 | 항상 1회 |

**종료:**
```bash
./scripts/stop-loadtest.sh
```

---

## 🛑 전체 종료

```bash
./scripts/stop-all.sh
```

모든 컨테이너를 정리합니다.

---

## 🌐 접속 주소

### GraphQL
- **Apollo Router (GraphiQL UI)**: http://localhost:14000
  - 브라우저에서 바로 쿼리 테스트 가능 (Swagger 같은 것)

### REST
- **NGINX Gateway**: http://localhost:24000
- **User Service Swagger**: http://localhost:28000/docs
- **Robot Service Swagger**: http://localhost:28001/docs
- **Site Service Swagger**: http://localhost:28002/docs

### 모니터링
- **Grafana**: http://localhost:33000 (admin/admin)
- **Prometheus**: http://localhost:39090

### 부하 테스트 (Web UI 모드)
- **Locust GraphQL**: http://localhost:48089
- **Locust REST**: http://localhost:58089

---

## 📊 수동 테스트 방법

### GraphQL 테스트 (http://localhost:14000)

브라우저에서 GraphiQL UI를 열고 쿼리를 실행하세요:

```graphql
# API-1: 사용자 목록 (Over-fetching 테스트)
query {
  users {
    id
    name
    email
  }
}

# API-2: 사용자 + 로봇 (Cross-service Join)
query {
  user(id: "1") {
    id
    name
    robots {
      id
      name
      status
      battery
    }
  }
}

# API-3: 로봇 + Telemetry (N+1 문제 테스트)
query {
  robots {
    id
    name
    telemetry {
      cpu
      memory
      temperature
    }
  }
}

# API-4: 사이트 대시보드 (복합 집계)
query {
  site(id: "1") {
    id
    name
    robots {
      id
      name
      owner { name }
      telemetry { cpu memory }
    }
  }
}
```

### REST 테스트

curl 사용:

```bash
# API-1: 사용자 목록
curl http://localhost:24000/api/users

# API-2: 사용자 + 로봇 (2번 호출 필요)
curl http://localhost:24000/api/users/1
curl http://localhost:24000/api/robots/by-owner/1

# API-3: 로봇 + Telemetry (배치 조회)
curl http://localhost:24000/api/robots
curl "http://localhost:24000/api/telemetry/batch?ids=1,2,3"

# API-4: 사이트 대시보드 (단일 엔드포인트)
curl http://localhost:24000/api/sites/1/dashboard
```

---

## 🔍 상태 확인

```bash
# 실행 중인 컨테이너 확인
docker-compose -f docker-compose.full.yml ps

# 로그 확인
docker-compose -f docker-compose.full.yml logs -f

# 특정 서비스 로그
docker-compose -f docker-compose.full.yml logs -f apollo-router
```

---

## 💡 Tip

- **처음 실행**: 이미지 빌드 때문에 2-3분 소요
- **두 번째부터**: 캐시 사용으로 30초 이내
- **종료 후 재시작**: `quick-start.sh` 다시 실행
- **문제 발생 시**: `stop-all.sh` 후 `quick-start.sh` 재실행
