# Monitoring & Performance Testing Guide

이 문서는 모니터링 인프라 설정 및 k6 성능 테스트 실행 방법을 설명합니다.

## 디렉토리 구조

```
graph-rest-preform/
├── monitoring/
│   ├── prometheus.yml                          # Prometheus 설정
│   └── grafana/
│       ├── provisioning/
│       │   ├── datasources/prometheus.yml      # Grafana 데이터소스
│       │   └── dashboards/dashboard.yml        # 대시보드 프로비저닝
│       └── dashboards/
│           └── k6-performance.json             # K6 성능 비교 대시보드
├── scripts/
│   ├── infra-up.sh          # 인프라 시작 (Postgres, Prometheus, Grafana)
│   ├── infra-down.sh        # 인프라 종료
│   ├── case1-rest.sh        # Case 1: REST Gateway 시작
│   ├── case2-strawberry.sh  # Case 2: Strawberry GraphQL 시작
│   ├── case3-apollo.sh      # Case 3: Apollo Router 시작
│   ├── case-stop.sh         # Case 서비스 종료 (인프라는 유지)
│   ├── k6-duration.sh       # K6 duration 모드 테스트
│   ├── k6-iterations.sh     # K6 iterations 모드 테스트
│   ├── seed.sh              # 시드 데이터 삽입
│   └── cleanup.sh           # 전체 정리 (볼륨, 이미지 포함)
└── k6/
    ├── common.js            # 공통 설정 및 유틸리티
    ├── case1-rest.js        # REST Gateway 테스트
    ├── case2-strawberry.js  # Strawberry GraphQL 테스트
    ├── case3-apollo.js      # Apollo Router 테스트
    └── results/             # 테스트 결과 저장 디렉토리
```

## 사전 준비

스크립트에 실행 권한을 부여하세요:

```bash
chmod +x scripts/*.sh
```

## 워크플로우

### 1. 인프라 시작

```bash
./scripts/infra-up.sh
```

이 스크립트는 다음을 수행합니다:
- PostgreSQL, Prometheus, Grafana 컨테이너 시작
- PostgreSQL 헬스체크 대기
- 시드 데이터 삽입 (15개 로봇, 각 로봇당 100개 텔레메트리, 5-10개 알림)

접속 정보:
- Grafana: http://localhost:13000 (admin/admin)
- Prometheus: http://localhost:19090
- PostgreSQL: localhost:15432

### 2. Case 서비스 시작

각 케이스를 순차적으로 테스트하려면:

```bash
# Case 1: REST Gateway
./scripts/case1-rest.sh

# Case 2: Strawberry GraphQL
./scripts/case2-strawberry.sh

# Case 3: Apollo Router (Federation)
./scripts/case3-apollo.sh
```

모든 경우 게이트웨이는 http://localhost:10000 에서 실행됩니다.

### 3. K6 성능 테스트 실행

#### Duration 모드 (시간 기반)

```bash
# 기본값: 2 VU, 10초
./scripts/k6-duration.sh --case 1

# 커스텀 설정
./scripts/k6-duration.sh --case 1 --vus 5 --duration 30s
./scripts/k6-duration.sh --case 2 --vus 10 --duration 1m
./scripts/k6-duration.sh --case 3 --vus 20 --duration 2m
```

#### Iterations 모드 (반복 횟수 기반)

```bash
# 기본값: 2 VU, 100 iterations
./scripts/k6-iterations.sh --case 1

# 커스텀 설정
./scripts/k6-iterations.sh --case 2 --vus 5 --iterations 200
./scripts/k6-iterations.sh --case 3 --vus 10 --iterations 500
```

### 4. Grafana 대시보드 확인

1. http://localhost:13000 접속
2. "K6 Performance Comparison" 대시보드 선택
3. `testid` 레이블로 케이스별 비교 가능:
   - `case1-duration` / `case1-iterations`
   - `case2-duration` / `case2-iterations`
   - `case3-duration` / `case3-iterations`

대시보드 패널:
- **RPS**: 초당 요청 수 (Requests Per Second)
- **Response Time P95**: 95 백분위 응답 시간
- **Response Time P50**: 중간값 응답 시간
- **Total Requests**: 총 요청 수
- **Error Rate**: 에러율 (임계값: 0.05 = 5%)
- **Active VUs**: 활성 가상 사용자 수

### 5. Case 서비스 종료

```bash
# Case 서비스만 종료 (인프라는 유지)
./scripts/case-stop.sh

# 인프라까지 모두 종료
./scripts/infra-down.sh
```

### 6. 완전 정리

