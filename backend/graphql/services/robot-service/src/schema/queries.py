"""GraphQL queries for Robot Service"""

from typing import List, Optional
import strawberry

from schema.types import Robot
from data.repository import RobotRepository


@strawberry.type
class Query:
    """Robot service queries"""
    
    @strawberry.field(description="Get all robots")
    async def robots(self, info: strawberry.Info) -> List[Robot]:
        """Get all robots"""
        repository = RobotRepository()
        robots_data = await repository.get_all()
        return [Robot.from_dict(r) for r in robots_data]
    
    @strawberry.field(description="Get single robot by ID")
    async def robot(
        self,
        id: strawberry.ID,
        info: strawberry.Info
    ) -> Optional[Robot]:
        """Get single robot by ID"""
        repository = RobotRepository()
        robot_data = await repository.get_by_id(int(id))
        
        if not robot_data:
            return None
        
        return Robot.from_dict(robot_data)
    
    @strawberry.field(description="Get robots by owner ID")
    async def robots_by_owner(
        self,
        owner_id: int,
        info: strawberry.Info
    ) -> List[Robot]:
        """Get all robots by owner ID"""
        repository = RobotRepository()
        robots_data = await repository.get_by_owner(owner_id)
        return [Robot.from_dict(r) for r in robots_data]
    
    @strawberry.field(description="Get robots by site ID")
    async def robots_by_site(
        self,
        site_id: int,
        info: strawberry.Info
    ) -> List[Robot]:
        """Get all robots by site ID"""
        repository = RobotRepository()
        robots_data = await repository.get_by_site(site_id)
        return [Robot.from_dict(r) for r in robots_data]
