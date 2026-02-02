# API 설계 상세 (REST vs GraphQL 성능 비교 최적화)

## 🎯 설계 철학

**REST와 GraphQL의 본질적 차이가 극명하게 드러나는 시나리오 설계**

### 핵심 차이점
1. **Over-fetching**: REST는 전체 객체, GraphQL은 필요한 필드만
2. **Under-fetching (N+1)**: REST는 여러 요청, GraphQL은 한 번에
3. **병렬 처리**: REST는 순차/수동, GraphQL은 자동 병렬
4. **Batching**: REST는 수동 구현, GraphQL은 DataLoader 자동
5. **Query Planning**: GraphQL의 오버헤드

---

## 📊 데이터 모델 및 관계

```
┌─────────────┐
│   User      │
│  (100명)    │
│─────────────│
│ id          │
│ name        │ ← 자주 사용
│ email       │ ← 자주 사용
│ role        │ ← 자주 사용
│ phone       │ ← 거의 안 씀 (Over-fetching 테스트용)
│ address     │ ← 거의 안 씀
│ bio         │ ← 거의 안 씀 (1KB 텍스트)
│ avatar_url  │ ← 거의 안 씀
│ site_id     │ → Site FK
└─────────────┘
       ↑
       │ 1:N
       │
┌─────────────┐        ┌─────────────┐
│   Robot     │  N:1   │    Site     │
│  (200대)    │───────→│   (5개)     │
│─────────────│        │─────────────│
│ id          │        │ id          │
│ model       │        │ name        │
│ status      │        │ location    │
│ battery     │        │ area_sqm    │
│ user_id     │ → User │ capacity    │
│ site_id     │ → Site │ address     │
│ last_seen   │        └─────────────┘
│ firmware_v  │
└─────────────┘
       │
       │ 1:N
       ↓
┌─────────────┐
│ Telemetry   │
│  (200개)    │
│─────────────│
│ robot_id    │ → Robot
│ cpu         │
│ memory      │
│ disk        │
│ temp        │
│ errors      │
│ timestamp   │
└─────────────┘
```

---

## 🔧 각 서비스별 API 명세

### 1. User Service

#### REST Endpoints

```python
# 단순 조회
GET /users
→ Response: List[User] (모든 필드 포함, 항상 over-fetching)
→ Latency: 10ms
→ Size: ~50KB (100명 × 500B)

GET /users/{user_id}
→ Response: User (모든 필드 포함)
→ Latency: 5ms
→ Size: ~500B

# 최적화 엔드포인트 (GraphQL 대응용)
GET /users?fields=id,name,email
→ Response: List[User] (선택된 필드만)
→ Latency: 8ms (파싱 오버헤드)
→ Size: ~10KB

# Batching 지원 (N+1 해결용)
POST /users/batch
Body: {"ids": [1, 2, 3, ...]}
→ Response: List[User]
→ Latency: 8ms + (0.1ms × ids 수)
→ 구현 필요: 직접 구현해야 함
```

#### GraphQL Schema

```graphql
type User {
  id: ID!
  name: String!
  email: String!
  role: String!
  phone: String          # 거의 요청 안 함
  address: String        # 거의 요청 안 함
  bio: String            # 1KB, 거의 요청 안 함
  avatarUrl: String      # 거의 요청 안 함
  site: Site             # Federation reference
}

type Query {
  users: [User!]!                    # 10ms
  user(id: ID!): User                # 5ms
}

# DataLoader 자동 batching
# - 여러 user(id) 요청 → 자동으로 묶어서 한 번에
```

---

### 2. Robot Service

#### REST Endpoints

