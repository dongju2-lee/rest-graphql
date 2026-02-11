# REST vs GraphQL 성능 비교 프로젝트 - 아키텍처 설계서 v3

---

## 1. 프로젝트 목표

마이크로서비스 환경에서 3가지 API 아키텍처 패턴의 성능을 비교한다.
- 클라이언트 호출 수는 모든 케이스에서 **1번**으로 동일
- 내부 호출 패턴과 오케스트레이션 방식이 다름
- 동일 DB, 동일 시드 데이터로 공정한 비교

---

## 2. 3가지 케이스 정의

### Case 1: REST 마이크로서비스 (서비스 간 직접 호출)

```
Client --(1 HTTP)--> REST Gateway (:10000, 단순 프록시)
                         |
                         --> Robot Service (:10001, 오케스트레이터)
                                |
                                --> Telemetry Service (:10002) ← N+1 발생
                                --> Alert Service (:10003)     ← N+1 발생
```

- Gateway는 단순 프록시 (라우팅만)
- **Robot Service가 다른 서비스를 직접 HTTP 호출** (실제 마이크로서비스 패턴)
- istio 등 서비스 메시 환경과 동일한 구조
- N+1 문제가 서비스 내부에서 자연스럽게 발생

### Case 2: Strawberry GraphQL (단일 GraphQL 서버)

```
Client --(1 GraphQL)--> Strawberry Gateway (:10000)
                             |
                             --> Robot Service (:10001)      ← 데이터만
                             --> Telemetry Service (:10002)  ← 데이터만
                             --> Alert Service (:10003)      ← 데이터만
```

- Strawberry가 단일 GraphQL 서버로 모든 오케스트레이션 담당
- **DataLoader가 N+1을 자동 배치 처리**
- 마이크로서비스는 순수 데이터 제공만

### Case 3: Apollo Router + Federation (분산 GraphQL)

```
Client --(1 GraphQL)--> Apollo Router (:10000)
                             |
                             --> Robot Subgraph (:10011)
                             |       --> Robot Service (:10001)
                             |
                             --> Telemetry Subgraph (:10012)
                             |       --> Telemetry Service (:10002)
                             |
                             --> Alert Subgraph (:10013)
                                     --> Alert Service (:10003)
```

- Apollo Router(Rust)가 쿼리를 분석, Subgraph에 분배
- 각 Subgraph는 Strawberry + Federation으로 구현 (Python 통일)
- 마이크로서비스는 순수 데이터 제공만
- Router↔Subgraph 간 GraphQL 통신 오버헤드 측정이 핵심

---

## 3. 공유/비공유 정리

### 공유하는 것

| 항목 | 설명 |
|------|------|
| PostgreSQL | 1개 인스턴스, 동일 스키마 |
| 데이터 모델 | SQLAlchemy 모델 (robots, telemetry_data, alerts) |
| 시드 데이터 | 로봇 15대, 텔레메트리, 알람 |
| Pydantic 스키마 | Request/Response 타입 |
| 클라이언트 API 인터페이스 | 3개 API의 최종 응답 데이터 동일 |

### 케이스별로 다른 것

| 항목 | Case 1 (REST) | Case 2 (Strawberry) | Case 3 (Apollo) |
|------|:---:|:---:|:---:|
| Gateway | REST Gateway (프록시) | Strawberry GraphQL 서버 | Apollo Router |
| 마이크로서비스 | 오케스트레이션 포함 | 순수 데이터만 | 순수 데이터만 |
| 추가 컴포넌트 | 없음 | 없음 | Subgraph 3개 |
| 서비스 간 직접 호출 | Robot → Telemetry, Alert | 없음 | 없음 |

**핵심**: Case 1의 마이크로서비스에는 다른 서비스를 호출하는 오케스트레이션 로직이 포함되며, batch 엔드포인트(POST /telemetry/batch, POST /alerts/batch)를 사용하여 N+1 없이 호출한다. GraphQL의 DataLoader와 동일한 호출 수를 달성하지만, batch 설계와 구현을 개발자가 명시적으로 해야 한다는 차이가 있다. (상세 비교: Section 10.5)

---

## 4. 포트 배정

각 케이스를 독립 실행하므로 Gateway 진입점은 항상 10000.

```
공용 (모든 케이스):
  PostgreSQL           : 15432

마이크로서비스 (케이스별 별도 빌드, 같은 포트):
  Robot Service        : 10001
  Telemetry Service    : 10002
  Alert Service        : 10003

Gateway 진입점 (항상 10000):
  Case 1: REST Gateway       : 10000
  Case 2: Strawberry Gateway  : 10000
  Case 3: Apollo Router       : 10000

Case 3 전용 (Subgraph):
  Robot Subgraph       : 10011
  Telemetry Subgraph   : 10012
  Alert Subgraph       : 10013
```

---

## 5. 마이크로서비스 API 설계 (최대한 간결하게)

### 5.1 데이터 모델

```sql
CREATE TABLE robots (
    id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    model VARCHAR(50) NOT NULL,
    location VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
);

CREATE TABLE telemetry_data (
    id SERIAL PRIMARY KEY,
    robot_id VARCHAR(20) NOT NULL REFERENCES robots(id),
    battery_level FLOAT NOT NULL,
    cpu_usage FLOAT NOT NULL,
    temperature FLOAT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_telemetry_robot_ts ON telemetry_data(robot_id, timestamp DESC);

CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    robot_id VARCHAR(20) NOT NULL REFERENCES robots(id),
    severity VARCHAR(20) NOT NULL,
    message VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_alerts_robot ON alerts(robot_id);
CREATE INDEX idx_alerts_severity ON alerts(severity);
```

### 5.2 Robot Service (:10001)

```
GET /robots
  → [{ id, name, model, location, status }]

GET /robots/{id}
  → { id, name, model, location, status }

GET /health
  → { status: "ok" }
```

### 5.3 Telemetry Service (:10002)

```
GET /telemetry/{robot_id}/latest
  → { robot_id, battery_level, cpu_usage, temperature, timestamp }

POST /telemetry/batch
  Body: { "robot_ids": ["robot-001", "robot-002"] }
  → { "robot-001": { battery_level, ... }, "robot-002": { ... } }

GET /health
  → { status: "ok" }
```

### 5.4 Alert Service (:10003)

```
GET /alerts/{robot_id}
  → [{ id, robot_id, severity, message, created_at }]

GET /alerts/critical
  → [{ id, robot_id, severity, message, created_at }]

POST /alerts/batch
  Body: { "robot_ids": ["robot-001", "robot-002"] }
  → { "robot-001": [{ id, severity, ... }], "robot-002": [...] }

GET /health
  → { status: "ok" }
```

---

## 6. 클라이언트 API 3개 (최종 응답 데이터 동일)

### API 1: Fleet Dashboard

N+1 문제 극대화 (15대 로봇)

