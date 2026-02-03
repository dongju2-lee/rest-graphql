# Scripts 사용법

## 🚀 시스템 실행

```bash
./scripts/quick-start.sh
```

**실행 내용:**
- REST API (FastAPI + NGINX)
- GraphQL API (Strawberry + Apollo Router)
- 모니터링 (Prometheus + Grafana + cAdvisor)

**총 11개 컨테이너** (약 6GB RAM 사용)

---

## 📊 부하 테스트 선택

### 🎯 k6 (정확한 성능 비교) - **추천!**

#### 기본 실행
```bash
./scripts/start-k6.sh
```

#### 커스텀 설정
```bash
# 사용자 수와 요청 수 지정
./scripts/start-k6.sh -u 100 -i 20000

# 실행 시간도 지정
./scripts/start-k6.sh -u 200 -i 50000 -d 30m

# 도움말 보기
./scripts/start-k6.sh -h
```

#### 옵션 설명

| 옵션 | 의미 | 기본값 | 설명 |
|------|------|--------|------|
| `-u, --users N` | **가상 사용자** | 50 | 동시에 요청을 보내는 사용자 수 |
| `-i, --iterations N` | **총 요청 수** | 10,000 | GraphQL과 REST **정확히 같은 수**의 요청 |
| `-d, --duration TIME` | **최대 실행 시간** | 10m | 타임아웃 (10m = 10분, 30s = 30초) |

#### 사용 예시

```bash
# 초고속 테스트 (10초, 100번)
./scripts/start-k6.sh -u 10 -i 100 -d 10s

# 빠른 테스트 (5분, 1,000번)
./scripts/start-k6.sh -u 20 -i 1000 -d 5m

# 기본 테스트 (10분, 10,000번)
./scripts/start-k6.sh

# 강력한 부하 테스트 (30분, 100,000번)
./scripts/start-k6.sh -u 200 -i 100000 -d 30m
```

**시간 표현:**
- `10s` = 10초
- `1m` = 1분
- `5m` = 5분
- `1h` = 1시간

**특징:**
- ✅ **정확히 동일한 요청 수** - 공정한 비교!
- ✅ GraphQL vs REST **동시 실행**
- ✅ Prometheus + Grafana 네이티브 지원
- ✅ 명령줄로 간단하게 설정 (Locust 웹 UI처럼!)

**결과 확인:**
- Grafana: http://localhost:33000
  - Dashboard: "k6 Performance Comparison - GraphQL vs REST"
  - CPU, Memory, Network, RPS, 응답시간 등 **모든 메트릭**

**종료:**
```bash
./scripts/stop-k6.sh
```

**상세 문서:** [k6-test/README.md](../k6-test/README.md)

---

### 🌊 Locust (사용자 시뮬레이션)

아래 섹션 참조 →

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
| API-2 | 사용자 + 로봇 조회 | 25% | 1 query | 1 call |
| API-3 | 전체 로봇 + Telemetry | 12.5% | 1 query | 1 call |
| API-4 | 사이트 대시보드 | 12.5% | 1 query | 1 call |
| Robot Detail | 로봇 + owner + site + telemetry | 12.5% | 1 query | 1 call |

**핵심:** 모든 시나리오에서 클라이언트 → 서버 호출은 1회. 서비스가 내부적으로 다른 서비스 호출 (마이크로서비스 오케스트레이션)

### API 서비스 의존성

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        서비스 구조 (Microservice Style)                       │
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
│   │user-service│───┐    │user-service│                                      │
│   │robot-service│──┼──► │robot-service│  ◄── Federation으로 자동 연결        │
│   │site-service│───┘    │site-service│                                      │
│   └────────────┘        └────────────┘                                      │
│   (httpx로 서비스간 통신)  (Federation subgraph 통신)                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### API별 호출 흐름

**API-1: 사용자 목록**
```
REST:     Client → NGINX → user-service                              [1 call]
GraphQL:  Client → Apollo → user-service                             [1 query]
```

**API-2: 사용자 + 로봇**
```
REST:     Client → NGINX → user-service → robot-service (httpx)      [1 call]
GraphQL:  Client → Apollo → user-service ─┐                          [1 query]
                          → robot-service ◄┘ (Federation)
```

**API-3: 로봇 + Telemetry**
```
REST:     Client → NGINX → robot-service (robots + telemetry 조합)    [1 call]
GraphQL:  Client → Apollo → robot-service (DataLoader batched)       [1 query]
```

**API-4: 사이트 대시보드**
```
REST:     Client → NGINX → site-service ──┬→ robot-service           [1 call]
                                          ├→ user-service  (httpx)
                                          └→ telemetry

GraphQL:  Client → Apollo → site-service ─┬→ robot-service           [1 query]
                                          ├→ user-service  (Federation)
                                          └→ telemetry     (DataLoader)
```

**Robot Detail: 로봇 상세**
```
REST:     Client → NGINX → robot-service ─┬→ user-service            [1 call]
                                          ├→ site-service  (httpx, parallel)
                                          └→ telemetry     (local)

GraphQL:  Client → Apollo → robot-service ─┬→ user-service           [1 query]
                                           ├→ site-service  (Federation)
                                           └→ telemetry
```

#### REST vs GraphQL 차이점

| 구분 | REST (Microservice) | GraphQL (Federation) |
|------|---------------------|----------------------|
| 서비스 조합 | 서비스가 내부적으로 다른 서비스 호출 (httpx) | Apollo Router가 자동 조합 |
| N+1 문제 | 서비스 내부에서 배치 처리 | DataLoader로 자동 해결 |
| Over-fetching | 모든 필드 반환 | 필요한 필드만 선택 |
| 네트워크 호출 | 항상 1회 (내부 오케스트레이션) | 항상 1회 |

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

# API-2: 사용자 + 로봇 (서비스 내부 오케스트레이션)
curl http://localhost:24000/api/users/1/with-robots

# API-3: 로봇 + Telemetry (내부 조합)
curl http://localhost:24000/api/robots/with-telemetry

# API-4: 사이트 대시보드 (서비스 내부 오케스트레이션)
curl http://localhost:24000/api/sites/1/dashboard

# Robot Detail: 로봇 상세 (서비스 내부 오케스트레이션)
curl http://localhost:24000/api/robots/1/full
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
