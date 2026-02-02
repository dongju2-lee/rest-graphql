"""GraphQL types for User Service"""

from typing import Optional
import strawberry


@strawberry.federation.type(keys=["id"])
class User:
    """User GraphQL type with Federation support"""
    
    id: strawberry.ID
    name: str
    email: str
    role: str
    phone: Optional[str] = None
    address: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    site_id: int
    
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create User from dictionary"""
        return cls(
            id=strawberry.ID(str(data["id"])),
            name=data["name"],
            email=data["email"],
            role=data["role"],
            phone=data.get("phone"),
            address=data.get("address"),
            bio=data.get("bio"),
            avatar_url=data.get("avatar_url"),
            site_id=data["site_id"]
        )
    
    @classmethod
    async def resolve_reference(cls, id: strawberry.ID, info: strawberry.Info) -> Optional["User"]:
        """
        Resolve Federation reference
        
        This is called by Apollo Router when another service references a User
        """
        from data.repository import UserRepository
        
        repository = UserRepository()
        user_data = await repository.get_by_id(int(id))
        
        if not user_data:
            return None
        
        return cls.from_dict(user_data)
