** User **
자 우리가 백엔드 서비스를 개발해야해. 마이크로서비스로 개발할거고 파이썬백엔드야. 근데 고민이 있어 레스트로 할지 그래프큐엘로 개발할지....그래서 성능테스트를 빡쎄게 하고 가보려고, 근데 우리시스템이 커서 구현하기 어려우니 간단하게 아키텍쳐링하자, 마이크로서비스는 3개정도하고, 데이터베이스는 딱 한개로 쓰고, 클라이언트에서 호출하는 에이피아이는 딱 3개 만들자, 마이크로서비스여서 직접 필요하면 서로 호출해야하니 필요한 에이피아이 더 개발해도 되고, 마이크로서비스를 충분히 잘 테스트할수있으면 좋겠는데, 설계좀해봐

** AI System **
좋아, 마이크로서비스 아키텍처로 REST vs GraphQL 성능 비교 테스트를 위한 간단하면서도 의미있는 설계를 해볼게.
시나리오: 간단한 이커머스 시스템
실제 마이크로서비스 패턴을 잘 보여줄 수 있는 구조로 잡았어.
┌─────────────────────────────────────────────────────────────────┐
│                         Client                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │           API Gateway                    │
        │   (REST 버전 / GraphQL 버전 각각 구현)    │
        └─────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
   │   User      │    │   Product   │    │   Order     │
   │   Service   │    │   Service   │    │   Service   │
   │   :8001     │    │   :8002     │    │   :8003     │
   └─────────────┘    └─────────────┘    └─────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │     :5432       │
                    └─────────────────┘

3개 마이크로서비스 설계
1. User Service (:8001)
내부 API설명GET /users/{id}사용자 정보 조회GET /users/{id}/profile프로필 상세 (Order Service가 호출)
2. Product Service (:8002)
내부 API설명GET /products/{id}상품 정보 조회GET /products?ids=1,2,3여러 상품 일괄 조회 (Order Service가 호출)PATCH /products/{id}/stock재고 차감 (Order Service가 호출)
3. Order Service (:8003)
내부 API설명POST /orders주문 생성 (→ User, Product 호출)GET /orders/{id}주문 상세 (→ User, Product 호출)GET /users/{id}/orders사용자 주문 목록

클라이언트 API 3개 (성능 테스트 대상)
API설명테스트 포인트1. 주문 상세 조회주문 + 사용자 + 상품들 정보N+1 문제, 데이터 집계2. 주문 생성재고 확인 → 차감 → 주문 저장트랜잭션, 서비스간 호출3. 사용자 대시보드사용자 정보 + 최근 주문 + 주문별 상품복잡한 중첩 데이터

왜 이 설계가 테스트에 좋은지
테스트 관점이 설계에서 검증 가능한 것N+1 문제주문에 상품 5개 있으면 REST는 5번 호출, GraphQL은 DataLoader로 1번Over-fetchingREST는 항상 전체 필드, GraphQL은 필요한 필드만서비스간 통신Order → User, Product 호출 패턴 비교복잡한 쿼리대시보드 API에서 중첩 데이터 처리 성능

데이터 모델 (PostgreSQL)
sql-- users
id, email, name, created_at

-- products  
id, name, price, stock, category

-- orders
id, user_id, status, total_amount, created_at

-- order_items
id, order_id, product_id, quantity, price

이 설계로 가면 될까? 괜찮으면 바로 구현 시작할게.
REST 버전이랑 GraphQL 버전 둘 다 만들어서 동일한 테스트 시나리오로 성능 비교할 수 있게 해줄게.그 주문상제조회가 N+1맞지?근데 저렇게 되어도 클라이언트에서 호출하는 건수는 같지? 마이크로 서비스 내부에서 필요시 더 다른 서비스 호출하는거고?2월 4일맞아! 정확하게 이해했어.
클라이언트 호출 vs 내부 서비스간 호출
클라이언트 → API Gateway

호출 횟수: 1번 (REST든 GraphQL이든 동일)
GET /api/orders/123 (REST)
query { order(id: 123) { ... } } (GraphQL)

내부에서 일어나는 일 (여기서 차이 발생!)
REST 방식:
Client → API Gateway (1번)
         ↓
    Order Service
         ↓
    1. GET /orders/123 조회
       → order_items에 상품이 5개 있음
    2. GET /users/456 (User Service 호출 1번)
    3. GET /products/1 (Product Service 호출)
    4. GET /products/2 (Product Service 호출)
    5. GET /products/3 (Product Service 호출)
    6. GET /products/4 (Product Service 호출)
    7. GET /products/5 (Product Service 호출)
    ↓
    총 내부 호출: 6번 (User 1번 + Product 5번)
GraphQL 방식 (DataLoader 사용시):
Client → API Gateway (1번)
         ↓
    Order Service
         ↓
    1. GET /orders/123 조회
       → order_items에 상품이 5개 있음
    2. GET /users/456 (User Service 호출 1번)
    3. GET /products?ids=1,2,3,4,5 (Product Service 호출 1번)
    ↓
    총 내부 호출: 2번 (User 1번 + Product 1번 - 배치)

성능 차이 포인트
항목RESTGraphQL (DataLoader)클라이언트 요청1번1번내부 네트워크 호출N+1번2번네트워크 레이턴시높음 (호출 많음)낮음 (배치 처리)서비스 부하분산됨 (여러번)집중됨 (적게)

추가로 테스트할 포인트
사용자 대시보드 API 같은 경우는 더 극적이야:
최근 주문 10개 + 각 주문의 상품들 (평균 3개씩)

REST: 1(사용자) + 10(주문들) + 30(상품들) = 41번 내부 호출
GraphQL: 1(사용자) + 1(주문 배치) + 1(상품 배치) = 3번 내부 호출
이게 마이크로서비스에서 REST vs GraphQL의 진짜 차이점이야.
클라이언트는 1번만 호출하지만, 뒤에서 서비스들이 서로 얼마나 효율적으로 통신하느냐가 핵심!
이 구조로 진행할까?

** User **

우리는 b2b라서 커머스만큼 복잡도가 높지는 않을거같은데....너무 극단적인거 아니야?

** AI System **
 맞아, B2B면 커머스보다는 훨씬 단순하지.
좀 더 현실적인 B2B 시나리오로 바꿔볼게.

시나리오: B2B SaaS 대시보드 시스템
┌─────────────────────────────────────────────────────────────────┐
│                    Client (기업 관리자)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │           API Gateway                    │
        └─────────────────────────────────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
   │  Company    │    │   User      │    │  Usage      │
   │  Service    │    │   Service   │    │  Service    │
   └─────────────┘    └─────────────┘    └─────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    └─────────────────┘

3개 마이크로서비스
1. Company Service

기업 정보, 구독 플랜, 설정 관리
GET /companies/{id}
GET /companies/{id}/settings

2. User Service

기업 소속 사용자 관리
GET /users/{id}
GET /companies/{company_id}/users (Company Service가 호출)

3. Usage Service

사용량, 로그, 이벤트 추적
GET /users/{user_id}/usage (User Service가 호출)
GET /companies/{company_id}/usage-summary (Company Service가 호출)


클라이언트 API 3개
1. 기업 대시보드 조회
GET /api/companies/{id}/dashboard
포함 데이터:

기업 정보 (플랜, 설정)
소속 사용자 목록 (10명 정도)
전체 사용량 요약

내부 호출:

REST: Company(1) + Users(1) + Usage(10) = 12번
GraphQL: Company(1) + Users(1) + Usage(1 배치) = 3번


2. 사용자 상세 + 활동 내역
GET /api/users/{id}/details
포함 데이터:

사용자 기본 정보
소속 기업 정보
최근 30일 사용 통계

내부 호출:

REST: User(1) + Company(1) + Usage(1) = 3번
GraphQL: 동일 3번

→ 이건 차이 없음 (N+1 아님)

3. 팀별 사용량 리포트
GET /api/companies/{id}/team-report
포함 데이터:

기업 정보
사용자별 사용량 (20명)

내부 호출:

REST: Company(1) + Users(1) + Usage(20) = 22번
GraphQL: Company(1) + Users(1) + Usage(1 배치) = 3번


왜 이게 더 현실적인가?
커머스 시나리오B2B SaaS 시나리오주문당 상품 수십개기업당 사용자 10~20명재고 트랜잭션 복잡단순 조회 위주실시간 재고 차감배치 집계 가능
B2B는 조회가 80%, 쓰기가 20% 정도라서:

N+1은 여전히 발생하지만 "10~20배" 정도 차이
트랜잭션 복잡도는 낮음
캐싱 효과가 더 좋음


이 정도면 적당해? 아니면 더 단순하게 갈까?

** User **
로봇관련 모니터링서비스야, 우리 내부개발자들이 보는거고, 다시 쭉 설계해보자

** AI System **
아 로봇 모니터링이면 완전 다르네! 내부 개발자용이면 더 현실적으로 가자.

시나리오: 로봇 플릿 모니터링 시스템
┌─────────────────────────────────────────────────────────────────┐
│              Client (내부 개발자/운영자)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │           API Gateway                    │
        └─────────────────────────────────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
   │   Robot     │    │   Telemetry │    │   Alert     │
   │   Service   │    │   Service   │    │   Service   │
   │   :8001     │    │   :8002     │    │   :8003     │
   └─────────────┘    └─────────────┘    └─────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    └─────────────────┘