```
요청:
  REST:    GET /api/fleet/dashboard
  GraphQL: query { fleetDashboard { robots { id name latestTelemetry { batteryLevel } activeAlerts { severity message } } } }

응답 (동일):
  {
    "robots": [
      {
        "id": "robot-001",
        "name": "AGV-Alpha",
        "latestTelemetry": { "batteryLevel": 85.5, "cpuUsage": 42.1, "temperature": 38.0 },
        "activeAlerts": [{ "severity": "warning", "message": "Battery below 30%" }]
      },
      ...
    ]
  }
```

**내부 호출:**

| | Case 1 (REST) | Case 2 (Strawberry) | Case 3 (Apollo) |
|---|:---:|:---:|:---:|
| Robot Service | 1번 (DB 조회) | 1번 (GET /robots) | Subgraph→1번 |
| Telemetry Service | **1번** (POST /telemetry/batch) | **1번** (DataLoader batch) | Subgraph→**1번** (DataLoader batch) |
| Alert Service | **1번** (POST /alerts/batch) | **1번** (DataLoader batch) | Subgraph→**1번** (DataLoader batch) |
| 총 서비스 호출 | **3번** | **3번** | **3번** + Subgraph 3번 |
| Batch 방식 | 명시적 batch 엔드포인트 | DataLoader 자동 | DataLoader 자동 |

> 3개 케이스 모두 서비스 호출 3번으로 동일. 차이는 batch 구현 방식 (명시적 vs 자동).
> 상세 흐름은 Section 10.1 참고.

### API 2: Robot Monitor

1:1 관계 (N+1 없음, 차이 없어야 함)

```
요청:
  REST:    GET /api/robots/{id}/monitor
  GraphQL: query { robotMonitor(id: "robot-001") { ... } }

응답 (동일):
  {
    "robot": { "id": "robot-001", "name": "AGV-Alpha", ... },
    "telemetry": { "batteryLevel": 85.5, ... },
    "recentAlerts": [{ "severity": "warning", ... }]
  }
```

**내부 호출:**

| | Case 1 REST | Case 2 (Strawberry) | Case 3 (Apollo) |
|---|:---:|:---:|:---:|
| Robot Service | 1번 (DB 조회) | 1번 | Subgraph→1번 |
| Telemetry Service | 1번 (GET /telemetry/{id}/latest) | 1번 | Subgraph→1번 |
| Alert Service | 1번 (GET /alerts/{id}) | 1번 | Subgraph→1번 |
| 총 서비스 호출 | **3번** | **3번** | **3번** + Subgraph 3번 |

> 1:1 관계이므로 N+1이 발생하지 않아 모든 케이스에서 호출 수 동일. batch 여부와 무관.

### API 3: Critical Alerts

N+1 발생 (크리티컬 알람 10건 → 각각 로봇 정보 필요)

```
요청:
  REST:    GET /api/alerts/critical
  GraphQL: query { criticalAlerts { id message robot { name } telemetrySnapshot { batteryLevel } } }

응답 (동일):
  {
    "alerts": [
      {
        "id": 1,
        "message": "Temperature critical",
        "robot": { "id": "robot-003", "name": "AGV-Gamma" },
        "telemetrySnapshot": { "batteryLevel": 15.2, ... }
      },
      ...
    ]
  }
```

**내부 호출:**

| | Case 1 (REST) | Case 2 (Strawberry) | Case 3 (Apollo) |
|---|:---:|:---:|:---:|
| Alert Service | 1번 (DB 조회) | 1번 (GET /alerts/critical) | Subgraph→1번 |
| Robot Service | **1번** (DB IN 쿼리) | **N번** (개별 GET) | Subgraph→**N번** (개별 GET) |
| Telemetry Service | **1번** (POST /telemetry/batch) | **1번** (DataLoader batch) | Subgraph→**1번** (DataLoader batch) |
| 총 서비스 호출 | **3번** | **2+N번** | **2+N번** + Subgraph 3번 |

> N = 유니크 로봇 수. Case 1은 Robot이 자체 DB라 IN 쿼리로 1번에 해결.
> Case 2, 3은 Robot batch 엔드포인트가 없어서 개별 GET N번.
> 상세 흐름은 Section 10.3 참고.

---

## 7. 디렉토리 구조