```python
# 기본 조회
GET /robots/{robot_id}
→ Response: Robot (기본 정보만)
→ Latency: 15ms
→ Size: ~200B

GET /robots/site/{site_id}
→ Response: List[Robot] (해당 사이트의 모든 로봇, 보통 40대)
→ Latency: 25ms
→ Size: ~8KB

# Cross-service 조인 (API-2용)
GET /robots/{robot_id}/full
→ Internal calls:
   1. GET /robots/{robot_id} (15ms)
   2. GET /users/{user_id} (5ms) ← 순차 호출
   3. GET /sites/{site_id} (12ms) ← 순차 호출
   4. Merge (2ms)
→ Total: 34ms
→ Size: ~900B (Robot + User + Site 모두 over-fetch)

# N+1 최적화 (API-3용)
GET /robots/site/{site_id}/dashboard
→ Internal calls:
   1. GET /robots/site/{site_id} (25ms) → 40대
   2. POST /users/batch (8ms) ← user_ids 40개 batching
   3. POST /telemetry/batch (15ms) ← robot_ids 40개 batching
   4. Merge (5ms)
→ Total: 53ms
→ Size: ~50KB (40개 로봇 + 운영자 + 텔레메트리)
→ 문제: Batch endpoint를 직접 구현해야 함

# N+1 최악 (비교용)
GET /robots/site/{site_id}/dashboard?naive=true
→ Internal calls:
   1. GET /robots/site/{site_id} (25ms)
   2. For each robot (40번):
      - GET /users/{user_id} (5ms) × 40 = 200ms
      - GET /telemetry/{robot_id} (10ms) × 40 = 400ms
   3. Merge (5ms)
→ Total: 630ms (최악!)
→ Size: 동일 ~50KB
```

#### GraphQL Schema

```graphql
type Robot {
  id: ID!
  model: String!
  status: String!
  battery: Int!
  lastSeen: String!
  firmwareVersion: String!
  
  # Federation: 다른 서비스 참조
  operator: User!            # → User Service (자동 batching!)
  site: Site!                # → Site Service (자동 병렬!)
  telemetry: Telemetry       # → Robot Service (같은 서비스)
}

type Telemetry {
  robotId: ID!
  cpu: Float!
  memory: Float!
  disk: Float!
  temp: Float!
  errors: Int!
  timestamp: String!
}

type Query {
  robot(id: ID!): Robot                      # 15ms
  robotsBySite(siteId: ID!): [Robot!]!       # 25ms
  telemetry(robotId: ID!): Telemetry         # 10ms
}

# DataLoader 자동 batching
# - 40개 robot의 operator 요청 → 자동으로 POST /users/batch
# - 40개 robot의 telemetry 요청 → 자동으로 묶어서 처리
```

---

### 3. Site Service

#### REST Endpoints

```python
GET /sites/{site_id}
→ Response: Site (기본 정보)
→ Latency: 12ms
→ Size: ~150B

POST /sites/batch
Body: {"ids": [1, 2, 3]}
→ Response: List[Site]
→ Latency: 18ms
→ Size: Variable
```

#### GraphQL Schema

```graphql
type Site {
  id: ID!
  name: String!
  location: String!
  areaSqm: Int!
  capacity: Int!
  address: String!
  
  # Federation: 역참조
  robots: [Robot!]!          # → Robot Service
}

type Query {
  site(id: ID!): Site                     # 12ms
  sites: [Site!]!                         # 18ms (5개)
}
```

---

## 🎭 테스트 시나리오 상세

### API-1: Over-fetching 비교 (단순 조회)

#### 목적
- REST의 over-fetching 문제 측정
- Gateway overhead 비교

#### REST 구현
```http
GET /api/v1/users HTTP/1.1
Host: nginx:8080

Response (50KB):
[
  {
    "id": 1,
    "name": "User1",           ← 필요
    "email": "user1@...",      ← 필요
    "role": "operator",        ← 필요
    "phone": "+82...",         ← 불필요 (over-fetch)
    "address": "Seoul...",     ← 불필요 (over-fetch)
    "bio": "Lorem ipsum...",   ← 불필요 1KB (over-fetch)
    "avatarUrl": "https://..." ← 불필요 (over-fetch)
  },
  ...
]
```

#### GraphQL 구현
```graphql
query {
  users {
    id        # 필요한 것만
    name
    email
    role
  }
}

# Response (10KB): 필요한 필드만
```

#### 예상 결과
```
REST:
- Latency: 12ms (10ms service + 2ms NGINX)
- Network: 50KB
- CPU (NGINX): 낮음

GraphQL:
- Latency: 17ms (10ms service + 5ms Router + 2ms parsing)
- Network: 10KB (80% 절감!)
- CPU (Router): 중간 (파싱/검증)

승자: Network 절약 vs Latency → 환경에 따라 다름
```

---

### API-2: Cross-Service Join (병렬 처리 비교)

#### 목적
- REST 순차 호출 vs GraphQL 병렬 처리
- Service-to-service call overhead

