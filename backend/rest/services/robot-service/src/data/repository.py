"""Robot data repository with in-memory data and latency simulation"""

import asyncio
import random
from typing import List, Optional
from datetime import datetime, timedelta

from core.config import get_settings


class RobotRepository:
    """Robot repository for data access"""
    
    def __init__(self):
        self.settings = get_settings()
        self._init_data()
    
    def _init_data(self):
        """Initialize in-memory data"""
        random.seed(100)  # Fixed seed for consistent data between REST and GraphQL

        statuses = ["active", "idle", "maintenance", "offline"]
        models = ["Model-X1", "Model-X2", "Model-Y1", "Model-Z1"]

        self.robots = [
            {
                "id": i,
                "name": f"Robot-{i}",
                "model": random.choice(models),
                "status": random.choice(statuses),
                "owner_id": ((i - 1) % 100) + 1,  # 100명의 사용자에게 분배
                "site_id": ((i - 1) % 5) + 1,  # 5개 사이트에 분배
                "battery": random.randint(20, 100),
                "last_maintenance": (datetime.now() - timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d"),
                "location": f"Zone-{chr(65 + (i % 10))}"  # Zone-A ~ Zone-J
            }
            for i in range(1, self.settings.num_robots + 1)
        ]

        random.seed()  # Reset seed
    
    async def get_all(self) -> List[dict]:
        """Get all robots"""
        await asyncio.sleep(self.settings.latency_robot_list)
        return [r.copy() for r in self.robots]
    
    async def get_by_id(self, robot_id: int) -> Optional[dict]:
        """Get single robot by ID"""
        await asyncio.sleep(self.settings.latency_robot_single)
        robot = next((r for r in self.robots if r["id"] == robot_id), None)
        return robot.copy() if robot else None
    
    async def get_by_ids(self, robot_ids: List[int]) -> List[dict]:
        """Get multiple robots by IDs (batch operation)"""
        await asyncio.sleep(self.settings.latency_robot_batch + (len(robot_ids) * 0.0001))
        return [r.copy() for r in self.robots if r["id"] in robot_ids]
    
    async def get_by_owner(self, owner_id: int) -> List[dict]:
        """Get all robots by owner ID"""
        await asyncio.sleep(self.settings.latency_robot_list)
        return [r.copy() for r in self.robots if r["owner_id"] == owner_id]
    
    async def get_by_site(self, site_id: int) -> List[dict]:
        """Get all robots by site ID"""
        await asyncio.sleep(self.settings.latency_robot_list)
        return [r.copy() for r in self.robots if r["site_id"] == site_id]
    
    def get_count(self) -> int:
        """Get total robot count"""
        return len(self.robots)


class TelemetryRepository:
    """Telemetry repository for data access - same logic as GraphQL"""

    def __init__(self):
        self.settings = get_settings()
        self._init_data()

    def _init_data(self):
        """Initialize in-memory telemetry data (1 record per robot)"""
        random.seed(42)  # Fixed seed for consistent data between REST and GraphQL

        self.telemetry = [
            {
                "robot_id": i,
                "cpu": round(random.uniform(10, 95), 1),
                "memory": round(random.uniform(20, 90), 1),
                "disk": round(random.uniform(30, 85), 1),
                "temperature": round(random.uniform(25, 65), 1),
                "error_count": random.randint(0, 10),
                "timestamp": (datetime.now() - timedelta(minutes=random.randint(1, 60))).isoformat()
            }
            for i in range(1, self.settings.num_robots + 1)
        ]

        random.seed()  # Reset seed

    async def get_by_robot_id(self, robot_id: int) -> Optional[dict]:
        """Get telemetry for a single robot"""
        await asyncio.sleep(self.settings.latency_telemetry_single)
        telemetry = next((t for t in self.telemetry if t["robot_id"] == robot_id), None)
        return telemetry.copy() if telemetry else None

    async def get_by_robot_ids(self, robot_ids: List[int]) -> List[dict]:
        """Get telemetry for multiple robots (batch operation)"""
        await asyncio.sleep(self.settings.latency_telemetry_batch + (len(robot_ids) * 0.0001))
        return [t.copy() for t in self.telemetry if t["robot_id"] in robot_ids]

    async def get_all(self) -> List[dict]:
        """Get all telemetry data"""
        await asyncio.sleep(self.settings.latency_telemetry_batch)
        return [t.copy() for t in self.telemetry]
