"""
Locust load test for REST API (NGINX Gateway)

Test scenarios for REST vs GraphQL performance comparison.
Run with: locust -f locustfile_rest.py --host=http://localhost:24000

Architecture: Microservice-style with internal service orchestration.
Each API call is a single HTTP request - services call each other internally,
similar to how GraphQL Federation works.
"""

from locust import HttpUser, task, between
import random

import prometheus_exporter  # noqa: F401


class RestUser(HttpUser):
    """Load test user for REST API"""

    wait_time = between(0.1, 0.5)
    host = "http://localhost:24000"  # NGINX Gateway

    # ============== API-1: Simple Query (Over-fetching test) ==============

    @task(3)
    def get_all_users(self):
        """
        Scenario 1: Simple query
        REST disadvantage: Over-fetching (returns all fields)
        """
        self.client.get("/api/users", name="API-1: Get users (all fields)")

    # ============== API-2: Cross-Service Join ==============

    @task(2)
    def get_user_with_robots(self):
        """
        Scenario 2: Cross-service join (1-hop dependency)
        Microservice orchestration: user-service internally calls robot-service

        REST: Client → user-service → robot-service (internal)  [1 call]
        GraphQL: Client → Apollo → user-service + robot-service  [1 query]
        """
        user_id = random.randint(1, 100)
        self.client.get(
            f"/api/users/{user_id}/with-robots",
            name="API-2: User + robots"
        )

    # ============== API-3: N+1 Problem Test ==============

    @task(1)
    def get_robots_with_telemetry(self):
        """
        Scenario 3: N+1 problem test with telemetry
        Microservice orchestration: robot-service returns embedded telemetry

        REST: Client → robot-service (robots + telemetry combined)  [1 call]
        GraphQL: Client → Apollo → robot-service (DataLoader batched)  [1 query]
        """
        self.client.get(
            "/api/robots/with-telemetry",
            name="API-3: N+1 (robots+telemetry)"
        )

    # ============== API-4: Complex Aggregation (Dashboard) ==============

    @task(1)
    def site_dashboard(self):
        """
        Scenario 4: Complex aggregation (Site Dashboard)
        Microservice orchestration: site-service calls robot/user/telemetry internally

        REST: Client → site-service → robot/user/telemetry (internal)  [1 call]
        GraphQL: Client → Apollo → site/robot/user (Federation)  [1 query]
        """
        site_id = random.randint(1, 5)
        self.client.get(
            f"/api/sites/{site_id}/dashboard",
            name="API-4: Site dashboard"
        )

    # ============== Additional Scenarios ==============

    @task(1)
    def get_single_robot_detail(self):
        """
        Single robot with all relations (cross-service)
        Microservice orchestration: robot-service calls user/site internally

        REST: Client → robot-service → user + site (parallel internal)  [1 call]
        GraphQL: Client → Apollo → robot/user/site/telemetry (Federation)  [1 query]
        """
        robot_id = random.randint(1, 500)
        self.client.get(
            f"/api/robots/{robot_id}/full",
            name="Robot detail (full)"
        )
