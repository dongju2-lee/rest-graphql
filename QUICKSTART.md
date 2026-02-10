# Quick Start Guide

프로젝트를 빠르게 시작하고 성능 비교를 수행하는 가이드입니다.

## 준비사항

1. Docker 및 Docker Compose 설치
2. k6 설치 (https://k6.io/docs/get-started/installation/)
3. 스크립트 실행 권한 부여:

```bash
chmod +x scripts/*.sh
```

## 5분 만에 시작하기

### 1단계: 인프라 시작 (1분)

```bash
./scripts/infra-up.sh
```

출력 예시:
```
Starting infrastructure services...
Waiting for PostgreSQL to be ready...
PostgreSQL is ready!
Running seed data...
Seeded: 15 robots, 1500 telemetry, 120 alerts

✓ Infrastructure ready!
  Grafana:    http://localhost:13000 (admin/admin)
  Prometheus: http://localhost:19090
  PostgreSQL: localhost:15432
```

### 2단계: Case 1 테스트 (2분)

```bash
# REST Gateway 시작
./scripts/case1-rest.sh

# k6 테스트 실행
./scripts/k6-duration.sh --case 1 --vus 10 --duration 30s
```

### 3단계: Case 2 테스트 (2분)

```bash
# Case 1 종료
./scripts/case-stop.sh

# Strawberry GraphQL 시작
./scripts/case2-strawberry.sh

# k6 테스트 실행
./scripts/k6-duration.sh --case 2 --vus 10 --duration 30s
```

### 4단계: Grafana에서 결과 확인

1. 브라우저에서 http://localhost:13000 접속
2. "K6 Performance Comparison" 대시보드 선택
3. `testid` 필터로 `case1-duration`과 `case2-duration` 비교

### 5단계: 정리

```bash
./scripts/case-stop.sh
./scripts/infra-down.sh
```

## 전체 3-Case 비교

```bash
# 인프라 시작
./scripts/infra-up.sh

# Case 1: REST
./scripts/case1-rest.sh
./scripts/k6-duration.sh --case 1 --vus 10 --duration 1m
./scripts/case-stop.sh

# Case 2: Strawberry
./scripts/case2-strawberry.sh
./scripts/k6-duration.sh --case 2 --vus 10 --duration 1m
./scripts/case-stop.sh

# Case 3: Apollo Router
./scripts/case3-apollo.sh
./scripts/k6-duration.sh --case 3 --vus 10 --duration 1m
./scripts/case-stop.sh

# Grafana에서 결과 비교
# http://localhost:13000

# 정리
./scripts/infra-down.sh
```

## 유용한 명령어

### 헬스체크

```bash
# Gateway
curl http://localhost:10000/health

# Prometheus
curl http://localhost:19090/-/healthy

# PostgreSQL
docker compose -f docker-compose.base.yml exec postgres pg_isready -U fleet
```

### 로그 확인

```bash
# 모든 로그
docker compose -f docker-compose.base.yml logs -f

# 특정 서비스
docker compose -f docker-compose.case1.yml logs -f rest-gateway
docker compose -f docker-compose.case2.yml logs -f strawberry-gateway
docker compose -f docker-compose.case3.yml logs -f apollo-router
```

### 시드 데이터 재생성

```bash
./scripts/seed.sh
```

### 완전 정리 (볼륨, 이미지 포함)

```bash
./scripts/cleanup.sh
```

## 성능 테스트 팁

### 부하 레벨별 테스트

```bash
# 가벼운 부하 (개발 환경)
./scripts/k6-duration.sh --case 1 --vus 2 --duration 10s

# 중간 부하
./scripts/k6-duration.sh --case 1 --vus 10 --duration 1m

# 높은 부하
./scripts/k6-duration.sh --case 1 --vus 50 --duration 5m

# 스트레스 테스트
./scripts/k6-duration.sh --case 1 --vus 100 --duration 10m
```

### Iterations 모드

특정 횟수의 요청으로 성능 비교:

```bash
./scripts/k6-iterations.sh --case 1 --vus 10 --iterations 1000
./scripts/k6-iterations.sh --case 2 --vus 10 --iterations 1000
./scripts/k6-iterations.sh --case 3 --vus 10 --iterations 1000
```

## 문제 해결

### "Permission denied" 에러

```bash
chmod +x scripts/*.sh
```

### "Network fleet-net not found"

```bash
docker network create fleet-net
```

### "Port already in use"

```bash
# 다른 서비스 종료
./scripts/case-stop.sh

# 또는 특정 포트 사용 프로세스 확인
lsof -i :10000
```

### PostgreSQL 연결 실패

```bash
# 컨테이너 재시작
docker compose -f docker-compose.base.yml restart postgres

# 로그 확인
docker compose -f docker-compose.base.yml logs postgres
```

## 다음 단계

- 상세 문서: [MONITORING.md](MONITORING.md)
- 프로젝트 개요: [README.md](README.md)
- 아키텍처 가이드: [docs/](docs/)

## 주요 URL 요약

| 서비스 | URL |
|---------|-----|
| Grafana | http://localhost:13000 (admin/admin) |
| Prometheus | http://localhost:19090 |
| Gateway (모든 Case) | http://localhost:10000 |
| PostgreSQL | localhost:15432 (fleet/fleet123) |
