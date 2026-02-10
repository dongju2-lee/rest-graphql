/**
 * K6 Test Script for Case 2: Strawberry GraphQL Gateway
 * Tests schema stitching with GraphQL queries
 */

import http from 'k6/http';
import { check, group } from 'k6';
import { getOptions, selectScenario, randomRobotId } from './common.js';

export const options = getOptions();

const BASE_URL = __ENV.GATEWAY_URL || 'http://localhost:10000';
const GRAPHQL_ENDPOINT = `${BASE_URL}/graphql`;

const headers = {
  'Content-Type': 'application/json',
};

// GraphQL query for fleet dashboard
const FLEET_QUERY = JSON.stringify({
  query: `
    query FleetDashboard {
      fleetDashboard {
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
    }
  `,
});

// GraphQL query for robot monitor
function getRobotMonitorQuery(robotId) {
  return JSON.stringify({
    query: `
      query RobotMonitor($id: String!) {
        robotMonitor(id: $id) {
          robot {
            id
            name
            status
            model
            location
          }
          telemetry {
            batteryLevel
            cpuUsage
            temperature
            timestamp
          }
          recentAlerts {
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

// GraphQL query for critical alerts
const CRITICAL_QUERY = JSON.stringify({
  query: `
    query CriticalAlerts {
      criticalAlerts {
        id
        message
        robot {
          name
          location
        }
        telemetrySnapshot {
          batteryLevel
          cpuUsage
          temperature
        }
      }
    }
  `,
});

export default function () {
  const scenario = selectScenario();

  if (scenario === 'fleet_dashboard') {
    // Fleet Dashboard with GraphQL
    group('fleet_dashboard', function () {
      const res = http.post(GRAPHQL_ENDPOINT, FLEET_QUERY, { headers });
      check(res, {
        'status is 200': (r) => r.status === 200,
        'has data': (r) => {
          try {
            const body = JSON.parse(r.body);
            return body.data && body.data.fleetDashboard && body.data.fleetDashboard.robots;
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
    // Robot Monitor with GraphQL
    group('robot_monitor', function () {
      const robotId = randomRobotId();
      const res = http.post(GRAPHQL_ENDPOINT, getRobotMonitorQuery(robotId), { headers });
      check(res, {
        'status is 200': (r) => r.status === 200,
        'has data': (r) => {
          try {
            const body = JSON.parse(r.body);
            return body.data && body.data.robotMonitor;
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
    // Critical Alerts with GraphQL
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