3개 마이크로서비스 설계
1. Robot Service (:8001)
로봇 메타데이터 및 상태 관리
API설명GET /robots/{id}로봇 기본 정보 (모델, 위치, 펌웨어 버전)GET /robots전체 로봇 목록GET /robots/{id}/config로봇 설정 정보 (Alert Service가 호출)
데이터:
python{
  "id": "robot-001",
  "name": "Warehouse-Robot-A",
  "model": "AGV-X200",
  "location": "Building-3-Floor-2",
  "firmware_version": "v2.3.1",
  "status": "active"
}

2. Telemetry Service (:8002)
센서 데이터 및 성능 메트릭
API설명GET /telemetry/robots/{id}/latest최신 텔레메트리 (배터리, CPU, 온도)GET /telemetry/robots/{id}/metrics?period=1h시계열 메트릭POST /telemetry/batch-query여러 로봇 일괄 조회 (Alert Service가 호출)
데이터:
python{
  "robot_id": "robot-001",
  "timestamp": "2024-02-04T10:30:00Z",
  "battery_level": 85.5,
  "cpu_usage": 45.2,
  "temperature": 42.1,
  "network_latency_ms": 12
}

3. Alert Service (:8003)
알람 및 이벤트 관리
API설명GET /alerts/robots/{id}특정 로봇의 활성 알람GET /alerts?severity=critical심각도별 알람 필터링GET /alerts/{id}/details알람 상세 (→ Robot, Telemetry 호출)
데이터:
python{
  "id": "alert-123",
  "robot_id": "robot-001",
  "type": "battery_low",
  "severity": "warning",
  "message": "Battery below 20%",
  "timestamp": "2024-02-04T10:25:00Z"
}
```

---

## 클라이언트 API 3개 (성능 테스트 대상)

### 1. **플릿 대시보드 (Fleet Overview)**
```
GET /api/fleet/dashboard
```

**응답 데이터:**
- 전체 로봇 목록 (15대)
- 각 로봇의 최신 텔레메트리
- 활성 알람 카운트

**내부 호출:**
```
REST:
- GET /robots (1번)
- GET /telemetry/robots/{id}/latest × 15번
- GET /alerts/robots/{id} × 15번
= 총 31번

GraphQL (DataLoader):
- GET /robots (1번)  
- POST /telemetry/batch-query (1번 - 15대 일괄)
- GET /alerts?robot_ids=... (1번 - 15대 일괄)
= 총 3번
```

**N+1 발생: 로봇 수만큼 반복 조회**

---

### 2. **로봇 상세 모니터링**
```
GET /api/robots/{id}/monitor
```

**응답 데이터:**
- 로봇 기본 정보
- 최근 1시간 메트릭 (시계열)
- 최근 알람 5개

**내부 호출:**
```
REST & GraphQL 동일:
- GET /robots/{id} (1번)
- GET /telemetry/robots/{id}/metrics?period=1h (1번)
- GET /alerts/robots/{id}?limit=5 (1번)
= 총 3번
```

**차이 없음: 1:1 관계라서 N+1 아님**

---

### 3. **알람 상세 조회 (여러 건)**
```
GET /api/alerts/critical
```

**응답 데이터:**
- 심각도 critical 알람 10개
- 각 알람의 로봇 정보
- 각 알람 발생 시점의 텔레메트리 스냅샷

**내부 호출:**
```
REST:
- GET /alerts?severity=critical (1번)
- GET /robots/{id} × 10번
- GET /telemetry/robots/{id}/latest × 10번  
= 총 21번

GraphQL (DataLoader):
- GET /alerts?severity=critical (1번)
- GET /robots?ids=... (1번 - 배치)
- POST /telemetry/batch-query (1번 - 배치)
= 총 3번
N+1 발생: 알람 개수만큼 반복 조회

데이터베이스 스키마
sql-- robots
id, name, model, location, firmware_version, status, created_at

-- telemetry_data
id, robot_id, timestamp, battery_level, cpu_usage, temperature, network_latency_ms

-- alerts  
id, robot_id, type, severity, message, status, created_at, resolved_at

왜 이 설계가 현실적인가?
특징로봇 모니터링 특성조회 패턴대시보드에서 여러 로봇 한번에 조회 (N+1 자주 발생)데이터 빈도텔레메트리는 초당 수십~수백건 (시계열 DB 고려)복잡도트랜잭션 단순, 조회 위주사용자내부 개발자 → 복잡한 쿼리 가능

추가 고려사항
텔레메트리 데이터가 많으면:

PostgreSQL 말고 TimescaleDB나 InfluxDB 고려
하지만 테스트 목적이니 PostgreSQL + 인덱싱으로 충분

실시간성:

WebSocket/SSE는 일단 제외
REST/GraphQL 폴링으로만 비교

이 정도면 적당해? 로봇 15대 정도로 테스트하면 N+1 차이 확실히 보일 거야!그래 딱좋다. 다시말하지만 클라이언트 콜수는 똑같지? 내부적으로 서로 호출량은 달라도? 그리고 아폴로랑 스트로베리는 써야해2월 4일맞아! 정확해.

클라이언트 호출 횟수: REST = GraphQL
클라이언트 → API Gateway: 항상 1번

GET /api/fleet/dashboard (REST)
query { fleetDashboard { ... } } (GraphQL)
내부에서만 차이 발생:

REST: 31번 (Robot 1 + Telemetry 15 + Alert 15)
GraphQL: 3번 (DataLoader로 배치 처리)


기술 스택 확정
GraphQL

Apollo Server (Node.js/Express) 또는
Strawberry (Python/FastAPI)

둘 다 써야 한다는 건 비교 테스트하려는 거야? 아니면 하나만 선택?
추천 조합
Option 1: Python 풀스택 (추천)
API Gateway (GraphQL): Strawberry + FastAPI
마이크로서비스 3개: FastAPI (REST)

장점: 언어 통일, 관리 편함
Strawberry가 DataLoader 지원함

Option 2: Apollo + Python
API Gateway (GraphQL): Apollo Server (Node.js)
마이크로서비스 3개: FastAPI (REST)

장점: Apollo 생태계 강력 (Apollo Studio, 캐싱)
단점: Node.js + Python 혼용

Option 3: 둘 다 구현 (비교용)
GraphQL 버전 A: Strawberry
GraphQL 버전 B: Apollo Server
마이크로서비스: FastAPI (공통)

Apollo vs Strawberry 성능도 비교 가능


내가 추천하는 방식
┌─────────────────────────────────────────┐
│  Client                                  │
└─────────────────────────────────────────┘
         │              │
         ▼              ▼
┌──────────────┐  ┌──────────────┐
│ REST Gateway │  │ GraphQL GW   │
│  (FastAPI)   │  │ (Strawberry) │
└──────────────┘  └──────────────┘
         │              │
         └──────┬───────┘
                ▼
    ┌───────────────────────┐
    │  Microservices (3개)  │
    │  FastAPI (REST)       │
    └───────────────────────┘
동일한 마이크로서비스를 두 Gateway가 호출
→ REST vs GraphQL 정확한 비교 가능

어떻게 할까?

Strawberry만 (Python 풀스택)
Apollo만 (Node + Python)
둘 다 (비교 테스트)

추천은 **1번 (Strawberry)**인데, Apollo도 보고 싶으면 3번!

** User **
근데 아폴로랑 스트로베리는 무슨 차이야? 정확히 말해줘

** AI System **
좋아, 정확하게 비교해줄게.

Apollo Server vs Strawberry: 핵심 차이
1. 언어 및 생태계
Apollo ServerStrawberry언어JavaScript/TypeScript (Node.js)Python프레임워크Express, Fastify, Koa 등FastAPI, Django, Flask 등타입 시스템TypeScript 기반Python Type Hints 기반

2. 스키마 정의 방식
Apollo Server (Schema First)
typescript// SDL로 스키마 먼저 정의
const typeDefs = gql`
  type Robot {
    id: ID!
    name: String!
    batteryLevel: Float
  }
  
  type Query {
    robot(id: ID!): Robot
  }
`;

// 리졸버 별도 구현
const resolvers = {
  Query: {
    robot: (parent, args, context) => {
      return fetchRobot(args.id);
    }
  }
};
Strawberry (Code First)
python# 파이썬 코드로 스키마 생성
import strawberry

@strawberry.type
class Robot:
    id: str
    name: str
    battery_level: float | None

@strawberry.type
class Query:
    @strawberry.field
    def robot(self, id: str) -> Robot:
        return fetch_robot(id)

3. DataLoader 구현
Apollo Server
typescriptimport DataLoader from 'dataloader';

const robotLoader = new DataLoader(async (ids) => {
  const robots = await fetchRobotsByIds(ids);
  return ids.map(id => robots.find(r => r.id === id));
});

// 리졸버에서 사용
const resolvers = {
  Alert: {
    robot: (alert, args, { robotLoader }) => {
      return robotLoader.load(alert.robotId);
    }
  }
};
Strawberry
pythonfrom strawberry.dataloader import DataLoader

async def load_robots(keys: list[str]) -> list[Robot]:
    robots = await fetch_robots_by_ids(keys)
    return [robots.get(k) for k in keys]

robot_loader = DataLoader(load_fn=load_robots)

