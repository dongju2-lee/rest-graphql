"""
Locust load test for REST API (NGINX Gateway)

Test scenarios for REST vs GraphQL performance comparison.
Run with: locust -f locustfile_rest.py --host=http://localhost:24000
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
        Scenario 2: Cross-service join
        REST disadvantage: Multiple sequential requests
        """
        user_id = random.randint(1, 100)

        # 1. Get user
        self.client.get(f"/api/users/{user_id}", name="API-2a: Get user")

        # 2. Get user's robots
        self.client.get(f"/api/robots/by-owner/{user_id}", name="API-2b: Get robots by owner")

    # ============== API-3: N+1 Problem Test ==============

    @task(1)
    def get_robots_with_telemetry(self):
        """
        Scenario 3: N+1 problem test with telemetry
        REST approach: Batch endpoint for optimization
        GraphQL equivalent: robots { id name status telemetry { cpu memory temperature } }
        """
        # Get all robots
        robots_response = self.client.get("/api/robots", name="API-3a: Get robots")

        if robots_response.status_code == 200:
            robots = robots_response.json()
            robot_ids = [str(r["id"]) for r in robots]

            if robot_ids:
                # Batch telemetry call for ALL robots (same as GraphQL)
                self.client.get(
                    f"/api/telemetry/batch?ids={','.join(robot_ids)}",
                    name="API-3b: Batch telemetry (all)"
                )

    # ============== API-4: Complex Aggregation (Dashboard) ==============

    @task(1)
    def site_dashboard(self):
        """
        Scenario 4: Complex aggregation (Site Dashboard)
        REST approach: Single optimized endpoint with internal orchestration
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
        GraphQL equivalent: robot { id name model status battery owner { name email } site { name location } telemetry { cpu memory disk temperature } }
        REST requires 3 calls to get same data
        """
        robot_id = random.randint(1, 500)

        # 1. Get robot + owner
        robot_response = self.client.get(
            f"/api/robots/{robot_id}/with-owner",
            name="Robot detail: robot+owner"
        )

        # 2. Get telemetry
        self.client.get(
            f"/api/telemetry/{robot_id}",
            name="Robot detail: telemetry"
        )

        # 3. Get site (site_id is in robot response)
        if robot_response.status_code == 200:
            site_id = robot_response.json().get("site_id", 1)
            self.client.get(
                f"/api/sites/{site_id}",
                name="Robot detail: site"
            )