```
graph-rest-preform/
├── .env.example
├── .gitignore
├── README.md
├── docker-compose.base.yml              # 공용: PostgreSQL
├── docker-compose.case1.yml             # Case 1: REST Gateway + REST 마이크로서비스
├── docker-compose.case2.yml             # Case 2: Strawberry + 데이터 마이크로서비스
├── docker-compose.case3.yml             # Case 3: Apollo Router + Subgraph + 데이터 마이크로서비스
│
├── shared/                              # 공용 코드
│   ├── __init__.py
│   ├── config.py                        # DB URL 등 공통 설정
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py                    # SQLAlchemy 모델 (Robot, TelemetryData, Alert)
│   │   ├── database.py                  # async 엔진, 세션 팩토리
│   │   └── seed.py                      # 시드 데이터 (로봇 15대 + 텔레메트리 + 알람)
│   └── schemas/
│       ├── __init__.py
│       ├── robot.py                     # RobotResponse
│       ├── telemetry.py                 # TelemetryResponse, TelemetryBatchRequest
│       └── alert.py                     # AlertResponse, AlertBatchRequest
│
├── services/                            # 마이크로서비스
│   │
│   ├── data/                            # Case 2, 3용 (순수 데이터 제공만)
│   │   ├── robot-service/
│   │   │   ├── Dockerfile
│   │   │   ├── requirements.txt
│   │   │   └── app/
│   │   │       ├── __init__.py
│   │   │       ├── main.py              # FastAPI, GET /robots, GET /robots/{id}
│   │   │       └── service.py           # DB 조회 로직
│   │   ├── telemetry-service/
│   │   │   ├── Dockerfile
│   │   │   ├── requirements.txt
│   │   │   └── app/
│   │   │       ├── __init__.py
│   │   │       ├── main.py              # GET /telemetry/{id}/latest, POST /telemetry/batch
│   │   │       └── service.py
│   │   └── alert-service/
│   │       ├── Dockerfile
│   │       ├── requirements.txt
│   │       └── app/
│   │           ├── __init__.py
│   │           ├── main.py              # GET /alerts/{id}, GET /alerts/critical, POST /alerts/batch
│   │           └── service.py
│   │
│   └── orchestrated/                    # Case 1용 (서비스 간 직접 호출 포함)
│       ├── robot-service/
│       │   ├── Dockerfile
│       │   ├── requirements.txt         # + httpx
│       │   └── app/
│       │       ├── __init__.py
│       │       ├── main.py              # 기본 API + 집계 API
│       │       ├── service.py           # DB 조회 (data/ 와 동일)
│       │       └── orchestrator.py      # 다른 서비스 호출 + 조합 (N+1 발생)
│       ├── telemetry-service/           # data/ 와 동일
│       │   ├── Dockerfile
│       │   ├── requirements.txt
│       │   └── app/
│       │       ├── __init__.py
│       │       ├── main.py
│       │       └── service.py
│       └── alert-service/               # data/ 와 동일
│           ├── Dockerfile
│           ├── requirements.txt
│           └── app/
│               ├── __init__.py
│               ├── main.py
│               └── service.py
│
├── gateways/
│   ├── rest/                            # Case 1: REST Gateway (단순 프록시)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app/
│   │       ├── __init__.py
│   │       ├── main.py                  # FastAPI, 프록시 라우트
│   │       └── config.py                # 서비스 URL
│   │
│   ├── strawberry/                      # Case 2: Strawberry GraphQL
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app/
│   │       ├── __init__.py
│   │       ├── main.py                  # FastAPI + Strawberry GraphQLRouter
│   │       ├── schema.py                # Query 타입, GraphQL 타입 정의
│   │       ├── dataloaders.py           # DataLoader (telemetry, alert, robot 배치)
│   │       └── config.py
│   │
│   └── apollo-federation/               # Case 3: Apollo Router + Subgraphs
│       ├── router/
│       │   ├── router.yaml              # Apollo Router 설정
│       │   ├── supergraph-config.yaml   # Subgraph URL 정의
│       │   └── supergraph.graphql       # 통합 스키마 (rover compose로 생성)
│       ├── robot-subgraph/
│       │   ├── Dockerfile
│       │   ├── requirements.txt
│       │   └── app/
│       │       ├── __init__.py
│       │       ├── main.py              # FastAPI + Strawberry Federation
│       │       ├── schema.py            # Robot @key, _entities 리졸버
│       │       └── config.py
│       ├── telemetry-subgraph/
│       │   ├── Dockerfile
│       │   ├── requirements.txt
│       │   └── app/
│       │       ├── __init__.py
│       │       ├── main.py
│       │       ├── schema.py            # extend Robot, latestTelemetry 필드
│       │       └── config.py
│       └── alert-subgraph/
│           ├── Dockerfile
│           ├── requirements.txt
│           └── app/
│               ├── __init__.py
│               ├── main.py
│               ├── schema.py            # extend Robot, activeAlerts, criticalAlerts
│               └── config.py
│
├── scripts/
│   ├── infra-up.sh                      # 인프라 기동 (DB + Prometheus + Grafana)
│   ├── infra-down.sh                    # 인프라 종료 (볼륨 유지)
│   ├── case1-rest.sh                    # Case 1 서비스 기동
│   ├── case2-strawberry.sh              # Case 2 서비스 기동
│   ├── case3-apollo.sh                  # Case 3 서비스 기동
│   ├── case-stop.sh                     # 현재 Case만 종료 (인프라 유지)
│   ├── k6-duration.sh                   # Mode 1: 부하 유지 테스트
│   ├── k6-iterations.sh                 # Mode 2: 고정 콜수 테스트
│   ├── seed.sh                          # DB 시드 데이터 삽입
│   └── cleanup.sh                       # 완전 삭제 (컨테이너+볼륨+이미지+네트워크)
│
├── k6/
│   ├── common.js                        # 공통 설정 (VU, duration, thresholds)
│   ├── case1-rest.js                    # REST 부하 테스트
│   ├── case2-strawberry.js              # Strawberry 부하 테스트
│   ├── case3-apollo.js                  # Apollo Federation 부하 테스트
│   └── results/
│       └── .gitkeep
│
└── docs/
    ├── concept.md                       # 설계 논의 기록
    └── architecture.md                  # 이 문서
```

---

## 8. Docker Compose 구성

### docker-compose.base.yml (PostgreSQL만)

```yaml
services:
  postgres:
    image: postgres:16-alpine
    ports:
      - "15432:5432"
    environment:
      POSTGRES_DB: robot_fleet
      POSTGRES_USER: fleet
      POSTGRES_PASSWORD: fleet123
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U fleet"]
      interval: 5s
      retries: 5
    networks:
      - fleet-net

volumes:
  pgdata:

networks:
  fleet-net:
    name: fleet-net
```

### docker-compose.case1.yml (REST)

```yaml
services:
  robot-service:
    build:
      context: .
      dockerfile: services/orchestrated/robot-service/Dockerfile
    ports: ["10001:10001"]
    environment:
      DATABASE_URL: postgresql+asyncpg://fleet:fleet123@postgres:5432/robot_fleet
      TELEMETRY_SERVICE_URL: http://telemetry-service:10002
      ALERT_SERVICE_URL: http://alert-service:10003
    depends_on:
      postgres: { condition: service_healthy }
    networks: [fleet-net]

  telemetry-service:
    build:
      context: .
      dockerfile: services/orchestrated/telemetry-service/Dockerfile
    ports: ["10002:10002"]
    environment:
      DATABASE_URL: postgresql+asyncpg://fleet:fleet123@postgres:5432/robot_fleet
    depends_on:
      postgres: { condition: service_healthy }
    networks: [fleet-net]

  alert-service:
    build:
      context: .
      dockerfile: services/orchestrated/alert-service/Dockerfile
    ports: ["10003:10003"]
    environment:
      DATABASE_URL: postgresql+asyncpg://fleet:fleet123@postgres:5432/robot_fleet
    depends_on:
      postgres: { condition: service_healthy }
    networks: [fleet-net]

  rest-gateway:
    build:
      context: .
      dockerfile: gateways/rest/Dockerfile
    ports: ["10000:10000"]
    environment:
      ROBOT_SERVICE_URL: http://robot-service:10001
    networks: [fleet-net]

networks:
  fleet-net:
    external: true
```

### docker-compose.case2.yml (Strawberry)

```yaml
services:
  robot-service:
    build:
      context: .
      dockerfile: services/data/robot-service/Dockerfile
    ports: ["10001:10001"]
    environment:
      DATABASE_URL: postgresql+asyncpg://fleet:fleet123@postgres:5432/robot_fleet
    depends_on:
      postgres: { condition: service_healthy }
    networks: [fleet-net]

  telemetry-service:
    build:
      context: .
      dockerfile: services/data/telemetry-service/Dockerfile
    ports: ["10002:10002"]
    environment:
      DATABASE_URL: postgresql+asyncpg://fleet:fleet123@postgres:5432/robot_fleet
    depends_on:
      postgres: { condition: service_healthy }
    networks: [fleet-net]

  alert-service:
    build:
      context: .
      dockerfile: services/data/alert-service/Dockerfile
    ports: ["10003:10003"]
    environment:
      DATABASE_URL: postgresql+asyncpg://fleet:fleet123@postgres:5432/robot_fleet
    depends_on:
      postgres: { condition: service_healthy }
    networks: [fleet-net]

  strawberry-gateway:
    build:
      context: .
      dockerfile: gateways/strawberry/Dockerfile
    ports: ["10000:10000"]
    environment:
      ROBOT_SERVICE_URL: http://robot-service:10001
      TELEMETRY_SERVICE_URL: http://telemetry-service:10002
      ALERT_SERVICE_URL: http://alert-service:10003
    networks: [fleet-net]

networks:
  fleet-net:
    external: true
```

