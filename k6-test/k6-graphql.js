/**
 * k6 Load Test for GraphQL API
 * 
 * 정확한 요청 수로 GraphQL 성능 측정
 * 
 * 실행:
 *   k6 run --out experimental-prometheus-rw k6-graphql.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';

// 커스텀 메트릭
const graphqlRequests = new Counter('graphql_requests_total');
const graphqlErrors = new Counter('graphql_errors_total');
const graphqlDuration = new Trend('graphql_duration_ms');

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

// GraphQL 엔드포인트
const GRAPHQL_URL = __ENV.GRAPHQL_URL || 'http://apollo-router:4000/';

// 시나리오 1: 간단한 사용자 조회
function simpleQuery() {
  const query = `
    query GetUsers {
      users {
        id
        name
        email
      }
    }
  `;
  
  const payload = JSON.stringify({ query });
  const params = {
    headers: { 'Content-Type': 'application/json' },
    tags: { scenario: 'simple_query' },
  };
  
  const start = Date.now();
  const res = http.post(GRAPHQL_URL, payload, params);
  const duration = Date.now() - start;
  
  graphqlRequests.add(1);
  graphqlDuration.add(duration);
  
  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'has data': (r) => JSON.parse(r.body).data !== undefined,
  });
  
  if (!success) {
    graphqlErrors.add(1);
  }
}

// 시나리오 2: 사용자와 로봇 조회 (Cross-service)
function userWithRobots() {
  const userId = Math.floor(Math.random() * 100) + 1;
  const query = `
    query GetUserWithRobots {
      user(id: "user-${userId}") {
        id
        name
        email
        robots {
          id
          name
          status
          battery
        }
      }
    }
  `;
  
  const payload = JSON.stringify({ query });
  const params = {
    headers: { 'Content-Type': 'application/json' },
    tags: { scenario: 'cross_service' },
  };
  
  const start = Date.now();
  const res = http.post(GRAPHQL_URL, payload, params);
  const duration = Date.now() - start;
  
  graphqlRequests.add(1);
  graphqlDuration.add(duration);
  
  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'has user data': (r) => JSON.parse(r.body).data?.user !== undefined,
  });
  
  if (!success) {
    graphqlErrors.add(1);
  }
}

// 시나리오 3: N+1 문제 테스트 (DataLoader)
function usersWithRobots() {
  const query = `
    query GetUsersWithRobots {
      users {
        id
        name
        robots {
          id
          name
          status
        }
      }
    }
  `;
  
  const payload = JSON.stringify({ query });
  const params = {
    headers: { 'Content-Type': 'application/json' },
    tags: { scenario: 'n_plus_1' },
  };
  
  const start = Date.now();
  const res = http.post(GRAPHQL_URL, payload, params);
  const duration = Date.now() - start;
  
  graphqlRequests.add(1);
  graphqlDuration.add(duration);
  
  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'has users': (r) => JSON.parse(r.body).data?.users?.length > 0,
  });
  
  if (!success) {
    graphqlErrors.add(1);
  }
}

// 시나리오 4: 복잡한 집계
function complexAggregation() {
  const siteId = Math.floor(Math.random() * 5) + 1;
  const query = `
    query GetSiteStats {
      site(id: "site-${siteId}") {
        id
        name
        location
        users {
          id
          name
          robots {
            id
            status
            battery
          }
        }
      }
    }
  `;
  
  const payload = JSON.stringify({ query });
  const params = {
    headers: { 'Content-Type': 'application/json' },
    tags: { scenario: 'complex_aggregation' },
  };
  
  const start = Date.now();
  const res = http.post(GRAPHQL_URL, payload, params);
  const duration = Date.now() - start;
  
  graphqlRequests.add(1);
  graphqlDuration.add(duration);
  
  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'has site': (r) => JSON.parse(r.body).data?.site !== undefined,
  });
  
  if (!success) {
    graphqlErrors.add(1);
  }
}

// 메인 테스트 함수
export default function () {
  // 가중치에 따라 시나리오 선택
  const scenario = Math.random();
  
  if (scenario < 0.4) {
    simpleQuery();         // 40%
  } else if (scenario < 0.7) {
    userWithRobots();      // 30%
  } else if (scenario < 0.9) {
    usersWithRobots();     // 20%
  } else {
    complexAggregation();  // 10%
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
