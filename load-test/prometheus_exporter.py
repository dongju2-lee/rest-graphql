"""
Prometheus metrics exporter for Locust.
Exposes metrics on port 9646 for Prometheus scraping.
"""

import os
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from locust import events

# Prometheus metrics
REQUESTS_TOTAL = Counter(
    'locust_requests_total',
    'Total number of requests',
    ['method', 'name', 'result']
)

RESPONSE_TIME = Histogram(
    'locust_response_times',
    'Response time in milliseconds',
    ['method', 'name'],
    buckets=[10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
)

USERS = Gauge(
    'locust_users',
    'Current number of users'
)

FAILURES_TOTAL = Counter(
    'locust_failures_total',
    'Total number of failures',
    ['method', 'name', 'exception']
)

# Track if server is started
_server_started = False


def start_prometheus_server(port=9646):
    """Start prometheus HTTP server on specified port."""
    global _server_started
    if not _server_started:
        try:
            start_http_server(port)
            _server_started = True
            print(f"Prometheus metrics available on port {port}")
        except OSError as e:
            print(f"Could not start prometheus server: {e}")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Track request metrics."""
    if exception:
        REQUESTS_TOTAL.labels(method=request_type, name=name, result='failure').inc()
        FAILURES_TOTAL.labels(
            method=request_type,
            name=name,
            exception=type(exception).__name__
        ).inc()
    else:
        REQUESTS_TOTAL.labels(method=request_type, name=name, result='success').inc()

    RESPONSE_TIME.labels(method=request_type, name=name).observe(response_time)


@events.spawning_complete.add_listener
def on_spawning_complete(user_count, **kwargs):
    """Update user count when spawning completes."""
    USERS.set(user_count)


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Start prometheus server when test starts."""
    port = int(os.environ.get('PROMETHEUS_PORT', 9646))
    start_prometheus_server(port)


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """Reset users when test ends."""
    USERS.set(0)
