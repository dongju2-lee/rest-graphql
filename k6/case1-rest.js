/**
 * K6 Test Script for Case 1: REST Gateway
 * Tests the N+1 query problem with traditional REST endpoints
 */

import http from 'k6/http';
import { check, group } from 'k6';
import { getOptions, selectScenario, randomRobotId } from './common.js';

export const options = getOptions();

const BASE_URL = __ENV.GATEWAY_URL || 'http://localhost:10000';

export default function () {
  const scenario = selectScenario();

  if (scenario === 'fleet_dashboard') {
    // Fleet Dashboard - maximum N+1 problem exposure
    // This endpoint will make 1 query for robots + N queries for each robot's data
    group('fleet_dashboard', function () {
      const res = http.get(`${BASE_URL}/api/fleet/dashboard`);
      check(res, {
        'status is 200': (r) => r.status === 200,
        'has robots data': (r) => {
          try {
            const body = JSON.parse(r.body);
            return Array.isArray(body) && body.length > 0;
          } catch (e) {
            return false;
          }
        },
      });
    });
  } else if (scenario === 'robot_monitor') {
    // Robot Monitor - single robot details
    group('robot_monitor', function () {
      const robotId = randomRobotId();
      const res = http.get(`${BASE_URL}/api/robots/${robotId}/monitor`);
      check(res, {
        'status is 200': (r) => r.status === 200,
        'has robot data': (r) => {
          try {
            const body = JSON.parse(r.body);
            return body.id === robotId;
          } catch (e) {
            return false;
          }
        },
      });
    });
  } else {
    // Critical Alerts - cross-service aggregation
    group('critical_alerts', function () {
      const res = http.get(`${BASE_URL}/api/alerts/critical`);
      check(res, {
        'status is 200': (r) => r.status === 200,
        'has alerts data': (r) => {
          try {
            const body = JSON.parse(r.body);
            return Array.isArray(body);
          } catch (e) {
            return false;
          }
        },
      });
    });
  }
}
