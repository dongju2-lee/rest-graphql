"""User data repository with in-memory data and latency simulation"""

import asyncio
from typing import List, Optional

from core.config import get_settings


class UserRepository:
    """User repository for data access"""
    
    def __init__(self):
        self.settings = get_settings()
        self._init_data()
    
    def _init_data(self):
        """Initialize in-memory data"""
        self.users = [
            {
                "id": i,
                "name": f"User{i}",
                "email": f"user{i}@robot.com",
                "role": "operator" if i % 3 != 0 else "admin",
                "phone": f"+82-10-{1000+i:04d}-{5000+i:04d}",
                "address": f"Seoul, District {i % 25 + 1}, Street {i}",
                "bio": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 10,  # ~1KB
                "avatar_url": f"https://api.dicebear.com/7.x/avataaars/svg?seed={i}",
                "site_id": (i % 5) + 1
            }
            for i in range(1, self.settings.num_users + 1)
        ]
    
    async def get_all(self, fields: Optional[List[str]] = None) -> List[dict]:
        """
        Get all users
        
        Args:
            fields: Optional list of fields to return
        
        Returns:
            List of user dictionaries
        """
        await asyncio.sleep(self.settings.latency_user_list)
        
        if fields:
            return [{k: u[k] for k in fields if k in u} for u in self.users]
        return [u.copy() for u in self.users]
    
    async def get_by_id(self, user_id: int) -> Optional[dict]:
        """
        Get single user by ID
        
        Args:
            user_id: User ID
        
        Returns:
            User dictionary or None
        """
        await asyncio.sleep(self.settings.latency_user_single)
        user = next((u for u in self.users if u["id"] == user_id), None)
        return user.copy() if user else None
    
    async def get_by_ids(self, user_ids: List[int]) -> List[dict]:
        """
        Get multiple users by IDs (batch operation)
        
        Args:
            user_ids: List of user IDs
        
        Returns:
            List of user dictionaries
        """
        # Slightly longer than single but much faster than N queries
        await asyncio.sleep(self.settings.latency_user_batch + (len(user_ids) * 0.0001))
        return [u.copy() for u in self.users if u["id"] in user_ids]
    
    async def get_by_site(self, site_id: int) -> List[dict]:
        """
        Get all users by site ID
        
        Args:
            site_id: Site ID
        
        Returns:
            List of user dictionaries
        """
        await asyncio.sleep(self.settings.latency_user_list)
        return [u.copy() for u in self.users if u["site_id"] == site_id]
    
    def get_count(self) -> int:
        """Get total user count"""
        return len(self.users)