#### REST 구현 (순차)
```python
# Robot Service 내부 구현
@app.get("/robots/{robot_id}/full")
async def get_robot_full(robot_id: int):
    # 1. Robot 조회 (15ms)
    robot = await get_robot(robot_id)
    
    # 2. User 조회 (순차, 5ms)
    async with httpx.AsyncClient() as client:
        user = await client.get(f"http://user-service:8000/users/{robot['user_id']}")
    
    # 3. Site 조회 (순차, 12ms)
    async with httpx.AsyncClient() as client:
        site = await client.get(f"http://site-service:8000/sites/{robot['site_id']}")
    
    # 4. Merge (2ms)
    return {**robot, "operator": user, "site": site}

# Total: 15 + 5 + 12 + 2 = 34ms
```

#### REST 구현 (병렬 최적화 - 추가 작업 필요)
```python
@app.get("/robots/{robot_id}/full")
async def get_robot_full_optimized(robot_id: int):
    robot = await get_robot(robot_id)
    
    # 병렬 호출 (직접 구현 필요!)
    async with httpx.AsyncClient() as client:
        user_task = client.get(f"http://user-service:8000/users/{robot['user_id']}")
        site_task = client.get(f"http://site-service:8000/sites/{robot['site_id']}")
        
        user, site = await asyncio.gather(user_task, site_task)
    
    return {**robot, "operator": user, "site": site}

# Total: 15 + max(5, 12) + 2 = 29ms
# 하지만 코드 복잡도 증가!
```

#### GraphQL 구현 (자동 병렬)
```graphql
query {
  robot(id: 42) {
    id
    model
    status
    operator {      # → User Service (자동 병렬!)
      name
      email
    }
    site {          # → Site Service (자동 병렬!)
      name
      location
    }
  }
}

# Apollo Router 자동 처리:
# 1. Robot Subgraph (15ms)
# 2. User + Site Subgraph 병렬 (max(5, 12) = 12ms)
# 3. Stitching (3ms)
# Total: 15 + 12 + 3 = 30ms (자동 최적화!)
```

#### 예상 결과
```
REST (순차):
- Latency: 36ms (34ms + NGINX 2ms)
- 구현: 간단
- 확장성: 나쁨

REST (병렬):
- Latency: 31ms (29ms + NGINX 2ms)
- 구현: 복잡 (asyncio.gather 직접 구현)
- 확장성: 좋음 (하지만 수동)

GraphQL:
- Latency: 35ms (30ms + Router 5ms)
- 구현: 간단 (자동 병렬)
- 확장성: 좋음 (자동)

승자: GraphQL (개발 편의성 + 자동 최적화)
```

---

### API-3: N+1 Problem (Batching 비교)

#### 목적
- N+1 문제 해결 효율성
- REST manual batching vs GraphQL DataLoader

#### REST 구현 (최악 - N+1)
```python
@app.get("/sites/{site_id}/dashboard")
async def get_site_dashboard_naive(site_id: int):
    # 1. 로봇 목록 조회 (25ms) → 40대
    robots = await get_robots_by_site(site_id)
    
    # 2. 각 로봇마다 운영자 조회 (N+1!)
    result = []
    async with httpx.AsyncClient() as client:
        for robot in robots:  # 40번 반복
            # User 조회 (5ms × 40 = 200ms)
            user = await client.get(f"http://user-service:8000/users/{robot['user_id']}")
            
            # Telemetry 조회 (10ms × 40 = 400ms)
            telemetry = await client.get(f"http://localhost:8000/telemetry/{robot['id']}")
            
            result.append({
                **robot,
                "operator": user,
                "telemetry": telemetry
            })
    
    return result

# Total: 25 + 200 + 400 + 5 = 630ms (재앙!)
```

#### REST 구현 (최적화 - Batch 직접 구현)
```python
@app.get("/sites/{site_id}/dashboard")
async def get_site_dashboard_optimized(site_id: int):
    # 1. 로봇 목록 (25ms)
    robots = await get_robots_by_site(site_id)
    
    # 2. IDs 추출
    user_ids = [r["user_id"] for r in robots]      # 40개
    robot_ids = [r["id"] for r in robots]          # 40개
    
    # 3. Batch 호출 (병렬)
    async with httpx.AsyncClient() as client:
        users_task = client.post("http://user-service:8000/users/batch", json=user_ids)
        telemetry_task = client.post("http://localhost:8000/telemetry/batch", json=robot_ids)
        
        users_resp, telemetry_resp = await asyncio.gather(users_task, telemetry_task)
    
    # 4. Dict로 변환
    users_map = {u["id"]: u for u in users_resp.json()}
    telemetry_map = {t["robot_id"]: t for t in telemetry_resp.json()}
    
    # 5. Merge (5ms)
    result = []
    for robot in robots:
        result.append({
            **robot,
            "operator": users_map[robot["user_id"]],
            "telemetry": telemetry_map[robot["id"]]
        })
    
    return result

# Total: 25 + max(8, 15) + 5 = 48ms
# 하지만:
# - Batch endpoint 직접 구현 필요
# - IDs 추출, Dict 변환 등 boilerplate 코드 많음
# - 유지보수 부담
```