@strawberry.type
class Alert:
    robot_id: str
    
    @strawberry.field
    async def robot(self) -> Robot:
        return await robot_loader.load(self.robot_id)
차이점:

Apollo: 별도 라이브러리 (dataloader 패키지)
Strawberry: 내장 지원 (strawberry.dataloader)


4. 주요 기능 비교
기능Apollo ServerStrawberryDataLoader✅ (별도 설치)✅ (내장)Subscription✅ (WebSocket)✅ (WebSocket, SSE)Federation✅ (Apollo Federation)✅ (실험적)Caching✅ (Apollo Cache Control)⚠️ (수동 구현)Tracing✅ (Apollo Studio)⚠️ (OpenTelemetry 연동)Playground✅ (Apollo Sandbox)✅ (GraphiQL)Type Safety✅ (TypeScript)✅ (Python Type Hints)

5. 성능 특성
Apollo Server (Node.js)

비동기 I/O 최적화 (이벤트 루프)
단일 스레드지만 I/O bound 작업에 강함
CPU intensive 작업은 약함

Strawberry (Python)

asyncio 기반 (FastAPI와 찰떡)
CPU bound는 멀티프로세싱 필요
I/O bound는 Apollo와 비슷한 성능


6. 개발자 경험 (DX)
Apollo Server
typescript✅ TypeScript로 타입 안전성 100%
✅ Apollo Studio (무료) - 실시간 모니터링, 스키마 레지스트리
✅ 방대한 생태계 (Apollo Client, Apollo Router)
⚠️ JS/TS 러닝커브 (Python 개발자에게)
Strawberry
python✅ Python 네이티브 - 기존 FastAPI 코드 재사용
✅ 직관적인 데코레이터 문법
✅ Pydantic 모델 바로 사용 가능
⚠️ Apollo Studio 같은 관리 도구 없음
⚠️ Federation 지원 약함

7. 프로덕션 도구
도구ApolloStrawberry모니터링Apollo Studio (무료)Prometheus + Grafana스키마 관리Schema Registry수동 관리캐싱Automatic Persisted QueriesRedis 직접 연동Rate LimitingApollo RouterFastAPI middleware

실전 비교: 같은 기능 구현
플릿 대시보드 쿼리
Apollo Server
typescripttype Query {
  fleetDashboard: FleetDashboard!
}

type FleetDashboard {
  robots: [Robot!]!
}

type Robot {
  id: ID!
  name: String!
  latestTelemetry: Telemetry
  activeAlerts: [Alert!]!
}

const resolvers = {
  Robot: {
    latestTelemetry: (robot, _, { telemetryLoader }) => {
      return telemetryLoader.load(robot.id);
    },
    activeAlerts: (robot, _, { alertLoader }) => {
      return alertLoader.load(robot.id);
    }
  }
};
Strawberry
python@strawberry.type
class Query:
    @strawberry.field
    async def fleet_dashboard(self) -> FleetDashboard:
        return await get_fleet_dashboard()

@strawberry.type
class Robot:
    id: str
    name: str
    
    @strawberry.field
    async def latest_telemetry(self) -> Telemetry:
        return await telemetry_loader.load(self.id)
    
    @strawberry.field  
    async def active_alerts(self) -> list[Alert]:
        return await alert_loader.load(self.id)

너의 상황에서 추천
Strawberry를 선택해야 하는 경우:
✅ 백엔드가 이미 Python (FastAPI)
✅ 팀이 Python에 익숙함
✅ 간단한 모니터링 시스템 (Apollo Studio 불필요)
✅ 빠른 프로토타이핑 필요
Apollo를 선택해야 하는 경우:
✅ 엔터프라이즈급 관리 도구 필요
✅ Microservice Federation 필요
✅ Apollo Client 사용 (프론트엔드)
✅ 팀에 Node.js 개발자 있음

최종 추천
너의 경우 (로봇 모니터링, Python 백엔드):
→ Strawberry 추천 🍓
이유:

마이크로서비스가 FastAPI면 언어 통일
DataLoader 내장이라 N+1 해결 쉬움
Type Hints로 타입 안전성 확보
내부 도구라 Apollo Studio 불필요
러닝커브 낮음

하지만 Apollo도 테스트해볼 가치 있음:

성능 비교 목적이면 둘 다 구현
Apollo Federation 나중에 필요할 수도

어떻게 할까? Strawberry로 가고, 나중에 필요하면 Apollo 추가?

** User **
아폴로 https://github.com/apollographql/apollo-server 이거 ...이거 그냥 엔진엑스같은거 아니야? 그래프뷰엘 페더레이션해주고?

** AI System **
아 잠깐, 네가 맞는 부분도 있고 아닌 부분도 있어. 정리해줄게.

Apollo Server의 정체
Apollo Server는 GraphQL 엔진이야. 네가 생각한 것처럼:
❌ Nginx 같은 순수 프록시는 아님

요청만 라우팅하는 게 아니라
GraphQL 쿼리를 실제로 실행하는 서버

✅ 하지만 Federation에서는 "게이트웨이" 역할도 함

Apollo의 두 가지 역할
1. 단일 GraphQL 서버 (우리가 쓸 방식)
Client → Apollo Server → 비즈니스 로직 실행
                      → DB 조회
                      → 마이크로서비스 호출
이 경우 Apollo Server가:

스키마 정의
리졸버 구현
DataLoader로 N+1 해결
실제 데이터 가져오기

→ Strawberry랑 완전히 동일한 역할

2. Apollo Federation (Gateway)
이게 네가 말한 "Nginx 같은" 역할:
                    ┌─ Robot Subgraph (Apollo Server)
                    │
Client → Apollo     ├─ Telemetry Subgraph (Apollo Server)
         Gateway    │
         (Router)   └─ Alert Subgraph (Apollo Server)
Apollo Router (Rust) 또는 **Apollo Gateway (Node)**가:

여러 서브그래프의 스키마를 합침
쿼리를 분해해서 각 서브그래프로 라우팅
결과를 조합해서 클라이언트에 응답

→ 이건 Nginx보다는 GraphQL 전용 API Gateway

우리 프로젝트에서는?
지금 설계한 구조
Client → API Gateway (GraphQL) → 3개 마이크로서비스 (REST)
Option 1: Apollo Server 단독
typescript// Apollo Server가 직접 마이크로서비스 호출
const resolvers = {
  Query: {
    fleetDashboard: async () => {
      const robots = await fetch('http://robot-service:8001/robots');
      // ... 나머지 로직
    }
  }
}
```

→ 이건 Strawberry랑 똑같은 역할

---

**Option 2: Apollo Federation (과잉)**
```
Client → Apollo Gateway 
           ├─ Robot Subgraph (Apollo Server) → Robot Service
           ├─ Telemetry Subgraph (Apollo Server) → Telemetry Service  
           └─ Alert Subgraph (Apollo Server) → Alert Service
```

→ 각 마이크로서비스 앞에 Apollo Server 하나씩 더 붙이는 거
→ **너무 복잡함, 불필요함**

---

## Federation이 필요한 경우

### 예시: 마이크로서비스가 이미 GraphQL일 때
```
만약 Robot Service가 GraphQL을 직접 제공한다면:

type Robot {
  id: ID!
  name: String!
}

type Query {
  robot(id: ID!): Robot
}
```

이런 상황에서:
- Robot Service: GraphQL 스키마 제공
- Telemetry Service: GraphQL 스키마 제공  
- Alert Service: GraphQL 스키마 제공

→ Apollo Federation이 이 3개를 **하나의 통합 스키마**로 합쳐줌

---

## 우리 경우는?

**마이크로서비스가 REST API 제공**
```
Robot Service: GET /robots/{id}
Telemetry Service: GET /telemetry/robots/{id}/latest
Alert Service: GET /alerts/robots/{id}
```

→ **Federation 불필요**
→ Apollo Server 또는 Strawberry가 **단독으로 REST 호출하면 됨**

---

## 정리

| | Apollo Server | Apollo Federation |
|---|---|---|
| **역할** | GraphQL 실행 엔진 | GraphQL 게이트웨이 (여러 GraphQL 통합) |
| **유사 제품** | Strawberry, GraphQL-Yoga | Kong, Nginx (개념적으로) |
| **우리 프로젝트** | ✅ 필요 (Gateway 역할) | ❌ 불필요 (마이크로서비스가 REST) |

---

## 최종 아키텍처 확정
```
┌─────────────────────────────────────────┐
│  Client                                  │
└─────────────────────────────────────────┘
         │              │
         ▼              ▼
┌──────────────┐  ┌──────────────┐
│ REST Gateway │  │ GraphQL GW   │
│  (FastAPI)   │  │ (Strawberry  │ ← 단독 서버
│              │  │  or Apollo)  │   마이크로서비스 REST 호출
└──────────────┘  └──────────────┘
         │              │
         └──────┬───────┘
                ▼
    ┌───────────────────────┐
    │  Microservices (3개)  │
    │  FastAPI (REST)       │
    └───────────────────────┘
Apollo Federation은 나중에 마이크로서비스가 GraphQL을 직접 제공하게 되면 고려하면 돼.
지금은 Strawberry (Python) 또는 Apollo Server (Node) 중 하나만 선택해서
Gateway 역할만 하면 충분해!
어떻게 할까?그럼 각종 경우의 수를 잘 정리해줘봐....용도도 헷갈린다2월 4일좋아, 모든 경우의 수를 명확하게 정리해줄게.