```bash
# 모든 컨테이너, 볼륨, 이미지, 네트워크 삭제
./scripts/cleanup.sh
```

## K6 테스트 시나리오

모든 케이스는 동일한 비율로 3가지 시나리오를 실행합니다:

- **Fleet Dashboard (50%)**: 전체 로봇 목록 + 각 로봇의 최신 텔레메트리 + 활성 알림
  - REST: 심각한 N+1 문제 발생 (1 + 15*2 = 31 쿼리)
  - GraphQL: 배칭 및 최적화 가능

- **Robot Monitor (30%)**: 특정 로봇의 상세 정보 + 텔레메트리 히스토리 + 최근 알림
  - 단일 엔티티 조회이므로 케이스 간 차이 작음

- **Critical Alerts (20%)**: 심각도가 'critical'인 알림 목록 + 로봇 정보 + 텔레메트리 스냅샷
  - 크로스 서비스 조인 성능 비교

## 성능 비교 포인트

### Case 1: REST Gateway (N+1 문제)
- Fleet Dashboard에서 최대 31개 DB 쿼리 발생
- 각 로봇마다 개별 텔레메트리 및 알림 조회
- **예상**: 가장 느린 응답 시간, 낮은 RPS

### Case 2: Strawberry GraphQL (Schema Stitching)
- DataLoader를 통한 배칭 가능
- 단일 GraphQL 쿼리로 여러 서비스 데이터 조합
- **예상**: 중간 수준 성능

### Case 3: Apollo Router (Federation)
- 각 서브그래프가 독립적으로 최적화 가능
- Federation 라우터의 쿼리 플래닝 및 배칭
- **예상**: 가장 빠른 응답 시간, 높은 RPS

## 예제 비교 워크플로우

```bash
# 1. 인프라 시작
./scripts/infra-up.sh

# 2. Case 1 테스트
./scripts/case1-rest.sh
./scripts/k6-duration.sh --case 1 --vus 10 --duration 1m
./scripts/case-stop.sh

# 3. Case 2 테스트
./scripts/case2-strawberry.sh
./scripts/k6-duration.sh --case 2 --vus 10 --duration 1m
./scripts/case-stop.sh

# 4. Case 3 테스트
./scripts/case3-apollo.sh
./scripts/k6-duration.sh --case 3 --vus 10 --duration 1m
./scripts/case-stop.sh

# 5. Grafana에서 결과 비교
# http://localhost:13000 -> K6 Performance Comparison 대시보드

# 6. 정리
./scripts/infra-down.sh
```

## 트러블슈팅

### PostgreSQL 연결 실패
```bash
# PostgreSQL 헬스체크
docker compose -f docker-compose.base.yml exec postgres pg_isready -U fleet

# 로그 확인
docker compose -f docker-compose.base.yml logs postgres
```

### 시드 데이터 재생성
```bash
./scripts/seed.sh
```

### Prometheus 메트릭 미수집
```bash
# Prometheus targets 확인
curl http://localhost:19090/api/v1/targets

# k6 experimental-prometheus-rw 출력 확인
# k6 실행 시 표준 출력에 메트릭 전송 로그가 표시됩니다
```

### Grafana 대시보드 미표시
```bash
# Grafana 프로비저닝 로그 확인
docker compose -f docker-compose.base.yml logs grafana

# 대시보드 디렉토리 권한 확인
ls -la monitoring/grafana/dashboards/
```

## 성능 테스트 기본 설정 이유

기본값이 2 VU, 10초로 매우 낮게 설정된 이유:
- **환경 호환성**: 성능이 낮은 개발 환경에서도 실행 가능
- **빠른 검증**: 빠르게 설정 및 워크플로우 검증 가능
- **점진적 확장**: 기본값으로 시작해서 점진적으로 부하 증가

프로덕션 수준 테스트를 위해서는:
```bash
./scripts/k6-duration.sh --case 1 --vus 50 --duration 5m
./scripts/k6-duration.sh --case 2 --vus 100 --duration 10m
```

## 메트릭 수집 주기

- Prometheus scrape interval: 5초
- Grafana refresh: 5초
- k6 메트릭 전송: 실시간 (experimental-prometheus-rw)

## 참고사항

- 모든 스크립트는 프로젝트 루트에서 실행되어야 합니다
- Docker 네트워크 `fleet-net`이 자동으로 생성됩니다
- 각 케이스는 동일한 포트(10000)를 사용하므로 동시 실행 불가
- k6 결과는 Prometheus에 실시간으로 전송되며 Grafana에서 시각화됩니다