#### GraphQL 구현 (DataLoader 자동)
```graphql
query {
  site(id: 1) {
    name
    location
    robots {              # 25ms → 40대
      id
      model
      status
      operator {          # DataLoader 자동 batching!
        name              # 40개 요청 → 자동으로 POST /users/batch
        email
      }
      telemetry {         # DataLoader 자동 batching!
        cpu               # 40개 요청 → 자동으로 묶어서 처리
        memory
      }
    }
  }
}

# Apollo Router + DataLoader:
# 1. Site → Robots (25ms)
# 2. 40개 robot의 operator 요청 감지 → 자동 batching (8ms)
# 3. 40개 robot의 telemetry 요청 감지 → 자동 batching (15ms)
# 4. 병렬 처리: max(8, 15) = 15ms
# 5. Stitching (5ms)
# Total: 25 + 15 + 5 = 45ms (자동!)
```

#### 예상 결과
```
REST (Naive):
- Latency: 632ms (630ms + NGINX 2ms)
- Network: 50KB (하지만 630ms...)
- 구현: 간단하지만 사용 불가

REST (Optimized):
- Latency: 50ms (48ms + NGINX 2ms)
- Network: 50KB
- 구현: 복잡 (batch endpoint + boilerplate)
- 개발 시간: +2시간 (batch endpoint 구현)

GraphQL:
- Latency: 50ms (45ms + Router 5ms)
- Network: 10KB (필요한 필드만)
- 구현: 간단 (DataLoader 자동)
- 개발 시간: +0시간

승자: GraphQL 압승! (자동화 + 개발 생산성)
```

---

### API-4: Complex Aggregation (Query Planning Overhead)

#### 목적
- 복잡한 쿼리에서 GraphQL Query Planning 오버헤드 측정
- High concurrency에서 Router 병목

#### REST 구현
```python
@app.get("/monitoring/overview")
async def get_monitoring_overview():
    async with httpx.AsyncClient() as client:
        # 병렬 호출
        tasks = [
            get_robot_statistics(),           # 40ms (aggregation)
            client.get("http://site-service:8000/sites"),  # 18ms (5개)
            get_top_operators()               # 8ms (상위 10명)
        ]
        
        robot_stats, sites, operators = await asyncio.gather(*tasks)
    
    # Merge (10ms)
    return {
        "totalRobots": robot_stats["total"],
        "activeRobots": robot_stats["active"],
        "siteStats": merge_site_stats(sites, robot_stats),
        "topOperators": operators
    }

# Total: max(40, 18, 8) + 10 = 50ms
# 단순한 orchestration
```

#### GraphQL 구현
```graphql
query {
  monitoringOverview {
    totalRobots              # → Robot Service
    activeRobots             # → Robot Service
    siteStats {              # → Robot + Site (복잡한 조인)
      siteId
      siteName
      robotCount
      avgBattery
      criticalAlerts
    }
    topOperators {           # → User + Robot (복잡한 조인)
      userId
      name
      robotsManaged
    }
  }
}

# Apollo Router:
# 1. Query Planning (8ms) ← 복잡한 쿼리 분석, 최적화 계획
# 2. Robot aggregation (40ms)
# 3. Site data (18ms) ┐ 병렬
# 4. User data (8ms)  ┘
# 5. Stitching/Merge (12ms) ← 복잡한 조인
# Total: 8 + 40 + 18 + 12 = 78ms

# High concurrency에서:
# - Query Planning이 CPU intensive
# - 100 users: Router CPU 90%+
# - Planning cache hit로 완화 가능
```

#### 예상 결과
```
Low Load (50 users):
- REST: 52ms (50ms + NGINX 2ms)
- GraphQL: 83ms (78ms + Router 5ms)
- 승자: REST (단순 aggregation 유리)

High Load (500 users):
- REST: 70ms (orchestration 안정적)
- GraphQL: 150ms (Query Planning 병목, Router CPU 100%)
- 승자: REST (Planning overhead 축적)

결론:
- 복잡한 aggregation + High concurrency → REST 유리
- Query Plan cache 활성화 시 → GraphQL도 개선 가능
```