1. 마이크로서비스 API 타입별 분류
Case A: 마이크로서비스가 REST API
Robot Service: GET /robots/{id}
Telemetry Service: GET /telemetry/robots/{id}/latest
Alert Service: GET /alerts/robots/{id}
→ 우리 프로젝트가 이 케이스
Case B: 마이크로서비스가 GraphQL API
Robot Service: query { robot(id: "123") { name } }
Telemetry Service: query { telemetry(robotId: "123") { battery } }
Alert Service: query { alerts(robotId: "123") { message } }

2. Gateway 선택지별 정리
Gateway 종류용도마이크로서비스 타입예시REST GatewayREST → REST 라우팅RESTNginx, Kong, FastAPIGraphQL ServerGraphQL → REST 호출RESTApollo Server, StrawberryGraphQL FederationGraphQL → GraphQL 통합GraphQLApollo Router, Apollo Gateway

3. 각 케이스별 상세 설명
📌 Case 1: REST Gateway + REST Services
Client → REST Gateway (FastAPI) → REST Services
구조:
python# FastAPI Gateway
@app.get("/api/fleet/dashboard")
async def fleet_dashboard():
    robots = await http_client.get("http://robot-service/robots")
    telemetry = await http_client.get("http://telemetry-service/...")
    alerts = await http_client.get("http://alert-service/...")
    return aggregate(robots, telemetry, alerts)
```

**특징:**
- ✅ 간단함
- ❌ N+1 문제 수동 해결 필요
- ❌ Over-fetching 해결 불가
- **용도:** 단순 라우팅, 레거시 통합

---

### 📌 Case 2: GraphQL Server + REST Services (★ 우리 케이스)
```
Client → GraphQL Gateway → REST Services
              (Apollo or Strawberry)
구조 (Strawberry):
python@strawberry.type
class Query:
    @strawberry.field
    async def fleet_dashboard(self) -> FleetDashboard:
        robots = await fetch_robots()  # REST 호출
        return FleetDashboard(robots=robots)

@strawberry.type
class Robot:
    id: str
    name: str
    
    @strawberry.field
    async def latest_telemetry(self) -> Telemetry:
        # DataLoader로 배치 처리
        return await telemetry_loader.load(self.id)
```

**특징:**
- ✅ N+1 문제 자동 해결 (DataLoader)
- ✅ Over-fetching 해결 (클라이언트가 필드 선택)
- ✅ 단일 엔드포인트
- **용도:** REST를 GraphQL로 래핑, N+1 최적화

**Apollo vs Strawberry 비교:**
| | Apollo Server | Strawberry |
|---|---|---|
| 언어 | Node.js/TypeScript | Python |
| 스키마 정의 | SDL (Schema First) | 데코레이터 (Code First) |
| 설치 | `npm install @apollo/server` | `pip install strawberry-graphql` |
| 백엔드 통합 | Express, Fastify | FastAPI, Django |
| DataLoader | 별도 설치 필요 | 내장 |
| 모니터링 | Apollo Studio (무료) | 수동 (Prometheus) |

---

### 📌 Case 3: GraphQL Federation + GraphQL Services
```
Client → Apollo Router → Subgraph 1 (Apollo Server) → Service 1
                      → Subgraph 2 (Apollo Server) → Service 2
                      → Subgraph 3 (Apollo Server) → Service 3
구조:
typescript// Robot Subgraph
const typeDefs = gql`
  type Robot @key(fields: "id") {
    id: ID!
    name: String!
  }
`;

// Telemetry Subgraph (Robot 확장)
const typeDefs = gql`
  extend type Robot @key(fields: "id") {
    id: ID! @external
    latestTelemetry: Telemetry
  }
`;

// Apollo Router가 이 둘을 자동으로 합침
```

**특징:**
- ✅ 각 팀이 독립적으로 스키마 관리
- ✅ 스키마 자동 통합
- ⚠️ 모든 서비스가 GraphQL이어야 함
- ⚠️ 복잡도 높음 (Subgraph마다 Apollo Server 필요)
- **용도:** 대규모 조직, 팀별 GraphQL 서비스

---

## 4. 우리 프로젝트 경우의 수

### Option A: REST만 (베이스라인)
```
Client → FastAPI Gateway → REST Services
```
- 성능 비교 대상
- N+1 문제 그대로 발생

---

### Option B: Strawberry (추천 ⭐)
```
Client → Strawberry + FastAPI → REST Services
python# main.py
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
import strawberry

app = FastAPI()

@strawberry.type
class Query:
    @strawberry.field
    async def robots(self) -> list[Robot]:
        return await fetch_robots_from_rest()

schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")
```

**장점:**
- Python 단일 언어
- FastAPI와 완벽 통합
- 러닝커브 낮음
- DataLoader 내장

---

### Option C: Apollo Server
```
Client → Apollo Server (Node.js) → REST Services
typescript// server.ts
import { ApolloServer } from '@apollo/server';
import { startStandaloneServer } from '@apollo/server/standalone';

const typeDefs = `#graphql
  type Query {
    robots: [Robot]
  }
  type Robot {
    id: ID!
    name: String!
  }
`;

const resolvers = {
  Query: {
    robots: async () => {
      const response = await fetch('http://robot-service:8001/robots');
      return response.json();
    }
  }
};

const server = new ApolloServer({ typeDefs, resolvers });
const { url } = await startStandaloneServer(server);
```

**장점:**
- Apollo Studio 무료 모니터링
- 강력한 생태계
- TypeScript 타입 안정성

**단점:**
- Node.js 추가 필요
- 백엔드와 언어 분리

---

### Option D: Apollo Federation (과잉)
```
Client → Apollo Router 
           → Robot Subgraph (Apollo) → Robot Service (GraphQL)
           → Telemetry Subgraph (Apollo) → Telemetry Service (GraphQL)
           → Alert Subgraph (Apollo) → Alert Service (GraphQL)
```

**문제점:**
- 마이크로서비스를 GraphQL로 다시 만들어야 함
- 각 서비스마다 Apollo Server 추가
- **완전히 불필요한 복잡도**

---

## 5. 최종 추천 구조

### 🎯 추천 아키텍처
```
┌─────────────────────────────────────────────┐
│            Performance Test Client           │
└─────────────────────────────────────────────┘
         │                      │
         ▼                      ▼
