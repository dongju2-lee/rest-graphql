# 🚀 빠른 시작 가이드

## 1️⃣ 시스템 시작

```bash
./scripts/quick-start.sh
```

## 2️⃣ 접속

### GraphQL (GraphiQL UI)
```
http://localhost:14000
```
→ Swagger처럼 브라우저에서 테스트 가능!

### REST (Swagger UI)  
```
http://localhost:28000/docs  # User Service
http://localhost:28001/docs  # Robot Service
http://localhost:28002/docs  # Site Service
```

### Grafana (모니터링)
```
http://localhost:33000
ID: admin, PW: admin
```

## 3️⃣ 테스트

```bash
# GraphQL 테스트
./scripts/test-graphql.sh

# REST 테스트
./scripts/test-rest.sh
```

## 4️⃣ 종료

```bash
./scripts/stop-all.sh
```

---

## 💡 예제 쿼리

### GraphQL (브라우저에서 http://localhost:14000)

```graphql
# 간단한 쿼리
{ users { id name email } }

# Cross-service Join
{ 
  user(id: "1") { 
    name 
    robots { name status battery } 
  } 
}

# N+1 문제 테스트 (DataLoader 자동 배치!)
{ users { name robots { name } } }
```

### REST (curl 또는 Swagger UI)

```bash
# 전체 사용자
curl http://localhost:24000/api/users

# 단일 사용자
curl http://localhost:24000/api/users/1

# 사용자의 로봇 (2번 요청 필요!)
curl http://localhost:24000/api/users/1
curl http://localhost:24000/api/robots/by-owner/1
```

---

## ⚠️ 문제 해결

### Docker가 실행되지 않음
```bash
# Docker Desktop 실행 확인
docker info
```

### 포트 충돌
```bash
# 사용 중인 포트 확인
lsof -i :14000
lsof -i :24000

# 기존 컨테이너 중지
./scripts/stop-all.sh
```

### 로그 확인
```bash
docker-compose -f docker-compose.full.yml logs -f
```

---

**준비 완료!** 🎉
