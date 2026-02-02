"""GraphQL queries for User Service"""

from typing import List, Optional
import strawberry

from schema.types import User
from data.repository import UserRepository


@strawberry.type
class Query:
    """User service queries"""
    
    @strawberry.field(description="Get all users")
    async def users(
        self,
        info: strawberry.Info
    ) -> List[User]:
        """
        Get all users
        
        Returns:
            List of users
        """
        repository = UserRepository()
        users_data = await repository.get_all()
        return [User.from_dict(u) for u in users_data]
    
    @strawberry.field(description="Get single user by ID")
    async def user(
        self,
        id: strawberry.ID,
        info: strawberry.Info
    ) -> Optional[User]:
        """
        Get single user by ID
        
        Args:
            id: User ID
        
        Returns:
            User or None if not found
        """
        repository = UserRepository()
        user_data = await repository.get_by_id(int(id))
        
        if not user_data:
            return None
        
        return User.from_dict(user_data)
    
    @strawberry.field(description="Get users by site ID")
    async def users_by_site(
        self,
        site_id: int,
        info: strawberry.Info
    ) -> List[User]:
        """
        Get all users by site ID
        
        Args:
            site_id: Site ID
        
        Returns:
            List of users
        """
        repository = UserRepository()
        users_data = await repository.get_by_site(site_id)
        return [User.from_dict(u) for u in users_data]