### docker-compose.case3.yml (Apollo Federation)

```yaml
services:
  robot-service:
    build:
      context: .
      dockerfile: services/data/robot-service/Dockerfile
    ports: ["10001:10001"]
    environment:
      DATABASE_URL: postgresql+asyncpg://fleet:fleet123@postgres:5432/robot_fleet
    depends_on:
      postgres: { condition: service_healthy }
    networks: [fleet-net]

  telemetry-service:
    build:
      context: .
      dockerfile: services/data/telemetry-service/Dockerfile
    ports: ["10002:10002"]
    environment:
      DATABASE_URL: postgresql+asyncpg://fleet:fleet123@postgres:5432/robot_fleet
    depends_on:
      postgres: { condition: service_healthy }
    networks: [fleet-net]

  alert-service:
    build:
      context: .
      dockerfile: services/data/alert-service/Dockerfile
    ports: ["10003:10003"]
    environment:
      DATABASE_URL: postgresql+asyncpg://fleet:fleet123@postgres:5432/robot_fleet
    depends_on:
      postgres: { condition: service_healthy }
    networks: [fleet-net]

  robot-subgraph:
    build:
      context: .
      dockerfile: gateways/apollo-federation/robot-subgraph/Dockerfile
    ports: ["10011:10011"]
    environment:
      ROBOT_SERVICE_URL: http://robot-service:10001
    networks: [fleet-net]

  telemetry-subgraph:
    build:
      context: .
      dockerfile: gateways/apollo-federation/telemetry-subgraph/Dockerfile
    ports: ["10012:10012"]
    environment:
      TELEMETRY_SERVICE_URL: http://telemetry-service:10002
    networks: [fleet-net]

  alert-subgraph:
    build:
      context: .
      dockerfile: gateways/apollo-federation/alert-subgraph/Dockerfile
    ports: ["10013:10013"]
    environment:
      ALERT_SERVICE_URL: http://alert-service:10003
    networks: [fleet-net]

  apollo-router:
    image: ghcr.io/apollographql/router:v1.57.1
    ports: ["10000:10000"]
    volumes:
      - ./gateways/apollo-federation/router/router.yaml:/dist/config/router.yaml
      - ./gateways/apollo-federation/router/supergraph.graphql:/dist/config/supergraph.graphql
    command: ["--config", "/dist/config/router.yaml", "--supergraph", "/dist/config/supergraph.graphql", "--listen", "0.0.0.0:10000"]
    depends_on: [robot-subgraph, telemetry-subgraph, alert-subgraph]
    networks: [fleet-net]

networks:
  fleet-net:
    external: true
```

---

## 9. 스크립트 목록

```
scripts/
├── infra-up.sh              # 인프라 기동 (PostgreSQL + Prometheus + Grafana)
├── infra-down.sh            # 인프라 종료 + 볼륨 삭제
├── case1-rest.sh            # Case 1 서비스 기동
├── case2-strawberry.sh      # Case 2 서비스 기동
├── case3-apollo.sh          # Case 3 서비스 기동
├── case-stop.sh             # 현재 Case 서비스만 종료 (인프라 유지)
├── k6-duration.sh           # Mode 1: 부하 유지 테스트
├── k6-iterations.sh         # Mode 2: 고정 콜수 테스트
├── seed.sh                  # DB 시드 데이터 삽입
└── cleanup.sh               # 전체 삭제 (컨테이너 + 볼륨 + 네트워크 + 이미지)
```

---

## 9.1 사용법

### 처음 시작

```bash
# 1. 인프라 기동 (PostgreSQL, Prometheus, Grafana)
./scripts/infra-up.sh

# 확인
# Grafana:    http://localhost:13000 (admin/admin)
# Prometheus: http://localhost:19090
```

### Case 1 (REST) 테스트

```bash
# 2. Case 1 서비스 기동
./scripts/case1-rest.sh

# 3-A. 부하 유지 테스트 (50유저, 5분)
./scripts/k6-duration.sh --case 1 --vus 50 --duration 5m

# 3-B. 고정 콜수 테스트 (50유저, 1000콜)
./scripts/k6-iterations.sh --case 1 --vus 50 --iterations 1000

# 4. Case 1 종료 (인프라는 유지)
./scripts/case-stop.sh
```

### Case 2 (Strawberry) 테스트

```bash
# 5. Case 2 서비스 기동
./scripts/case2-strawberry.sh

# 6. 테스트
./scripts/k6-duration.sh --case 2 --vus 50 --duration 5m
./scripts/k6-iterations.sh --case 2 --vus 50 --iterations 1000

# 7. Case 2 종료
./scripts/case-stop.sh
```

### Case 3 (Apollo Federation) 테스트

```bash
# 8. Case 3 서비스 기동
./scripts/case3-apollo.sh

# 9. 테스트
./scripts/k6-duration.sh --case 3 --vus 50 --duration 5m
./scripts/k6-iterations.sh --case 3 --vus 50 --iterations 1000

# 10. Case 3 종료
./scripts/case-stop.sh
```

### 결과 확인

```bash
# Grafana에서 3개 케이스 결과 비교 (Prometheus에 메트릭 다 쌓여있음)
open http://localhost:13000
```

### 종료 및 삭제

```bash
# 인프라 종료 (컨테이너 중지, 볼륨 유지)
./scripts/infra-down.sh

# 완전 삭제 (컨테이너 + 볼륨 + 네트워크 + 빌드 이미지 전부 삭제)
./scripts/cleanup.sh
```

### 한번에 3개 케이스 연속 테스트

```bash
# 인프라 기동
./scripts/infra-up.sh

# Case 1
./scripts/case1-rest.sh
./scripts/k6-duration.sh --case 1 --vus 50 --duration 5m
./scripts/case-stop.sh

# Case 2
./scripts/case2-strawberry.sh
./scripts/k6-duration.sh --case 2 --vus 50 --duration 5m
./scripts/case-stop.sh

# Case 3
./scripts/case3-apollo.sh
./scripts/k6-duration.sh --case 3 --vus 50 --duration 5m
./scripts/case-stop.sh

# Grafana에서 비교
open http://localhost:13000
```

### 스크립트 내부 동작

