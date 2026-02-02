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
./scripts/start-loadtest.sh
```

**Locust 웹 UI:**
- GraphQL: http://localhost:48089
- REST: http://localhost:58089

**테스트 방법:**
1. 브라우저에서 Locust UI 열기
2. 설정 입력:
   - Number of users: 100 (동시 사용자)
   - Spawn rate: 10 (초당 증가)
3. "Start swarming" 클릭
4. Grafana에서 실시간 모니터링

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

---

## 📊 테스트 방법

### GraphQL 테스트 (http://localhost:14000)

브라우저에서 GraphiQL UI를 열고 쿼리를 실행하세요:

```graphql
# 1. 간단한 사용자 조회
query {
  users {
    id
    name
    email
  }
}

# 2. 사용자와 로봇 조회 (Cross-service)
query {
  user(id: "user-1") {
    id
    name
    robots {
      id
      name
      status
    }
  }
}

# 3. N+1 문제 테스트 (DataLoader 사용)
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

### REST 테스트

브라우저에서 Swagger UI를 열고 테스트하세요:
- User Service: http://localhost:28000/docs
- Robot Service: http://localhost:28001/docs
- Site Service: http://localhost:28002/docs

또는 curl 사용:

```bash
# 사용자 목록
curl http://localhost:24000/api/users

# 특정 사용자
curl http://localhost:24000/api/users/user-1

# 로봇 목록
curl http://localhost:24000/api/robots

# 사이트별 사용자
curl http://localhost:24000/api/users/by-site/site-1
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
