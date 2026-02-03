/**
 * k6 Load Test for REST API
 * 
 * 공정한 비교를 위한 MSA 패턴 적용
 * REST: Microservice 내부 통신 (1번 요청)
 * GraphQL: Federation 자동 해결 (1번 요청)
 * 
 * 실행:
 *   k6 run --out experimental-prometheus-rw k6-rest.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';

// 커스텀 메트릭
const restRequests = new Counter('rest_requests_total');
const restErrors = new Counter('rest_errors_total');
const restDuration = new Trend('rest_duration_ms');

// 테스트 옵션 (환경 변수로 설정 가능)
export const options = {
  // 총 요청 수 (환경 변수 K6_ITERATIONS 또는 기본값 10000)
  iterations: __ENV.K6_ITERATIONS || 10000,
  
  // 가상 사용자 수 (환경 변수 K6_VUS 또는 기본값 50)
  vus: __ENV.K6_VUS || 50,
  
  // 최대 실행 시간 (환경 변수 K6_DURATION 또는 기본값 10m)
  duration: __ENV.K6_DURATION || '10m',
  
  // 임계값 (성공 기준)
  thresholds: {
    'http_req_duration': ['p(95)<500'], // 95%가 500ms 이하
    'http_req_failed': ['rate<0.01'],   // 에러율 1% 이하
  },
};

// REST API 엔드포인트
const REST_BASE_URL = __ENV.REST_URL || 'http://nginx-gateway:80';

// 시나리오 1: 간단한 사용자 조회 (Over-fetching test)
function simpleQuery() {
  const params = {
    tags: { scenario: 'simple_query' },
  };
  
  const start = Date.now();
  const res = http.get(`${REST_BASE_URL}/api/users`, params);
  const duration = Date.now() - start;
  
  restRequests.add(1);
  restDuration.add(duration);
  
  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'has users': (r) => JSON.parse(r.body).length > 0,
  });
  
  if (!success) {
    restErrors.add(1);
  }
}

// 시나리오 2: 사용자와 로봇 조회 (MSA 내부 통신)
function userWithRobots() {
  const userId = Math.floor(Math.random() * 100) + 1;
  const params = {
    tags: { scenario: 'cross_service' },
  };
  
  const start = Date.now();
  
  // MSA 패턴: user-service가 robot-service 내부 호출
  // REST: Client → user-service → robot-service (internal) [1 call]
  // GraphQL: Client → Apollo → user-service + robot-service [1 query]
  const res = http.get(`${REST_BASE_URL}/api/users/${userId}/with-robots`, params);
  
  const duration = Date.now() - start;
  restRequests.add(1);  // 1번만!
  restDuration.add(duration);
  
  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'has user': (r) => JSON.parse(r.body).id !== undefined,
    'has robots': (r) => JSON.parse(r.body).robots !== undefined,
  });
  
  if (!success) {
    restErrors.add(1);
  }
}

// 시나리오 3: 로봇과 텔레메트리 (MSA 내부 통신)
function robotsWithTelemetry() {
  const params = {
    tags: { scenario: 'n_plus_1_solved' },
  };
  
  const start = Date.now();
  
  // MSA 패턴: robot-service가 telemetry 내부 호출
  // REST: Client → robot-service (robots + telemetry combined) [1 call]
  // GraphQL: Client → Apollo → robot-service (DataLoader batched) [1 query]
  const res = http.get(`${REST_BASE_URL}/api/robots/with-telemetry`, params);
  
  const duration = Date.now() - start;
  restRequests.add(1);  // 1번만!
  restDuration.add(duration);
  
  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'has robots': (r) => JSON.parse(r.body).length > 0,
  });
  
  if (!success) {
    restErrors.add(1);
  }
}

// 시나리오 4: 복잡한 집계 - Site Dashboard (MSA 내부 통신)
function siteDashboard() {
  const siteId = Math.floor(Math.random() * 5) + 1;
  const params = {
    tags: { scenario: 'complex_aggregation' },
  };
  
  const start = Date.now();
  
  // MSA 패턴: site-service가 robot/user/telemetry 내부 호출
  // REST: Client → site-service → robot/user/telemetry (internal) [1 call]
  // GraphQL: Client → Apollo → site/robot/user (Federation) [1 query]
  const res = http.get(`${REST_BASE_URL}/api/sites/${siteId}/dashboard`, params);
  
  const duration = Date.now() - start;
  restRequests.add(1);  // 1번만!
  restDuration.add(duration);
  
  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'has site': (r) => JSON.parse(r.body).site !== undefined,
  });
  
  if (!success) {
    restErrors.add(1);
  }
}

// 시나리오 5: 로봇 상세 정보 (Full join)
function robotFullDetail() {
  const robotId = Math.floor(Math.random() * 500) + 1;
  const params = {
    tags: { scenario: 'full_join' },
  };
  
  const start = Date.now();
  
  // MSA 패턴: robot-service가 user/site 내부 호출
  // REST: Client → robot-service → user + site (parallel internal) [1 call]
  // GraphQL: Client → Apollo → robot/user/site/telemetry (Federation) [1 query]
  const res = http.get(`${REST_BASE_URL}/api/robots/${robotId}/full`, params);
  
  const duration = Date.now() - start;
  restRequests.add(1);  // 1번만!
  restDuration.add(duration);
  
  const success = check(res, {
    'status is 200': (r) => r.status === 200,
  });
  
  if (!success) {
    restErrors.add(1);
  }
}

// 메인 테스트 함수
export default function () {
  // Locust와 동일한 가중치
  const scenario = Math.random();
  
  if (scenario < 0.375) {
    simpleQuery();           // 37.5% (Locust task(3))
  } else if (scenario < 0.625) {
    userWithRobots();        // 25% (Locust task(2))
  } else if (scenario < 0.75) {
    robotsWithTelemetry();   // 12.5% (Locust task(1))
  } else if (scenario < 0.875) {
    siteDashboard();         // 12.5% (Locust task(1))
  } else {
    robotFullDetail();       // 12.5% (Locust task(1))
  }
  
  // 사용자 간 약간의 대기 시간 (선택적)
  // sleep(0.1);
}

// 테스트 시작 시
export function setup() {
  // Quiet mode - no logs
}

// 테스트 종료 시
export function teardown(data) {
  // Quiet mode - no logs
}