---

## 📐 전체 아키텍처 다이어그램

### REST Architecture

```
[Client/Locust]
       ↓ HTTP
┌──────────────────┐
│  NGINX Gateway   │ (2ms overhead)
└────────┬─────────┘
         │
    ┌────┴────┬─────────┬────────┐
    ↓         ↓         ↓         ↓
┌────────┐ ┌────────┐ ┌────────┐
│  User  │ │ Robot  │ │  Site  │
│Service │ │Service │ │Service │
└────────┘ └───┬────┘ └────────┘
               │
         ┌─────┴─────┐
         ↓           ↓
    HTTP call   HTTP call
    (순차 or 병렬은 직접 구현)

API-2 (Cross-service):
Robot Service → User Service (httpx)
               → Site Service (httpx)
순차: 15 + 5 + 12 = 32ms
병렬: 15 + max(5,12) = 27ms (코드 복잡)
```

### GraphQL Architecture

```
[Client/Locust]
       ↓ HTTP POST
┌─────────────────────┐
│  Apollo Router      │ (5ms overhead + Query Planning)
│  - Query Planning   │
│  - DataLoader       │
│  - Auto Batching    │
│  - Auto Parallel    │
└──────┬──────────────┘
       │ Federation Protocol
    ┌──┴───┬────────┬────────┐
    ↓      ↓        ↓         ↓
┌────────┐ ┌────────┐ ┌────────┐
│  User  │ │ Robot  │ │  Site  │
│Subgraph│ │Subgraph│ │Subgraph│
└────────┘ └────────┘ └────────┘

API-2 (Cross-service):
Router → Robot Subgraph (15ms)
       → User Subgraph (5ms)  ┐ 자동 병렬
       → Site Subgraph (12ms) ┘
Stitching (3ms)
Total: 15 + 12 + 3 = 30ms (자동!)
```

---

## 🎯 최종 테스트 매트릭스

| API | 시나리오 | REST 구현 | GraphQL 구현 | 예상 승자 | 핵심 차이 |
|-----|---------|----------|--------------|----------|----------|
| **API-1** | 단순 조회 (100명 유저) | 전체 필드 (50KB) | 필요 필드만 (10KB) | 환경 의존 | Over-fetching |
| **API-2** | Cross-service (1:N) | 순차 34ms / 병렬 29ms (복잡) | 자동 병렬 30ms | GraphQL | 자동 최적화 |
| **API-3** | N+1 (40대 로봇) | Naive 630ms / Opt 48ms (복잡) | 자동 45ms | GraphQL | DataLoader |
| **API-4** | Aggregation (복잡) | 50ms (단순) | 78ms (Planning) | REST | Query overhead |

### 개발 생산성 비교

| 기능 | REST | GraphQL |
|------|------|---------|
| 병렬 처리 | asyncio.gather 직접 구현 | 자동 |
| Batching | Batch endpoint + boilerplate | DataLoader 자동 |
| 필드 선택 | ?fields 쿼리 파라미터 구현 | 기본 기능 |
| 스키마 문서화 | Swagger 수동 작성 | 자동 생성 |
| **총 개발 시간** | **+4시간** | **기본** |

---

## ✅ 핵심 인사이트

### REST가 유리한 경우
1. ✅ **단순한 CRUD** (API-1)
2. ✅ **높은 처리량 필요** (3000+ RPS)
3. ✅ **복잡한 aggregation** (API-4)
4. ✅ **Gateway overhead 최소화**

### GraphQL이 유리한 경우
1. ✅ **N+1 문제 많음** (API-3) → 자동 batching
2. ✅ **Cross-service join 많음** (API-2) → 자동 병렬
3. ✅ **클라이언트 요구사항 다양** → 필드 선택
4. ✅ **개발 생산성** → 자동화된 최적화

### 하이브리드 전략
- **Public API**: GraphQL (클라이언트 유연성)
- **Internal API**: REST (성능, 단순성)
- **Read-heavy**: GraphQL (batching 효과)
- **Write-heavy**: REST (Planning overhead 없음)
- **Mobile**: GraphQL (Over-fetching 방지)
- **Server-to-Server**: REST/gRPC (오버헤드 최소)

이 설계로 REST와 GraphQL의 **본질적 차이**가 명확히 드러납니다! 🎯