```
infra-up.sh:
  docker compose -f docker-compose.base.yml up -d
  → PostgreSQL, Prometheus, Grafana 기동
  → fleet-net 네트워크 생성
  → DB 헬스체크 대기
  → 시드 데이터 삽입

case1-rest.sh:
  docker compose -f docker-compose.case1.yml up -d --build
  → REST Gateway + orchestrated 마이크로서비스 기동
  → 헬스체크 대기
  → "Ready! http://localhost:10000"

case-stop.sh:
  docker compose -f docker-compose.case1.yml down 2>/dev/null
  docker compose -f docker-compose.case2.yml down 2>/dev/null
  docker compose -f docker-compose.case3.yml down 2>/dev/null
  → 현재 떠있는 case 서비스만 종료
  → base(인프라)는 건드리지 않음

infra-down.sh:
  docker compose -f docker-compose.case1.yml down 2>/dev/null
  docker compose -f docker-compose.case2.yml down 2>/dev/null
  docker compose -f docker-compose.case3.yml down 2>/dev/null
  docker compose -f docker-compose.base.yml down
  → 전체 종료 (볼륨은 유지, 다음에 다시 올리면 데이터 살아있음)

cleanup.sh:
  docker compose -f docker-compose.case1.yml down -v --rmi local 2>/dev/null
  docker compose -f docker-compose.case2.yml down -v --rmi local 2>/dev/null
  docker compose -f docker-compose.case3.yml down -v --rmi local 2>/dev/null
  docker compose -f docker-compose.base.yml down -v --rmi local
  docker network rm fleet-net 2>/dev/null
  → 컨테이너 삭제
  → 볼륨 삭제 (DB 데이터, Prometheus 데이터 포함)
  → 빌드한 이미지 삭제
  → 네트워크 삭제
  → 완전 초기화
```

---

## 10. 3개 케이스 내부 호출 흐름 상세

각 API에 대해 Case 1, 2, 3의 **실제 내부 호출 흐름**을 비교한다.

---

### 10.1 API 1: Fleet Dashboard (15대 로봇)

#### Case 1: REST (현재 구현 — batch 사용)

```
Client → REST Gateway → Robot Service (오케스트레이터)

Robot Service 내부 (orchestrator.py):
  1. DB에서 로봇 15대 조회                                           (DB 1번)
  2. robot_ids = [r.id for r in robots]
  3. POST http://telemetry-service:10002/telemetry/batch             (HTTP 1번)
       Body: { "robot_ids": robot_ids }
  4. POST http://alert-service:10003/alerts/batch                    (HTTP 1번)
       Body: { "robot_ids": robot_ids }
  5. 결과 조합하여 반환
  → 총: DB 1번 + HTTP 2번 = 3번
```

#### Case 2: Strawberry GraphQL

```
Client → Strawberry Gateway (오케스트레이터)

Strawberry 내부:
  1. Query.fleet_dashboard 리졸버 실행
     → GET http://robot-service:10001/robots                         (HTTP 1번)
  2. 15개 RobotType 생성 → 각각 latest_telemetry, active_alerts 필드 리졸브
  3. DataLoader가 15개 robot_id를 자동 수집 (같은 이벤트 루프 틱)
     → telemetry_loader: POST http://telemetry-service:10002/telemetry/batch  (HTTP 1번)
     → alert_loader:     POST http://alert-service:10003/alerts/batch         (HTTP 1번)
  4. DataLoader가 결과를 각 RobotType에 분배
  → 총: HTTP 3번 (DataLoader가 자동 batch)
```

#### Case 3: Apollo Federation

```
Client → Apollo Router → 쿼리 플랜 생성 → Subgraph 분배

Step 1: Router → Robot Subgraph (GraphQL)
  Robot Subgraph 내부:
    → GET http://robot-service:10001/robots                          (HTTP 1번)
    → 15개 Robot 엔티티 반환

Step 2: Router → Telemetry Subgraph (GraphQL, _entities 쿼리)
  Telemetry Subgraph 내부:
    → 15개 robot_id로 resolve_reference 호출
    → DataLoader가 수집: POST http://telemetry-service:10002/telemetry/batch  (HTTP 1번)
    → 각 Robot에 latest_telemetry 필드 추가

Step 3: Router → Alert Subgraph (GraphQL, _entities 쿼리)
  Alert Subgraph 내부:
    → 15개 robot_id로 resolve_reference 호출
    → DataLoader가 수집: POST http://alert-service:10003/alerts/batch         (HTTP 1번)
    → 각 Robot에 active_alerts 필드 추가

  → 총: Subgraph 3번 (GraphQL) + 서비스 3번 (HTTP) = 네트워크 홉 6번
```

#### Fleet Dashboard 호출 수 비교

| | REST (현재 구현) | Strawberry | Apollo Federation |
|---|:---:|:---:|:---:|
| Gateway → 서비스 | 3번 (HTTP, batch) | 3번 (HTTP, DataLoader) | — |
| Router → Subgraph | — | — | 3번 (GraphQL) |
| Subgraph → 서비스 | — | — | 3번 (HTTP) |
| **총 네트워크 홉** | **3번** | **3번** | **6번** |

---

### 10.2 API 2: Robot Monitor (1대 로봇)

#### Case 1: REST

```
Client → REST Gateway → Robot Service (오케스트레이터)

Robot Service 내부:
  1. DB에서 로봇 1대 조회                                            (DB 1번)
  2. GET http://telemetry-service:10002/telemetry/{id}/latest        (HTTP 1번)
  3. GET http://alert-service:10003/alerts/{id}                      (HTTP 1번)
  4. 결과 조합하여 반환
  → 총: DB 1번 + HTTP 2번 = 3번
```

#### Case 2: Strawberry GraphQL

```
Client → Strawberry Gateway

Strawberry 내부:
  1. Query.robot_monitor 리졸버 실행 (직접 호출, DataLoader 미사용)
     → GET http://robot-service:10001/robots/{id}                    (HTTP 1번)
     → GET http://telemetry-service:10002/telemetry/{id}/latest      (HTTP 1번)
     → GET http://alert-service:10003/alerts/{id}                    (HTTP 1번)
  → 총: HTTP 3번 (1:1이라 DataLoader 불필요)
```

#### Case 3: Apollo Federation

```
Client → Apollo Router → Subgraph 분배

Step 1: Router → Robot Subgraph (GraphQL)
  → GET http://robot-service:10001/robots/{id}                       (HTTP 1번)

Step 2: Router → Telemetry Subgraph (GraphQL, _entities)
  → DataLoader: POST http://telemetry-service:10002/telemetry/batch  (HTTP 1번, 1개 항목)

Step 3: Router → Alert Subgraph (GraphQL, _entities)
  → DataLoader: POST http://alert-service:10003/alerts/batch         (HTTP 1번, 1개 항목)

  → 총: Subgraph 3번 (GraphQL) + 서비스 3번 (HTTP) = 네트워크 홉 6번
```

#### Robot Monitor 호출 수 비교

