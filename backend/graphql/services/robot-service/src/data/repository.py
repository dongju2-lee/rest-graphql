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
        """
        Get multiple robots by IDs (batch operation for DataLoader)
        Critical for N+1 problem solution
        """
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
