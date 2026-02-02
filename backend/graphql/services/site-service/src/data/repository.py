"""Site data repository with in-memory data and latency simulation"""

import asyncio
from typing import List, Optional

from core.config import get_settings


class SiteRepository:
    """Site repository for data access"""
    
    def __init__(self):
        self.settings = get_settings()
        self._init_data()
    
    def _init_data(self):
        """Initialize in-memory data"""
        locations = [
            ("Seoul Factory", "Seoul, South Korea", "Asia/Seoul", 200),
            ("Tokyo Warehouse", "Tokyo, Japan", "Asia/Tokyo", 150),
            ("Berlin Manufacturing", "Berlin, Germany", "Europe/Berlin", 180),
            ("San Francisco Office", "San Francisco, USA", "America/Los_Angeles", 100),
            ("London Distribution", "London, UK", "Europe/London", 120)
        ]
        
        self.sites = [
            {
                "id": i,
                "name": locations[i-1][0],
                "location": locations[i-1][1],
                "timezone": locations[i-1][2],
                "capacity": locations[i-1][3],
                "description": f"Primary site for {locations[i-1][1]} operations"
            }
            for i in range(1, self.settings.num_sites + 1)
        ]
    
    async def get_all(self) -> List[dict]:
        """Get all sites"""
        await asyncio.sleep(self.settings.latency_site_list)
        return [s.copy() for s in self.sites]
    
    async def get_by_id(self, site_id: int) -> Optional[dict]:
        """Get single site by ID"""
        await asyncio.sleep(self.settings.latency_site_single)
        site = next((s for s in self.sites if s["id"] == site_id), None)
        return site.copy() if site else None
    
    async def get_by_ids(self, site_ids: List[int]) -> List[dict]:
        """Get multiple sites by IDs (batch operation)"""
        await asyncio.sleep(self.settings.latency_site_batch + (len(site_ids) * 0.0001))
        return [s.copy() for s in self.sites if s["id"] in site_ids]
    
    def get_count(self) -> int:
        """Get total site count"""
        return len(self.sites)