| | REST | Strawberry | Apollo Federation |
|---|:---:|:---:|:---:|
| Gateway → 서비스 | 3번 (HTTP) | 3번 (HTTP) | — |
| Router → Subgraph | — | — | 3번 (GraphQL) |
| Subgraph → 서비스 | — | — | 3번 (HTTP) |
| **총 네트워크 홉** | **3번** | **3번** | **6번** |

> 1:1 관계이므로 N+1 없음. 모든 케이스에서 서비스 호출은 3번이지만,
> Apollo는 Router↔Subgraph 간 GraphQL 통신 3번이 추가되어 **오버헤드가 가장 큼**.
> 이 API에서 Apollo가 가장 느리다면 Subgraph 오버헤드 때문이다.

---

### 10.3 API 3: Critical Alerts (크리티컬 알람 10건)

#### Case 1: REST (현재 구현 — batch 사용)

```
Client → REST Gateway → Robot Service (오케스트레이터)

Robot Service 내부 (orchestrator.py):
  1. DB에서 critical 알람 조회                                        (DB 1번)
  2. robot_ids = unique([a.robot_id for a in alerts])
  3. DB에서 robots batch 조회 (WHERE id IN (...))                     (DB 1번)
  4. POST http://telemetry-service:10002/telemetry/batch              (HTTP 1번)
       Body: { "robot_ids": robot_ids }
  5. 결과 조합하여 반환
  → 총: DB 2번 + HTTP 1번 = 3번
```

#### Case 2: Strawberry GraphQL

```
Client → Strawberry Gateway

Strawberry 내부:
  1. Query.critical_alerts 리졸버 실행
     → GET http://alert-service:10003/alerts/critical                 (HTTP 1번)
  2. 10개 알람 → 각각 robot_loader.load(robot_id), telemetry_loader.load(robot_id)
  3. DataLoader가 robot_id들을 자동 수집 (중복 제거됨)
     → robot_loader:     GET http://robot-service:10001/robots/{id}   (HTTP N번, 유니크 로봇 수만큼)
     → telemetry_loader: POST http://telemetry-service:10002/telemetry/batch  (HTTP 1번)
  → 총: HTTP 2번 + 유니크 로봇 수만큼 개별 GET
```

> **참고**: 현재 구현에서 `load_robots_batch`는 내부적으로 개별 GET을 사용한다 (dataloaders.py:53-62).
> `POST /robots/batch` 엔드포인트를 만들면 1번으로 줄일 수 있다.
> DataLoader의 장점은 **중복 제거** — 10개 알람이 5개 로봇에서 왔다면 5번만 호출.

#### Case 3: Apollo Federation

```
Client → Apollo Router → 쿼리 플랜 생성

Step 1: Router → Alert Subgraph (GraphQL)
  Alert Subgraph 내부:
    → GET http://alert-service:10003/alerts/critical                  (HTTP 1번)
    → 10개 Alert 반환 (각각 robot_id 포함)

Step 2: Router → Robot Subgraph (GraphQL, _entities)
  Robot Subgraph 내부:
    → resolve_reference가 유니크 robot_id마다 호출
    → GET http://robot-service:10001/robots/{id}                      (HTTP N번, 유니크 로봇 수만큼)

Step 3: Router → Telemetry Subgraph (GraphQL, _entities)
  Telemetry Subgraph 내부:
    → DataLoader: POST http://telemetry-service:10002/telemetry/batch (HTTP 1번)

  → 총: Subgraph 3번 (GraphQL) + 서비스 2번 + 유니크 로봇 GET N번
```

> **참고**: Robot Subgraph의 `resolve_reference`도 개별 GET이다 (robot-subgraph/schema.py:23-36).
> DataLoader나 batch 엔드포인트로 개선 가능.

#### Critical Alerts 호출 수 비교

| | REST (현재 구현) | Strawberry | Apollo Federation |
|---|:---:|:---:|:---:|
| 알람 조회 | DB 1번 | HTTP 1번 | Subgraph→HTTP 1번 |
| 로봇 정보 | DB 1번 (IN 쿼리) | HTTP N번 (개별 GET) | Subgraph→HTTP N번 (개별 GET) |
| 텔레메트리 | HTTP 1번 (POST /telemetry/batch) | HTTP 1번 (DataLoader batch) | Subgraph→HTTP 1번 (DataLoader batch) |
| **총 네트워크 홉** | **3번** | **2+N번** | **2+N번** (+ Subgraph 3번) |

> N = 유니크 로봇 수 (10개 알람이 5개 로봇에서 왔다면 N=5)
> Robot의 batch 엔드포인트가 없어서 Case 2, 3 모두 개별 GET.
> `POST /robots/batch`를 추가하면 모든 케이스에서 3번으로 줄일 수 있다.

---

### 10.4 전체 호출 수 요약

| API | REST (Case 1) | Strawberry (Case 2) | Apollo (Case 3) |
|---|:---:|:---:|:---:|
| Fleet Dashboard | 3번 (batch) | 3번 (DataLoader) | 3+3번 (서비스+Subgraph) |
| Robot Monitor | 3번 | 3번 | 3+3번 (서비스+Subgraph) |
| Critical Alerts | 3번 (batch) | 2+N번 | 2+N+3번 (서비스+Subgraph) |

> **핵심 발견**:
> 1. REST도 batch 엔드포인트를 사용하면 서비스 호출 수는 GraphQL과 동일
> 2. Apollo는 항상 Subgraph 오버헤드(+3번 GraphQL 통신)가 추가됨
> 3. Robot batch 엔드포인트가 없어서 Critical Alerts에서 Case 2, 3은 개별 GET N번 발생 (REST는 자체 DB라 IN 쿼리로 해결)
> 4. 호출 수가 동일해도 차이는 **"batch를 얼마나 쉽게 적용하는가"** (아래 Section 10.5 참고)

---

### 10.5 REST Batch vs GraphQL DataLoader: 본질적 차이

REST도 batch하면 호출 수가 동일해진다. 그러면 왜 GraphQL이 N+1 해결에 유리하다고 하는가?

#### 차이점 요약

| | REST Batch | GraphQL DataLoader |
|---|---|---|
| Batch 구현 위치 | 오케스트레이터 (호출하는 쪽) | DataLoader (선언적) |
| 새 집계 API 추가 시 | 매번 batch 로직 작성 | DataLoader 재사용, 자동 적용 |
| Batch 엔드포인트 | 별도로 설계+구현 필요 | 불필요 (DataLoader가 자동 수집) |
| 개발자 실수 가능성 | 높음 (for loop으로 쓰기 쉬움) | 낮음 (구조적으로 batch 강제) |
| 새 필드 추가 시 | 오케스트레이터 코드 수정 필요 | 스키마에 필드 추가만 하면 됨 |

#### 구체적 비교: "알림에 로봇 위치 추가" 요구사항이 들어왔을 때

