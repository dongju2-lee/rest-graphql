/**
 * Common k6 configuration and utilities
 */

/**
 * Generate k6 options based on test mode and environment variables
 * @returns {object} k6 options configuration
 */
export function getOptions() {
  const testMode = __ENV.TEST_MODE || 'duration';
  const vus = parseInt(__ENV.VUS || '2');
  const caseNum = __ENV.CASE || '1';

  const baseOptions = {
    thresholds: {
      http_req_duration: ['p(95)<2000'],
      http_req_failed: ['rate<0.05'],
    },
  };

  if (testMode === 'duration') {
    return {
      ...baseOptions,
      vus: vus,
      duration: __ENV.DURATION || '10s',
      tags: {
        testid: `case${caseNum}-duration`,
      },
    };
  } else if (testMode === 'iterations') {
    return {
      ...baseOptions,
      vus: vus,
      iterations: parseInt(__ENV.ITERATIONS || '100'),
      tags: {
        testid: `case${caseNum}-iterations`,
      },
    };
  }

  throw new Error(`Unknown TEST_MODE: ${testMode}`);
}

/**
 * Select a random scenario based on weighted probability
 * Fleet: 50%, Monitor: 30%, Critical: 20%
 * @returns {string} scenario name
 */
export function selectScenario() {
  const rand = Math.random();

  if (rand < 0.5) {
    return 'fleet_dashboard';
  } else if (rand < 0.8) {
    return 'robot_monitor';
  } else {
    return 'critical_alerts';
  }
}

/**
 * Generate a random robot ID
 * @returns {string} robot ID in format 'robot-XXX'
 */
export function randomRobotId() {
  const num = Math.floor(Math.random() * 15) + 1;
  return `robot-${String(num).padStart(3, '0')}`;
}
