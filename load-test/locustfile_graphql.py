"""
Locust load test for GraphQL (Apollo Federation)

Test scenarios for REST vs GraphQL performance comparison.
Run with: locust -f locustfile_graphql.py --host=http://localhost:14000
"""

from locust import HttpUser, task, between
import random

import prometheus_exporter  # noqa: F401


class GraphQLUser(HttpUser):
    """Load test user for GraphQL API"""

    wait_time = between(0.1, 0.5)  # Wait 0.1-0.5s between requests
    host = "http://localhost:14000"  # Apollo Router

    # ============== API-1: Simple Query (Over-fetching test) ==============

    @task(3)
    def get_all_users(self):
        """
        Scenario 1: Simple query (Over-fetching test)
        GraphQL advantage: Client selects only needed fields
        """
        query = """
        query GetUsers {
            users {
                id
                name
                email
            }
        }
        """
        self.client.post("/", json={"query": query}, name="API-1: Get users (3 fields)")

    # ============== API-2: Cross-Service Join ==============

    @task(2)
    def get_user_with_robots(self):
        """
        Scenario 2: Cross-service join (1-hop dependency)
        GraphQL advantage: Single query, automatic joining via Federation
        """
        user_id = random.randint(1, 100)
        query = f"""
        query GetUserWithRobots {{
            user(id: "{user_id}") {{
                id
                name
                email
                robots {{
                    id
                    name
                    status
                    battery
                }}
            }}
        }}
        """
        self.client.post("/", json={"query": query}, name="API-2: User + robots")

    # ============== API-3: N+1 Problem Test ==============

    @task(1)
    def get_robots_with_telemetry(self):
        """
        Scenario 3: N+1 problem test with telemetry
        GraphQL advantage: DataLoader batches requests automatically
        """
        query = """
        query GetRobotsWithTelemetry {
            robots {
                id
                name
                status
                telemetry {
                    cpu
                    memory
                    temperature
                }
            }
        }
        """
        self.client.post("/", json={"query": query}, name="API-3: N+1 (robots+telemetry)")

    # ============== API-4: Complex Aggregation (Dashboard) ==============

    @task(1)
    def site_dashboard(self):
        """
        Scenario 4: Complex aggregation (Site Dashboard)
        GraphQL advantage: Single query with nested relations
        """
        site_id = random.randint(1, 5)
        query = f"""
        query SiteDashboard {{
            site(id: "{site_id}") {{
                id
                name
                location
                robots {{
                    id
                    name
                    status
                    battery
                    owner {{
                        id
                        name
                        email
                    }}
                    telemetry {{
                        cpu
                        memory
                        temperature
                        errorCount
                    }}
                }}
            }}
        }}
        """
        self.client.post("/", json={"query": query}, name="API-4: Site dashboard")

    # ============== Additional Scenarios ==============

    @task(1)
    def get_single_robot_detail(self):
        """
        Single robot with all relations
        """
        robot_id = random.randint(1, 500)
        query = f"""
        query RobotDetail {{
            robot(id: "{robot_id}") {{
                id
                name
                model
                status
                battery
                owner {{
                    name
                    email
                }}
                site {{
                    name
                    location
                }}
                telemetry {{
                    cpu
                    memory
                    disk
                    temperature
                }}
            }}
        }}
        """
        self.client.post("/", json={"query": query}, name="Robot detail (full)")