**REST (명시적)**:
```python
# 1. 이미 POST /robots/batch 엔드포인트가 있어야 함 (없으면 새로 만들어야)
# 2. orchestrator.py에서 batch 호출 코드를 직접 작성
robot_ids = [alert.robot_id for alert in alerts]
robots_resp = await client.post(f"{ROBOT_URL}/robots/batch", json={"ids": robot_ids})
robots_map = {r["id"]: r for r in robots_resp.json()}
for alert in alerts:
    alert["robot_location"] = robots_map[alert["robot_id"]]["location"]
```

**GraphQL (자동)**:
```python
# 1. 스키마에 필드 하나 추가 → 끝
@strawberry.type
class Alert:
    @strawberry.field
    async def robot(self, info) -> Robot:
        return await info.context["robot_loader"].load(self.robot_id)
        # DataLoader가 여러 alert의 robot_id를 자동으로 모아서 1번에 조회
```

#### 이 프로젝트에서의 선택

이 프로젝트는 **Case 1에서 batch 엔드포인트를 사용**하여 공정한 비교를 한다.

- `orchestrator.py`에서 POST /telemetry/batch, POST /alerts/batch 호출
- `service.py`에서 `get_robots_by_ids` (WHERE id IN (...)) batch DB 조회
- 호출 수는 GraphQL(Case 2)과 동일: Fleet Dashboard 3번, Critical Alerts 3번

> **결론**: 호출 수는 동일해도, REST는 batch를 직접 설계(엔드포인트 추가 + 오케스트레이터 코드 작성)해야 하고,
> GraphQL은 DataLoader 선언만으로 구조적으로 해결된다. 이것이 본질적 차이다.

---

### 10.6 REST Gateway 프록시

Case 1에서 REST Gateway는 Robot Service의 집계 API를 단순 프록시:

```
GET /api/fleet/dashboard    --> http://robot-service:10001/robots/dashboard
GET /api/robots/{id}/monitor --> http://robot-service:10001/robots/{id}/monitor
GET /api/alerts/critical     --> http://robot-service:10001/robots/alerts/critical
```

---

## 11. services/data vs services/orchestrated 차이

```
services/data/                          services/orchestrated/
├── robot-service/                      ├── robot-service/
│   └── app/                            │   └── app/
│       ├── main.py    (기본 API만)      │       ├── main.py    (기본 + 집계 API)
│       └── service.py (DB 조회만)       │       ├── service.py (DB 조회, 동일)
│                                       │       └── orchestrator.py (다른 서비스 호출!)
├── telemetry-service/ (동일)            ├── telemetry-service/ (동일)
└── alert-service/     (동일)            └── alert-service/     (동일)
```

- `telemetry-service`와 `alert-service`는 data/ 와 orchestrated/ 에서 **완전 동일**
- `robot-service`만 orchestrated/에서 `orchestrator.py` 추가 + `main.py`에 집계 라우트 추가

---

## 12. 구현 순서

### Phase 1: 공용 인프라
- shared/db/models.py, database.py, seed.py
- shared/schemas/
- docker-compose.base.yml
- .env.example, .gitignore

### Phase 2: 데이터 마이크로서비스 (services/data/)
- robot-service (기본 API)
- telemetry-service (기본 + batch API)
- alert-service (기본 + batch + critical 필터)
- Dockerfile 3개
- 통합 테스트

### Phase 3: Case 1 (REST)
- services/orchestrated/robot-service (orchestrator.py 추가)
- gateways/rest/ (프록시)
- docker-compose.case1.yml
- scripts/case1-rest.sh

### Phase 4: Case 2 (Strawberry)
- gateways/strawberry/ (schema, dataloaders)
- docker-compose.case2.yml
- scripts/case2-strawberry.sh

### Phase 5: Case 3 (Apollo Federation)
- gateways/apollo-federation/ (router + subgraph 3개)
- supergraph.graphql 생성
- docker-compose.case3.yml
- scripts/case3-apollo.sh

### Phase 6: 모니터링 스택
- docker-compose.base.yml에 Prometheus + Grafana 추가
- Grafana 대시보드 프로비저닝

### Phase 7: 성능 테스트
- k6/common.js
- k6/case1-rest.js, case2-strawberry.js, case3-apollo.js
- scripts/stop.sh

---

## 13. 클라이언트 호출수 확인

**모든 케이스에서 k6가 보내는 요청수는 동일하다.**

```
k6 → GET http://localhost:10000/api/fleet/dashboard    (Case 1)
k6 → POST http://localhost:10000/graphql               (Case 2)
k6 → POST http://localhost:10000/graphql               (Case 3)
```

- k6 입장에서는 항상 localhost:10000에 1번 요청
- 내부에서 어떻게 처리되는지는 케이스별로 다름
- **측정 대상은 이 1번 요청의 응답 시간과 처리량**

---

## 14. k6 테스트 설계

### 14.1 두 가지 테스트 모드

#### Mode 1: Duration-based (부하 유지)

```
입력: VU(가상유저) + Duration(유지시간)
예시: 50 VU, 5분

동작: 50명이 5분 동안 쉬지 않고 계속 요청
결과: 총 요청수, RPS, p50/p95/p99 응답시간
```

```bash
# 사용법
./scripts/k6-duration.sh --case 1 --vus 50 --duration 5m
./scripts/k6-duration.sh --case 2 --vus 50 --duration 5m
./scripts/k6-duration.sh --case 3 --vus 50 --duration 5m
```

비교 포인트:
- **같은 시간 동안 어떤 케이스가 더 많은 요청을 처리하는가?**
- REST (Case 1): 내부 3번 호출 (batch 엔드포인트 사용) → GraphQL과 동일한 호출 수
- Strawberry (Case 2): 내부 3번 호출 (DataLoader 자동 batch) → REST와 동일한 호출 수
- Apollo (Case 3): 내부 3번 + Subgraph 오버헤드 3번 → 총 6번, Case 1·2보다 약간 느릴 수 있음
- 핵심 비교: 같은 호출 수에서 REST vs GraphQL vs Federation의 순수 오버헤드 차이

#### Mode 2: Iteration-based (고정 콜수)

```
입력: VU(가상유저) + Iterations(총 요청수)
예시: 50 VU, 1000 콜

동작: 50명이 총 1000번 요청을 분담하여 처리
결과: 완료 시간, p50/p95/p99 응답시간
```

```bash
# 사용법
./scripts/k6-iterations.sh --case 1 --vus 50 --iterations 1000
./scripts/k6-iterations.sh --case 2 --vus 50 --iterations 1000
./scripts/k6-iterations.sh --case 3 --vus 50 --iterations 1000
```

비교 포인트:
- **같은 요청수를 처리하는 데 어떤 케이스가 더 빠른가?**
- REST (Case 1): batch 사용으로 Strawberry와 유사한 성능 예상
- Strawberry (Case 2): 가장 빠를 것으로 예상
- Apollo (Case 3): Case 2보다 약간 느림 (Subgraph 오버헤드)

