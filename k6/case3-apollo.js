/**
 * K6 Test Script for Case 3: Apollo Router (Federation)
 * Tests Apollo Federation with distributed GraphQL schema
 */

import http from 'k6/http';
import { check, group } from 'k6';
import { getOptions, selectScenario, randomRobotId } from './common.js';

export const options = getOptions();

const BASE_URL = __ENV.GATEWAY_URL || 'http://localhost:10000';
// Apollo Router serves GraphQL at root path by default
const GRAPHQL_ENDPOINT = `${BASE_URL}`;

const headers = {
  'Content-Type': 'application/json',
};

// GraphQL query for fleet dashboard (Federation style)
const FLEET_QUERY = JSON.stringify({
  query: `
    query FleetDashboard {
      robots {
        id
        name
        status
        latestTelemetry {
          batteryLevel
          cpuUsage
          temperature
        }
        activeAlerts {
          severity
          message
        }
      }
    }
  `,
});

// GraphQL query for robot monitor (Federation style)
function getRobotMonitorQuery(robotId) {
  return JSON.stringify({
    query: `
      query RobotMonitor($id: ID!) {
        robot(id: $id) {
          id
          name
          status
          model
          location
          latestTelemetry {
            batteryLevel
            cpuUsage
            temperature
            timestamp
          }
          activeAlerts {
            severity
            message
            createdAt
          }
        }
      }
    `,
    variables: {
      id: robotId,
    },
  });
}

// GraphQL query for critical alerts (Federation style)
// Note: Alert type in Federation doesn't have robot/telemetry fields.
// This tests the simpler cross-subgraph query pattern.
const CRITICAL_QUERY = JSON.stringify({
  query: `
    query CriticalAlerts {
      criticalAlerts {
        id
        robotId
        severity
        message
        createdAt
      }
    }
  `,
});

export default function () {
  const scenario = selectScenario();

  if (scenario === 'fleet_dashboard') {
    // Fleet Dashboard via Apollo Router
    group('fleet_dashboard', function () {
      const res = http.post(GRAPHQL_ENDPOINT, FLEET_QUERY, { headers });
      check(res, {
        'status is 200': (r) => r.status === 200,
        'has data': (r) => {
          try {
            const body = JSON.parse(r.body);
            return body.data && body.data.robots && Array.isArray(body.data.robots);
          } catch (e) {
            return false;
          }
        },
        'no errors': (r) => {
          try {
            const body = JSON.parse(r.body);
            return !body.errors;
          } catch (e) {
            return false;
          }
        },
      });
    });
  } else if (scenario === 'robot_monitor') {
    // Robot Monitor via Apollo Router
    group('robot_monitor', function () {
      const robotId = randomRobotId();
      const res = http.post(GRAPHQL_ENDPOINT, getRobotMonitorQuery(robotId), { headers });
      check(res, {
        'status is 200': (r) => r.status === 200,
        'has data': (r) => {
          try {
            const body = JSON.parse(r.body);
            return body.data && body.data.robot;
          } catch (e) {
            return false;
          }
        },
        'no errors': (r) => {
          try {
            const body = JSON.parse(r.body);
            return !body.errors;
          } catch (e) {
            return false;
          }
        },
      });
    });
  } else {
    // Critical Alerts via Apollo Router
    group('critical_alerts', function () {
      const res = http.post(GRAPHQL_ENDPOINT, CRITICAL_QUERY, { headers });
      check(res, {
        'status is 200': (r) => r.status === 200,
        'has data': (r) => {
          try {
            const body = JSON.parse(r.body);
            return body.data && Array.isArray(body.data.criticalAlerts);
          } catch (e) {
            return false;
          }
        },
        'no errors': (r) => {
          try {
            const body = JSON.parse(r.body);
            return !body.errors;
          } catch (e) {
            return false;
          }
        },
      });
    });
  }
}
