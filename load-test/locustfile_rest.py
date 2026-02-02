"""
Locust load test for REST API (NGINX Gateway)
"""

from locust import HttpUser, task, between
import random


class RestUser(HttpUser):
    """Load test user for REST API"""
    
    wait_time = between(0.1, 0.5)
    host = "http://localhost:24000"  # NGINX Gateway
    
    @task(3)
    def get_all_users(self):
        """
        Scenario 1: Simple query
        REST disadvantage: Over-fetching (returns all fields)
        """
        self.client.get("/api/users", name="REST: Get all users")
    
    @task(2)
    def get_user_with_robots_naive(self):
        """
        Scenario 2: Cross-service join (Naive approach)
        REST disadvantage: Multiple sequential requests (N+1)
        """
        user_id = random.randint(1, 100)
        
        # 1. Get user
        user_response = self.client.get(f"/api/users/{user_id}", name="REST: Get user")
        
        if user_response.status_code == 200:
            # 2. Get user's robots (requires knowing owner_id)
            self.client.get(f"/api/robots/by-owner/{user_id}", name="REST: Get robots by owner")
    
    @task(1)
    def get_users_with_robots_n_plus_1(self):
        """
        Scenario 3: N+1 problem (worst case for REST)
        REST disadvantage: 1 + N queries (1 for users, N for each user's robots)
        """
        # 1. Get all users
        users_response = self.client.get("/api/users", name="REST: Get all users (N+1)")
        
        if users_response.status_code == 200:
            users = users_response.json()
            # Limit to first 10 for testing (otherwise too many requests)
            for user in users[:10]:
                # 2-N. Get robots for each user
                self.client.get(
                    f"/api/robots/by-owner/{user['id']}", 
                    name="REST: Get robots for each user (N+1)"
                )
    
    @task(1)
    def complex_aggregation_multiple_calls(self):
        """
        Scenario 4: Complex aggregation (multiple REST calls)
        REST disadvantage: Multiple sequential requests, client-side coordination
        """
        site_id = random.randint(1, 5)
        
        # 1. Get site
        self.client.get(f"/api/sites/{site_id}", name="REST: Get site")
        
        # 2. Get users by site
        users_response = self.client.get(
            f"/api/users/by-site/{site_id}", 
            name="REST: Get users by site"
        )
        
        # 3. Get robots by site
        self.client.get(
            f"/api/robots/by-site/{site_id}", 
            name="REST: Get robots by site"
        )
        
        # 4. For each user, get their robots (simplified - just first 5)
        if users_response.status_code == 200:
            users = users_response.json()
            for user in users[:5]:
                self.client.get(
                    f"/api/robots/by-owner/{user['id']}", 
                    name="REST: Get robots per user"
                )
