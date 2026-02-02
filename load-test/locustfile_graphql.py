"""
Locust load test for GraphQL (Apollo Federation)
"""

from locust import HttpUser, task, between
import random


class GraphQLUser(HttpUser):
    """Load test user for GraphQL API"""
    
    wait_time = between(0.1, 0.5)  # Wait 0.1-0.5s between requests
    host = "http://localhost:14000"  # Apollo Router
    
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
        self.client.post("/", json={"query": query}, name="GraphQL: Get all users")
    
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
        self.client.post("/", json={"query": query}, name="GraphQL: User with robots")
    
    @task(1)
    def get_users_with_robots_list(self):
        """
        Scenario 3: N+1 problem test
        GraphQL advantage: DataLoader batches requests automatically
        """
        query = """
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
        """
        self.client.post("/", json={"query": query}, name="GraphQL: N+1 problem (users+robots)")
    
    @task(1)
    def complex_aggregation(self):
        """
        Scenario 4: Complex aggregation
        GraphQL advantage: Single query, server-side coordination
        """
        site_id = random.randint(1, 5)
        query = f"""
        query ComplexAggregation {{
            site(id: "{site_id}") {{
                id
                name
                location
            }}
            usersBySite(siteId: {site_id}) {{
                id
                name
                robots {{
                    id
                    status
                    battery
                }}
            }}
            robotsBySite(siteId: {site_id}) {{
                id
                name
                status
                owner {{
                    id
                    name
                }}
            }}
        }}
        """
        self.client.post("/", json={"query": query}, name="GraphQL: Complex aggregation")