┌──────────────────┐  ┌──────────────────┐
│  REST Endpoint   │  │ GraphQL Endpoint │
│                  │  │                  │
│  FastAPI         │  │  Strawberry      │
│  /api/rest/*     │  │  /graphql        │
└──────────────────┘  └──────────────────┘
         │                      │
         └──────────┬───────────┘
                    ▼
        ┌───────────────────────┐
        │   Microservices       │
        │                       │
        │  Robot Service :8001  │
        │  Telemetry Service    │
        │  Alert Service        │
        │                       │
        │  (모두 FastAPI REST)  │
        └───────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │      PostgreSQL       │
        └───────────────────────┘

6. 정리표
구성 요소REST 버전GraphQL 버전GatewayFastAPI /api/rest/*Strawberry /graphql스키마 정의OpenAPI (자동)GraphQL Schema (데코레이터)N+1 해결수동 (배치 쿼리 직접 구현)DataLoader (자동)Over-fetching전체 응답필드 선택 가능마이크로서비스FastAPI (동일)FastAPI (동일)데이터베이스PostgreSQL (동일)PostgreSQL (동일)

7. 구현 순서

마이크로서비스 3개 구현 (FastAPI REST)

Robot Service
Telemetry Service
Alert Service


REST Gateway 구현 (FastAPI)

3개 클라이언트 API 구현
N+1 문제 그대로 두기


GraphQL Gateway 구현 (Strawberry)

동일한 3개 API를 GraphQL로
DataLoader로 N+1 해결


성능 테스트

Locust / k6로 부하 테스트
내부 호출 횟수 비교
응답 시간 비교




이제 명확해?

Apollo Federation은 우리한테 불필요
Strawberry로 GraphQL Gateway만 만들면 됨
마이크로서비스는 그냥 REST로 유지

구현 시작할까?그럼 스트로베리쓰고 뒷단 서비스는 레스트면 그래프큐엘을 왜 쓰는거지?2월 4일아 핵심 질문이다! 이게 많이 헷갈리는 부분이야.

왜 뒷단이 REST인데 GraphQL을 쓰냐?
문제 상황 재확인
플릿 대시보드 API 호출:
Client: "15대 로봇 정보 + 각각의 최신 텔레메트리 + 알람 줘"

Case 1: REST Gateway (현재)
클라이언트 → Gateway 통신:
httpGET /api/fleet/dashboard
Gateway → 마이크로서비스 통신 (내부):
python# Gateway 내부 로직
async def fleet_dashboard():
    robots = await get("http://robot-service/robots")  # 1번
    
    result = []
    for robot in robots:  # 15대
        # N+1 문제!
        tele = await get(f"http://telemetry-service/robots/{robot.id}/latest")  # 15번
        alerts = await get(f"http://alert-service/robots/{robot.id}")  # 15번
        result.append({
            "robot": robot,
            "telemetry": tele,
            "alerts": alerts
        })
    return result

# 총 내부 호출: 1 + 15 + 15 = 31번
문제점:

Gateway가 반복문으로 서비스를 여러 번 호출
N+1 문제를 수동으로 해결해야 함 (배치 쿼리 직접 구현)


Case 2: GraphQL Gateway (Strawberry)
클라이언트 → Gateway 통신:
graphqlquery {
  fleetDashboard {
    robots {
      id
      name
      latestTelemetry { battery }
      activeAlerts { message }
    }
  }
}
Gateway → 마이크로서비스 통신 (내부):
pythonfrom strawberry.dataloader import DataLoader

# DataLoader 정의
async def load_telemetry(robot_ids: list[str]):
    # 한번에 배치 조회!
    response = await post(
        "http://telemetry-service/batch-query",
        json={"robot_ids": robot_ids}
    )
    return response.json()

telemetry_loader = DataLoader(load_fn=load_telemetry)

# GraphQL 리졸버
@strawberry.type
class Robot:
    id: str
    name: str
    
    @strawberry.field
    async def latest_telemetry(self) -> Telemetry:
        # DataLoader가 자동으로 배치 처리!
        # 15개 요청을 모아서 한번에 호출
        return await telemetry_loader.load(self.id)

# 총 내부 호출: 1(robots) + 1(telemetry batch) + 1(alerts batch) = 3번

핵심 차이: DataLoader의 마법
REST Gateway - 순진한 반복문
pythonfor robot in robots:  # 15번 반복
    tele = await call_service(robot.id)  # 매번 네트워크 호출
GraphQL Gateway - 똑똑한 배치 처리
python# DataLoader가 내부에서 자동으로:
# 1. 여러 개의 load(robot.id) 요청을 수집 (버퍼링)
# 2. 이벤트 루프의 다음 틱에서 한번에 처리
# 3. 배치 API 호출: [id1, id2, ..., id15]
# 4. 결과를 각 요청자에게 분배
```

---

## 비유로 설명

### 🏪 편의점 배달 (REST Gateway)
```
손님 15명이 각자 "물 1개씩 주문"

배달원이 15번 왕복:
- 1번째: A에게 물 배달
- 2번째: B에게 물 배달
- ...
- 15번째: O에게 물 배달

총 15번 배달
```

### 🚚 대형마트 배달 (GraphQL DataLoader)
```
손님 15명이 각자 "물 1개씩 주문"

배달원이 잠깐 기다렸다가:
- "아 15명이 주문했네? 한번에 모아서 배달하자"
- 트럭에 물 15개 싣고 한번에 배달

총 1번 배달

실제 코드로 명확하게 비교
REST Gateway 구현
python@app.get("/api/fleet/dashboard")
async def fleet_dashboard():
    robots = await http.get("http://robot-service/robots")
    
    # 😭 이렇게 하면 N+1
    for robot in robots:
        robot["telemetry"] = await http.get(
            f"http://telemetry-service/robots/{robot['id']}/latest"
        )
    
    # ✅ 이렇게 해야 최적화 (수동)
    robot_ids = [r["id"] for r in robots]
    telemetry_map = await http.post(
        "http://telemetry-service/batch-query",
        json={"robot_ids": robot_ids}
    )
    for robot in robots:
        robot["telemetry"] = telemetry_map[robot["id"]]
    
    return robots
→ 배치 처리를 개발자가 직접 구현해야 함

GraphQL Gateway 구현
python# DataLoader 한번만 정의
telemetry_loader = DataLoader(load_fn=load_telemetry_batch)

@strawberry.type
class Robot:
    id: str
    
    @strawberry.field
    async def latest_telemetry(self) -> Telemetry:
        # 그냥 load 호출만 하면 끝
        # DataLoader가 알아서 배치 처리
        return await telemetry_loader.load(self.id)
→ 배치 처리가 자동으로 됨

추가 이점
1. Over-fetching 해결
REST:
json// 클라이언트가 로봇 이름만 필요해도 전체 데이터 전송
{
  "id": "robot-001",
  "name": "Robot-A",
  "model": "AGV-X200",          // 불필요
  "location": "Building-3",     // 불필요
  "firmware_version": "v2.3.1", // 불필요
  "status": "active"            // 불필요
}
GraphQL:
graphql# 필요한 것만 요청
query {
  robots {
    name  # 이것만 전송됨
  }
}

2. Under-fetching 해결
REST:
httpGET /api/robots           # 1번 - 로봇 목록
GET /api/users/me         # 2번 - 내 정보
GET /api/alerts/active    # 3번 - 활성 알람

클라이언트가 3번 호출해야 함
GraphQL:
graphqlquery {
  robots { name }
  me { email }
  activeAlerts { message }
}

클라이언트가 1번만 호출
```

---

## 그래서 답은?

### GraphQL을 쓰는 이유 (뒷단이 REST여도)

| 문제 | REST Gateway | GraphQL Gateway |
|------|-------------|----------------|
| **N+1 문제** | 수동 해결 (복잡) | DataLoader 자동 해결 |
| **Over-fetching** | 항상 전체 전송 | 필요한 필드만 |
| **Under-fetching** | 여러 번 호출 | 한번에 해결 |
| **클라이언트 유연성** | 고정된 응답 | 쿼리로 제어 |

---

## 결론

**GraphQL Gateway는:**
- ❌ 마이크로서비스를 GraphQL로 바꾸는 게 아니라
- ✅ REST 마이크로서비스를 **똑똑하게 조합**하는 계층

**쉽게 말하면:**
```
REST 서비스: "재료 창고" (개별 데이터 제공)
GraphQL Gateway: "똑똑한 셰프" (효율적으로 조합해서 요리)
이제 이해됐어? GraphQL은 뒷단 API 호출을 최적화하려고 쓰는 거야!

** User **
그럼 아폴로라우터랑 스트로베리랑 좀 겹치는거지?

** AI System **
아! 정확한 질문이야. 근데 겹치지 않아. 완전히 다른 용도야.

Apollo Router vs Strawberry
StrawberryApollo Router역할GraphQL 서버 (실행 엔진)GraphQL 게이트웨이 (라우터)입력GraphQL 쿼리 받음GraphQL 쿼리 받음출력REST API 호출해서 응답다른 GraphQL 서버들 호출해서 통합비유요리사 (재료를 요리)음식점 총괄 매니저 (여러 요리사 관리)

구체적인 차이
Strawberry (GraphQL Server)
Client → Strawberry
           ↓
        [GraphQL 쿼리 실행]
           ↓
        REST API 호출
           ↓
        Robot Service (REST)
        Telemetry Service (REST)
        Alert Service (REST)
Strawberry가 하는 일:
python@strawberry.type
class Query:
    @strawberry.field
    async def robot(self, id: str) -> Robot:
        # 직접 REST API 호출
        response = await http.get(f"http://robot-service/robots/{id}")
        return Robot(**response.json())
```

→ **GraphQL 쿼리를 받아서 REST로 변환**

---

### Apollo Router (Federation Gateway)
```
Client → Apollo Router
           ↓
        [쿼리 분석 및 분해]
           ↓
        여러 GraphQL Subgraph로 분산
           ↓
        Robot Subgraph (GraphQL)
        Telemetry Subgraph (GraphQL)
        Alert Subgraph (GraphQL)
           ↓
        [응답 통합]
           ↓
        Client에게 반환
```

**Apollo Router가 하는 일:**
```
클라이언트 쿼리:
query {
  robot(id: "123") {
    name              # → Robot Subgraph로
    latestTelemetry { # → Telemetry Subgraph로
      battery
    }
  }
}

Apollo Router 내부:
1. 쿼리 분석: "아, robot.name은 Robot Subgraph, telemetry는 Telemetry Subgraph"
2. 각 Subgraph에 쿼리 전송 (GraphQL → GraphQL)
3. 응답 조합해서 클라이언트에 반환
```

→ **GraphQL을 여러 GraphQL로 분산하고 통합**

---

## 핵심 차이: 뒷단이 뭐냐?

| Gateway | 뒷단 서비스 타입 | 통신 방식 |
|---------|----------------|----------|
| **Strawberry** | REST API | GraphQL → REST 변환 |
| **Apollo Router** | GraphQL API | GraphQL → GraphQL 라우팅 |

---

## 시각적 비교

### Strawberry 아키텍처 (우리 프로젝트)
```
┌─────────┐
│ Client  │
└────┬────┘
     │ GraphQL Query
     ▼
┌──────────────────┐
│   Strawberry     │ ◄── 이게 "GraphQL Server"
│  (GraphQL 실행)  │     리졸버에서 직접 REST 호출
└────┬─────────────┘
     │ HTTP REST
     ▼
┌──────────────────┐
│ Robot Service    │ REST API
│ Telemetry Service│ REST API
│ Alert Service    │ REST API
└──────────────────┘
```

---

### Apollo Router 아키텍처 (Federation)
```
┌─────────┐
│ Client  │
└────┬────┘
     │ GraphQL Query
     ▼
┌──────────────────┐
│  Apollo Router   │ ◄── 이게 "Gateway" (라우터)
│  (쿼리 분산기)    │     GraphQL을 GraphQL로 라우팅만
└────┬─────────────┘
     │ GraphQL (Federation Protocol)
     ▼
┌──────────────────┐
│ Robot Subgraph   │ ◄── 이것도 GraphQL Server (Apollo Server)
│  (Apollo Server) │     Robot Service(REST) 호출
└──────────────────┘
┌──────────────────┐
│ Telemetry Sub    │ ◄── 이것도 GraphQL Server
│  (Apollo Server) │     Telemetry Service(REST) 호출
└──────────────────┘
→ Apollo Router 뒤에도 결국 GraphQL Server가 있음!

실제 코드 비교
Strawberry 방식 (1개 서버)
python# 전체가 하나의 서버
from strawberry.fastapi import GraphQLRouter

@strawberry.type
class Query:
    @strawberry.field
    async def robot(self, id: str) -> Robot:
        # 여기서 직접 REST 호출
        data = await fetch_from_rest_api(f"/robots/{id}")
        return Robot(**data)
    
    @strawberry.field
    async def telemetry(self, robot_id: str) -> Telemetry:
        # 여기서 직접 REST 호출
        data = await fetch_from_rest_api(f"/telemetry/{robot_id}")
        return Telemetry(**data)

schema = strawberry.Schema(query=Query)
app = FastAPI()
app.include_router(GraphQLRouter(schema), prefix="/graphql")
→ 하나의 서버에서 모든 타입 처리

Apollo Federation 방식 (여러 서버)
Robot Subgraph (별도 서버 1):
typescript// 포트 4001
const typeDefs = gql`
  type Robot @key(fields: "id") {
    id: ID!
    name: String!
  }
  
  type Query {
    robot(id: ID!): Robot
  }
`;

const resolvers = {
  Query: {
    robot: (_, { id }) => {
      // 여기서 Robot Service(REST) 호출
      return fetch(`http://robot-service/robots/${id}`);
    }
  }
};
Telemetry Subgraph (별도 서버 2):
typescript// 포트 4002
const typeDefs = gql`
  extend type Robot @key(fields: "id") {
    id: ID! @external
    latestTelemetry: Telemetry
  }
  
  type Telemetry {
    battery: Float
  }
`;

const resolvers = {
  Robot: {
    latestTelemetry: (robot) => {
      // 여기서 Telemetry Service(REST) 호출
      return fetch(`http://telemetry-service/robots/${robot.id}/latest`);
    }
  }
};
Apollo Router (통합):
yaml# router.yaml
supergraph:
  subgraphs:
    robot:
      url: http://localhost:4001
    telemetry:
      url: http://localhost:4002
```

→ **여러 GraphQL 서버를 Router가 통합**

---

## 언제 뭘 쓰나?

### Strawberry 쓸 때 (우리 케이스)
```
✅ 마이크로서비스가 REST
✅ 단일 팀이 전체 관리
✅ 간단한 구조 원함
✅ Python 백엔드
```

**장점:**
- 간단함 (서버 1개)
- 빠른 개발
- 운영 복잡도 낮음

---

### Apollo Router 쓸 때
```
✅ 마이크로서비스가 이미 GraphQL
✅ 여러 팀이 각자 스키마 관리
✅ 스키마 자동 통합 필요
✅ 대규모 조직
```

**장점:**
- 팀별 독립 개발
- 스키마 자동 병합
- 확장성 높음

**단점:**
- 복잡함 (서버 N+1개)
- 운영 부담
- 마이크로서비스를 GraphQL로 만들어야 함

---

## 비유로 정리

### Strawberry
```
혼자 하는 식당
- 셰프 1명이 모든 요리 담당
- 재료 창고(REST 서비스)에서 재료 가져와서 요리
- 간단하고 효율적
```

### Apollo Router + Subgraphs
```
푸드코트
- 각 매장(Subgraph)이 GraphQL로 메뉴 제공
- 총괄 데스크(Router)가 주문 분산
- 각 매장도 결국 재료 창고(REST)에서 재료 가져옴
- 복잡하지만 규모 확장에 유리

최종 정리
질문답변Strawberry랑 Apollo Router 겹쳐?❌ 완전히 다른 역할Strawberry는?GraphQL 서버 (REST 호출)Apollo Router는?GraphQL 게이트웨이 (GraphQL 통합)우리 프로젝트는?Strawberry만 필요Apollo Router 필요한 경우?마이크로서비스가 GraphQL일 때

한 문장 요약:
Strawberry는 "GraphQL 요리사" (REST를 GraphQL로 변환)
Apollo Router는 "푸드코트 관리자" (여러 GraphQL을 통합)
이제 명확해? 우리는 Strawberry만 쓰면 돼!

** User **
그그럼 다시한번 경우의수들을 줘봐...솔루션마다 정의나 용도를 먼저 정의한다음에... 코드는 안보여줘도 괜찮고, 레이어별로 호출그런거만 좀 알려줘봐. 그림 많이 그리지말고 -> 이런 화살표이용해서 플로우만 그리고

** AI System **
좋아, 깔끔하게 정리해줄게.


솔루션별 정의 및 용도
1. REST Gateway
정의: HTTP REST 엔드포인트로 요청을 받아 REST 마이크로서비스를 호출하는 라우터
용도: 단순 프록시, API 통합, 인증/로깅 추가
예시: Nginx, Kong, FastAPI

2. GraphQL Server (Strawberry, Apollo Server)
정의: GraphQL 쿼리를 실행하고 리졸버에서 직접 데이터 소스(REST/DB)를 호출하는 서버
용도: REST를 GraphQL로 래핑, N+1 문제 해결, Over-fetching 방지
예시: Strawberry, Apollo Server, GraphQL Yoga

3. GraphQL Federation Gateway (Apollo Router)
정의: 여러 GraphQL 서버(Subgraph)의 스키마를 통합하고 쿼리를 분산/라우팅하는 게이트웨이
용도: 대규모 조직에서 팀별 독립 GraphQL 서비스 통합
예시: Apollo Router, Apollo Gateway

아키텍처 비교
Case A: REST Gateway + REST Services
Client 
  → REST Gateway (FastAPI)
    → Robot Service (REST)
    → Telemetry Service (REST)
    → Alert Service (REST)
특징:

Gateway에서 N+1 수동 해결 필요
클라이언트는 항상 고정된 응답 받음


Case B: GraphQL Server + REST Services (★ 추천)
Client 
  → GraphQL Server (Strawberry or Apollo Server)
    → Robot Service (REST)
    → Telemetry Service (REST)
    → Alert Service (REST)
특징:

DataLoader로 N+1 자동 해결
클라이언트가 필요한 필드만 요청 가능
서버 1개로 모든 타입 관리


Case C: GraphQL Federation
Client 
  → Apollo Router
    → Robot Subgraph (Apollo Server)
      → Robot Service (REST)
    → Telemetry Subgraph (Apollo Server)
      → Telemetry Service (REST)
    → Alert Subgraph (Apollo Server)
      → Alert Service (REST)
특징:

각 Subgraph가 독립적인 GraphQL 서버
Router가 쿼리를 분해해서 각 Subgraph로 라우팅
팀별 스키마 독립 관리 가능
복잡도 매우 높음


내부 호출 흐름 비교
플릿 대시보드 조회 (15대 로봇)
Case A: REST Gateway
Client → GET /api/fleet/dashboard

Gateway 내부:
  → GET /robots (1번)
  → GET /robots/1/telemetry (1번)
  → GET /robots/2/telemetry (1번)
  → ... (15번)
  → GET /robots/1/alerts (1번)
  → GET /robots/2/alerts (1번)
  → ... (15번)

총 내부 호출: 31번

Case B: GraphQL Server + DataLoader
Client → POST /graphql (query { fleetDashboard { robots { telemetry alerts } } })

GraphQL Server 내부:
  → GET /robots (1번)
  → DataLoader가 telemetry 요청 15개 수집
    → POST /telemetry/batch (1번, robot_ids=[1,2,...,15])
  → DataLoader가 alerts 요청 15개 수집
    → POST /alerts/batch (1번, robot_ids=[1,2,...,15])

총 내부 호출: 3번

Case C: GraphQL Federation
Client → POST /graphql (query { fleetDashboard { robots { telemetry alerts } } })

Apollo Router 내부:
  1. 쿼리 분석
  2. Subgraph별 쿼리 생성
  
  → Robot Subgraph: query { robots { id name } }
    Robot Subgraph 내부:
      → GET /robots (1번)
  
  → Telemetry Subgraph: query { _entities(representations: [...]) { telemetry } }
    Telemetry Subgraph 내부:
      → POST /telemetry/batch (1번)
  
  → Alert Subgraph: query { _entities(representations: [...]) { alerts } }
    Alert Subgraph 내부:
      → POST /alerts/batch (1번)
  
  3. 응답 병합

총 내부 호출: 3번 (하지만 GraphQL 서버 3개 필요)

솔루션별 장단점
REST Gateway
장점:

단순함
레거시 통합 쉬움

단점:

N+1 수동 해결
Over-fetching 불가피
클라이언트가 여러 엔드포인트 호출 필요


GraphQL Server (Strawberry/Apollo Server)
장점:

N+1 자동 해결
단일 엔드포인트
클라이언트 유연성
서버 1개로 충분

단점:

GraphQL 러닝커브
REST 대비 복잡도 증가


GraphQL Federation
장점:

팀별 독립 개발
스키마 자동 통합
대규모 확장성

단점:

매우 높은 복잡도
운영 부담 (서버 N+1개)
모든 서비스를 GraphQL로 변환 필요
소규모 프로젝트에 과잉


선택 가이드
상황추천 솔루션마이크로서비스가 REST, 단일 팀GraphQL Server (Strawberry)마이크로서비스가 REST, 단순 프록시만 필요REST Gateway마이크로서비스가 GraphQL, 여러 팀GraphQL Federation성능 테스트 목적REST Gateway + GraphQL Server 비교

우리 프로젝트 최종 구조
Performance Test:

Client
  → REST Endpoint (/api/rest/*)
    → Robot Service (REST)
    → Telemetry Service (REST)
    → Alert Service (REST)

Client
  → GraphQL Endpoint (/graphql)
    → Robot Service (REST)
    → Telemetry Service (REST)
    → Alert Service (REST)

비교 포인트:
- REST: 31번 내부 호출
- GraphQL: 3번 내부 호출 (DataLoader)

이제 명확해? Federation은 우리한테 완전히 불필요하고, Strawberry vs REST Gateway 비교만 하면 돼!그럼 저 기준으로 아키텍쳐를 두벌만들고, 각각 도커들을 다 띄어야겠지? 근데 뒷단이 다 레스트서버인거면 공용으로 사용해도 되지 않아? 앞단이 다른거지?2월 4일완전 정확해! 뒷단 마이크로서비스는 공용으로 쓰면 돼.

아키텍처 구성
┌─────────────────────────────────────────────┐
│          Performance Test Client             │
└─────────────────────────────────────────────┘
         │                      │
         ▼                      ▼
┌──────────────────┐  ┌──────────────────┐
│  REST Gateway    │  │ GraphQL Gateway  │
│  (FastAPI)       │  │ (Strawberry)     │
│  Port 8000       │  │ Port 8100        │
└──────────────────┘  └──────────────────┘
         │                      │
         └──────────┬───────────┘
                    ▼
        ┌───────────────────────┐
        │   공용 마이크로서비스   │
        │                       │
        │  Robot Service :8001  │
        │  Telemetry Service    │
        │  :8002                │
        │  Alert Service :8003  │
        └───────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │      PostgreSQL       │
        │         :5432         │
        └───────────────────────┘

Docker Compose 구성
필요한 컨테이너 (총 6개)

rest-gateway (Port 8000)
graphql-gateway (Port 8100)
robot-service (Port 8001) ← 공용
telemetry-service (Port 8002) ← 공용
alert-service (Port 8003) ← 공용
postgres (Port 5432) ← 공용


호출 흐름
REST 테스트
Client 
  → http://localhost:8000/api/fleet/dashboard
    → http://robot-service:8001/robots
    → http://telemetry-service:8002/robots/1/latest
    → http://telemetry-service:8002/robots/2/latest
    → ...
GraphQL 테스트
Client 
  → http://localhost:8100/graphql
    → http://robot-service:8001/robots
    → http://telemetry-service:8002/batch-query (robot_ids=[1,2,...])
    → http://alert-service:8003/batch-query (robot_ids=[1,2,...])
뒷단 서비스는 동일하게 호출됨!

핵심 포인트
공용으로 쓰는 이유
✅ REST 마이크로서비스는 HTTP API만 제공 (누가 호출하든 상관없음)
✅ 성능 비교가 공정함 (같은 뒷단 호출)
✅ 리소스 절약 (중복 컨테이너 불필요)
✅ 데이터베이스도 공유 (동일한 데이터로 테스트)
분리하는 것
✅ REST Gateway와 GraphQL Gateway만 별도 컨테이너
✅ 각자 다른 포트로 리스닝
✅ 성능 테스트 시 각각 측정

마이크로서비스 요구사항
뒷단 서비스들이 배치 조회 API를 제공해야 함:
Robot Service
GET /robots          # 전체 목록
GET /robots/{id}     # 단건 조회
Telemetry Service
GET /telemetry/robots/{id}/latest      # 단건 조회
POST /telemetry/batch-query            # 배치 조회 (GraphQL용)
  Body: { "robot_ids": ["1", "2", ...] }
Alert Service
GET /alerts/robots/{id}     # 단건 조회
POST /alerts/batch-query    # 배치 조회 (GraphQL용)
  Body: { "robot_ids": ["1", "2", ...] }
REST Gateway는 단건 API만 여러 번 호출
GraphQL Gateway는 배치 API 한번만 호출

성능 테스트 방식
동시에 두 Gateway 테스트
bash# REST Gateway 부하 테스트
locust -f test_rest.py --host=http://localhost:8000

# GraphQL Gateway 부하 테스트 (별도 터미널)
locust -f test_graphql.py --host=http://localhost:8100
측정 항목

응답 시간 (REST vs GraphQL)
뒷단 서비스 호출 횟수 (중요!)
네트워크 트래픽
CPU/메모리 사용량


추가 고려사항
관찰 가능성 (Observability)
공용 마이크로서비스에 로깅 추가하면:
python@app.get("/robots/{id}")
async def get_robot(id: str):
    logger.info(f"Called by: {request.headers.get('X-Gateway-Type')}")  # REST or GraphQL
    return robot_data
이렇게 하면 어느 Gateway에서 얼마나 호출했는지 추적 가능!

최종 확인
네 말이 100% 맞아:

✅ 뒷단 마이크로서비스는 공용
✅ Gateway만 두 벌 (REST, GraphQL)
✅ 데이터베이스도 공용
✅ 성능 비교는 Gateway 레벨에서

Docker Compose 시작하면:
bashdocker-compose up

Running containers:
- rest-gateway (8000)
- graphql-gateway (8100)
- robot-service (8001) ← 공용
- telemetry-service (8002) ← 공용
- alert-service (8003) ← 공용
- postgres (5432) ← 공용
이 구조로 갈까?

** User **
그럼 좀 공평하게 레스트 게이트웨이가  콩게이트웨이 그런거 써야하는거 아니야?

** AI System **
아 좋은 지적이야! 공정한 비교를 위한 고민이네.


공평성 이슈
현재 설계
REST Gateway: FastAPI (Python)
GraphQL Gateway: Strawberry + FastAPI (Python)
문제점:

둘 다 FastAPI 기반이면 → 공평함 ✅
하지만 "Gateway 제품" 비교 아닌가?


선택지
Option 1: 둘 다 FastAPI (현재)
REST Gateway: FastAPI로 직접 구현
GraphQL Gateway: Strawberry + FastAPI
공평한가?

✅ 같은 언어/프레임워크
✅ 순수하게 REST vs GraphQL 프로토콜 비교
❌ 프로덕션급 Gateway 기능 부족


Option 2: 전문 Gateway 제품 사용
REST Gateway: Kong / Nginx / Traefik
GraphQL Gateway: Apollo Server / Strawberry
문제점:

Kong은 C/Lua 기반
Apollo는 Node.js 기반
Strawberry는 Python 기반
언어/런타임이 달라서 불공평 ❌


Option 3: 언어 통일 (추천 ⭐)
REST Gateway: FastAPI (직접 구현)
GraphQL Gateway: Strawberry + FastAPI (직접 구현)
이게 가장 공평한 이유:

같은 언어/런타임
같은 HTTP 서버 (uvicorn)
순수하게 REST API 호출 방식 vs GraphQL DataLoader 비교


네가 말한 Kong 같은 걸 쓴다면?
Kong Gateway 추가 시
REST Gateway: Kong (C/Lua, 엔터프라이즈급)
  - Rate limiting
  - Load balancing
  - Service mesh
  - 플러그인 생태계

GraphQL Gateway: Strawberry (Python, 직접 구현)
  - DataLoader만 있음
문제:

Kong이 너무 무거움
기능이 너무 많아서 비교 초점 흐려짐
우리가 비교하려는 건: N+1 해결 능력


공정한 비교를 위한 원칙
우리가 테스트하려는 것
REST 방식의 N+1 문제 
vs 
GraphQL DataLoader의 배치 처리
변수 통제
요소RESTGraphQL통제 여부언어PythonPython✅ 동일프레임워크FastAPIFastAPI✅ 동일HTTP 서버uvicornuvicorn✅ 동일데이터베이스PostgreSQLPostgreSQL✅ 동일마이크로서비스공용공용✅ 동일차이점반복 호출DataLoader🎯 측정 대상

만약 Kong을 쓴다면
공정하게 만들려면
REST Gateway: Kong
GraphQL Gateway: Apollo Router (엔터프라이즈급)
하지만:

Apollo Router는 Federation용 (우리 구조에 안 맞음)
Kong + Apollo Server 조합? (너무 복잡)
결국 FastAPI 수준으로 단순화해야 비교 가능


최종 추천
공정한 비교 구조
┌─────────────────────────────────────────┐
│      Performance Test Client             │
└─────────────────────────────────────────┘
         │                      │
         ▼                      ▼
┌──────────────────┐  ┌──────────────────┐
│  REST Gateway    │  │ GraphQL Gateway  │
│                  │  │                  │
│  FastAPI         │  │  Strawberry      │
│  + uvicorn       │  │  + FastAPI       │
│                  │  │  + uvicorn       │
│  수동 배치처리    │  │  DataLoader      │
└──────────────────┘  └──────────────────┘
핵심:

둘 다 FastAPI 기반
REST Gateway도 최적화된 코드 작성 (배치 API 활용)
순수하게 호출 패턴의 차이만 비교


REST Gateway 최적화 버전
순진한 REST (Naive)
python# N+1 문제 그대로
for robot in robots:
    telemetry = await get(f"/robots/{robot.id}/telemetry")
최적화된 REST (Optimized)
python# 배치 API 활용
robot_ids = [r.id for r in robots]
telemetry_map = await post("/telemetry/batch-query", json={"robot_ids": robot_ids})
```

**이렇게 하면:**
- REST도 3번 호출 가능
- GraphQL과 동일한 성능
- **그럼 GraphQL의 장점이 뭐냐?** → 자동화!

---

## 비교 시나리오

### Test 1: 순진한 구현
```
REST (Naive): 31번 호출
GraphQL (DataLoader): 3번 호출

결과: GraphQL 10배 빠름
```

### Test 2: 둘 다 최적화
```
REST (Optimized): 3번 호출 (수동 배치)
GraphQL (DataLoader): 3번 호출 (자동 배치)

결과: 성능 비슷, 하지만 GraphQL이 코드 간결
```

---

## 결론

### 공정한 비교를 위해:

**✅ 추천: 둘 다 FastAPI**
- 언어/런타임 통일
- 순수 프로토콜 비교
- 두 가지 REST 버전 테스트
  1. Naive REST (반복 호출)
  2. Optimized REST (배치 API)
  3. GraphQL (DataLoader)

**❌ 비추천: Kong 같은 전문 Gateway**
- 변수 너무 많아짐
- 비교 초점 흐려짐
- 오버엔지니어링

---

### 최종 테스트 구조
```
Client
  → REST Naive (FastAPI) - 31번 호출
  → REST Optimized (FastAPI) - 3번 호출 (수동)
  → GraphQL (Strawberry) - 3번 호출 (자동)

측정:
- 성능 (응답 시간)
- 코드 복잡도
- 유지보수성
이렇게 가는 게 어때? Kong은 나중에 프로덕션 적용할 때 고려하고!

** User **
그그래 그럼 다시 한번 정리해줘봐

** AI System **
좋아, 전체를 깔끔하게 정리해줄게.

프로젝트 목표
REST vs GraphQL 성능 비교

마이크로서비스 환경에서 N+1 문제 해결 능력 비교
내부 서비스 호출 횟수 및 응답 시간 측정


전체 아키텍처
┌─────────────────────────────────────────────┐
│          Performance Test Client             │
│              (Locust / k6)                   │
└─────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ REST Naive   │ │ REST         │ │ GraphQL      │
│              │ │ Optimized    │ │              │
│ FastAPI      │ │ FastAPI      │ │ Strawberry   │
│ :8000        │ │ :8001        │ │ + FastAPI    │
│              │ │              │ │ :8100        │
└──────────────┘ └──────────────┘ └──────────────┘
         │              │              │
         └──────────────┼──────────────┘
                        ▼
            ┌───────────────────────┐
            │   공용 마이크로서비스   │
            │                       │
            │  Robot Service :8001  │
            │  Telemetry Service    │
            │  :8002                │
            │  Alert Service :8003  │
            │                       │
            │  (모두 FastAPI REST)  │
            └───────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │      PostgreSQL       │
            │         :5432         │
            └───────────────────────┘

마이크로서비스 구성 (공용)
1. Robot Service (:8001)
역할: 로봇 메타데이터 관리
API:
GET  /robots           - 전체 로봇 목록
GET  /robots/{id}      - 로봇 단건 조회
데이터:
- id: 로봇 ID
- name: 로봇 이름
- model: 모델명
- location: 위치
- status: 상태

2. Telemetry Service (:8002)
역할: 센서 데이터 및 메트릭
API:
GET  /telemetry/robots/{id}/latest     - 단건 조회
POST /telemetry/batch-query            - 배치 조회
     Body: {"robot_ids": ["1", "2"]}
데이터:
- robot_id: 로봇 ID
- battery_level: 배터리
- cpu_usage: CPU 사용률
- temperature: 온도
- timestamp: 시간

3. Alert Service (:8003)
역할: 알람 및 이벤트 관리
API:
GET  /alerts/robots/{id}               - 단건 조회
POST /alerts/batch-query               - 배치 조회
     Body: {"robot_ids": ["1", "2"]}
데이터:
- id: 알람 ID
- robot_id: 로봇 ID
- type: 알람 타입
- severity: 심각도
- message: 메시지

Gateway 구성 (3개 버전)
1. REST Gateway - Naive (:8000)
구현 방식: 순진한 반복 호출
플릿 대시보드 내부 로직:
1. GET /robots (1번)
2. for each robot (15대):
     - GET /telemetry/robots/{id}/latest (15번)
     - GET /alerts/robots/{id} (15번)

총 31번 호출
목적: 베이스라인, 최악의 경우

2. REST Gateway - Optimized (:8001)
구현 방식: 수동 배치 처리
플릿 대시보드 내부 로직:
1. GET /robots (1번)
2. robot_ids 추출
3. POST /telemetry/batch-query (1번)
4. POST /alerts/batch-query (1번)

총 3번 호출
목적: REST도 최적화하면 빠를 수 있다는 증명

3. GraphQL Gateway (:8100)
구현 방식: DataLoader 자동 배치
플릿 대시보드 내부 로직:
1. GET /robots (1번)
2. DataLoader가 telemetry 요청 자동 수집
   → POST /telemetry/batch-query (1번)
3. DataLoader가 alerts 요청 자동 수집
   → POST /alerts/batch-query (1번)

총 3번 호출 (자동)
목적: GraphQL의 자동 최적화 능력

클라이언트 API (3개)
1. 플릿 대시보드
목적: N+1 문제 극대화
요청:
REST: GET /api/fleet/dashboard
GraphQL: query { fleetDashboard { robots { name latestTelemetry { battery } activeAlerts { message } } } }
응답 데이터:

15대 로봇 정보
각 로봇의 최신 텔레메트리
각 로봇의 활성 알람

내부 호출:
REST Naive: 31번
REST Optimized: 3번
GraphQL: 3번

2. 로봇 상세 모니터링
목적: 1:1 관계 (N+1 없음)
요청:
REST: GET /api/robots/{id}/monitor
GraphQL: query { robot(id: "123") { name latestTelemetry { battery } recentAlerts { message } } }
응답 데이터:

로봇 기본 정보
최신 텔레메트리
최근 알람 5개

내부 호출:
REST Naive: 3번
REST Optimized: 3번
GraphQL: 3번
차이: 없음 (공정한 비교)

3. 크리티컬 알람 조회
목적: N+1 문제 발생
요청:
REST: GET /api/alerts/critical
GraphQL: query { criticalAlerts { message robot { name } telemetrySnapshot { battery } } }
응답 데이터:

심각도 critical 알람 10개
각 알람의 로봇 정보
발생 시점 텔레메트리

내부 호출:
REST Naive: 21번 (1 + 10 + 10)
REST Optimized: 3번
GraphQL: 3번

Docker Compose 구성
컨테이너 목록 (총 7개):
1. rest-naive-gateway     (Port 8000)
2. rest-optimized-gateway (Port 8001)
3. graphql-gateway        (Port 8100)
4. robot-service          (Port 8001) - 공용
5. telemetry-service      (Port 8002) - 공용
6. alert-service          (Port 8003) - 공용
7. postgres               (Port 5432) - 공용

데이터베이스 스키마
sql-- robots
id, name, model, location, status, created_at

-- telemetry_data
id, robot_id, timestamp, battery_level, cpu_usage, temperature

-- alerts
id, robot_id, type, severity, message, status, created_at
```

**초기 데이터:**
- 로봇 15대
- 각 로봇당 텔레메트리 100개 (시계열)
- 각 로봇당 알람 5~10개

---

## 성능 테스트 시나리오

### 테스트 도구
- Locust 또는 k6

### 테스트 케이스
**1. 동시 사용자 100명**
- 플릿 대시보드 반복 조회
- 30초간 지속

**2. 측정 항목**
- 응답 시간 (평균, P95, P99)
- 처리량 (RPS)
- **마이크로서비스 호출 횟수** (중요!)
- CPU/메모리 사용량

**3. 비교 대상**
```
REST Naive vs REST Optimized vs GraphQL
```

---

## 예상 결과

### 응답 시간 (예측)
```
REST Naive:      ~500ms (31번 호출)
REST Optimized:  ~100ms (3번 호출)
GraphQL:         ~100ms (3번 호출)
```

### 코드 복잡도
```
REST Naive:      간단 (비효율)
REST Optimized:  복잡 (수동 배치 로직)
GraphQL:         간단 (DataLoader 자동)
결론

성능: Optimized REST ≈ GraphQL
생산성: GraphQL > REST (자동화)
유지보수: GraphQL > REST (선언적)


기술 스택 정리
계층REST NaiveREST OptimizedGraphQL마이크로서비스언어PythonPythonPythonPython프레임워크FastAPIFastAPIFastAPIFastAPIHTTP 서버uvicornuvicornuvicornuvicornGraphQL--Strawberry-데이터베이스---PostgreSQLORM---SQLAlchemy

구현 순서
Phase 1: 마이크로서비스

Robot Service
Telemetry Service (+ 배치 API)
Alert Service (+ 배치 API)
초기 데이터 세팅

Phase 2: Gateway

REST Naive Gateway
REST Optimized Gateway
GraphQL Gateway (Strawberry + DataLoader)

Phase 3: 테스트

단위 테스트 (각 API 검증)
통합 테스트 (전체 플로우)
성능 테스트 (Locust)
결과 분석 및 리포트