### 14.2 k6 테스트 시나리오

각 케이스에서 3가지 API를 비율 기반으로 호출:

```
Fleet Dashboard  : 50% (N+1 극대화, 핵심 비교 대상)
Robot Monitor    : 30% (차이 없음, 베이스라인)
Critical Alerts  : 20% (N+1 발생)
```

### 14.3 k6 → Prometheus 연동

k6는 Prometheus remote write를 지원한다:

```bash
k6 run \
  --out experimental-prometheus-rw \
  --env K6_PROMETHEUS_RW_SERVER_URL=http://localhost:19090/api/v1/write \
  case1-rest.js
```

k6가 전송하는 메트릭:
- `k6_http_req_duration` : 요청 응답 시간
- `k6_http_reqs` : 총 요청수
- `k6_http_req_failed` : 실패율
- `k6_iterations` : 총 이터레이션
- `k6_vus` : 활성 VU 수

---

## 15. 모니터링 스택 (Prometheus + Grafana)

### 15.1 아키텍처

```
┌──────┐     ┌────────────┐     ┌─────────┐
│  k6  │──── │ Prometheus │──── │ Grafana │
│      │ rw  │  (:19090)  │     │(:13000) │
└──────┘     └────────────┘     └─────────┘
                   │
                   │ scrape
                   │
          ┌────────┴────────┐
          │ 마이크로서비스    │
          │ /metrics         │
          └─────────────────┘
```

- k6 → Prometheus: remote write (테스트 메트릭)
- Prometheus → 마이크로서비스: scrape (서비스 메트릭, 호출 카운터)
- Grafana → Prometheus: 쿼리 (대시보드 시각화)

### 15.2 포트 배정 (모니터링)

```
Prometheus : 19090
Grafana    : 13000
```

### 15.3 docker-compose.base.yml 에 추가

```yaml
  prometheus:
    image: prom/prometheus:v2.51.0
    ports:
      - "19090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--web.enable-remote-write-receiver'
    networks:
      - fleet-net

  grafana:
    image: grafana/grafana:10.4.0
    ports:
      - "13000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_AUTH_ANONYMOUS_ENABLED: "true"
      GF_AUTH_ANONYMOUS_ORG_ROLE: Admin
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
    depends_on:
      - prometheus
    networks:
      - fleet-net
```

### 15.4 Prometheus 설정 (monitoring/prometheus.yml)

```yaml
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'robot-service'
    static_configs:
      - targets: ['robot-service:10001']

  - job_name: 'telemetry-service'
    static_configs:
      - targets: ['telemetry-service:10002']

  - job_name: 'alert-service'
    static_configs:
      - targets: ['alert-service:10003']
```

### 15.5 Grafana 대시보드

#### Dashboard 1: k6 성능 비교

패널:
- **RPS (Requests Per Second)**: 케이스별 처리량
- **Response Time (p50, p95, p99)**: 응답 시간 분포
- **Total Requests**: 총 요청수 (Duration 모드)
- **Total Duration**: 총 소요 시간 (Iteration 모드)
- **Error Rate**: 실패율
- **Active VUs**: 가상 유저 수

#### Dashboard 2: 마이크로서비스 내부 호출

패널:
- **호출 횟수 by endpoint**: 각 서비스의 엔드포인트별 호출 수
- **호출 횟수 비교**: Case 1 (31번) vs Case 2 (3번) vs Case 3 (3번+Subgraph)
- **서비스별 응답 시간**: 마이크로서비스 레벨 레이턴시

---

## 16. 마이크로서비스 메트릭 노출

각 마이크로서비스에 Prometheus 메트릭 엔드포인트 추가:

```
GET /metrics

노출 메트릭:
  http_requests_total{method, endpoint, status}  : 총 요청수
  http_request_duration_seconds{endpoint}         : 요청 처리 시간
```

Python에서 `prometheus-fastapi-instrumentator` 또는 수동 미들웨어로 구현.

---

## 17. 업데이트된 디렉토리 구조 (모니터링 추가)

```
graph-rest-preform/
├── ...기존 구조...
│
├── monitoring/                          # 모니터링 설정
│   ├── prometheus.yml                   # Prometheus 스크래핑 설정
│   └── grafana/
│       ├── provisioning/
│       │   ├── datasources/
│       │   │   └── prometheus.yml       # Grafana → Prometheus 연결
│       │   └── dashboards/
│       │       └── dashboard.yml        # 대시보드 자동 로드 설정
│       └── dashboards/
│           ├── k6-performance.json      # k6 성능 비교 대시보드
│           └── service-metrics.json     # 마이크로서비스 호출 대시보드
│
├── scripts/
│   ├── case1-rest.sh                    # Case 1 기동
│   ├── case2-strawberry.sh              # Case 2 기동
│   ├── case3-apollo.sh                  # Case 3 기동
│   ├── k6-duration.sh                   # Mode 1: 부하 유지 테스트
│   ├── k6-iterations.sh                 # Mode 2: 고정 콜수 테스트
│   ├── stop.sh                          # 전체 종료
│   └── seed.sh                          # DB 시드 데이터
│
├── k6/
│   ├── common.js                        # 공통 설정, 시나리오 비율
│   ├── case1-rest.js                    # REST 테스트 (GET 요청)
│   ├── case2-strawberry.js              # Strawberry 테스트 (GraphQL 쿼리)
│   ├── case3-apollo.js                  # Apollo 테스트 (GraphQL 쿼리)
│   └── results/
│       └── .gitkeep
...
```

---

## 18. 스크립트 사용법 정리

```bash
# 1. Case 기동 (DB + 모니터링 + 서비스 + Gateway)
./scripts/case1-rest.sh

# 2-A. Duration 테스트 (5분, 50유저)
./scripts/k6-duration.sh --case 1 --vus 50 --duration 5m
# → 결과: 5분간 총 요청수, RPS, p95 등

# 2-B. Iteration 테스트 (50유저, 1000콜)
./scripts/k6-iterations.sh --case 1 --vus 50 --iterations 1000
# → 결과: 1000콜 완료까지 걸린 시간, p95 등

# 3. Grafana에서 결과 확인
open http://localhost:13000
# → k6 성능 비교 대시보드
# → 마이크로서비스 호출 대시보드

# 4. 종료 후 다음 케이스
./scripts/stop.sh
./scripts/case2-strawberry.sh
./scripts/k6-duration.sh --case 2 --vus 50 --duration 5m
```

---

## 19. 전체 포트 맵 (최종)

```
PostgreSQL        : 15432
Prometheus        : 19090
Grafana           : 13000
Gateway 진입점    : 10000
Robot Service     : 10001
Telemetry Service : 10002
Alert Service     : 10003
Robot Subgraph    : 10011 (Case 3만)
Telemetry Subgraph: 10012 (Case 3만)
Alert Subgraph    : 10013 (Case 3만)
```
