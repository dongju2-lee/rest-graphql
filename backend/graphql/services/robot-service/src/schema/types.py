"""GraphQL types for Robot Service"""

from typing import Optional, TYPE_CHECKING
import strawberry

if TYPE_CHECKING:
    from strawberry.types import Info


@strawberry.federation.type(keys=["id"], extend=True)
class User:
    """Extended User type (reference from user-service)"""
    id: strawberry.ID = strawberry.federation.field(external=True)
    
    @strawberry.field(description="Robots owned by this user")
    async def robots(self, info: "Info") -> list["Robot"]:
        """Get all robots owned by this user"""
        from data.repository import RobotRepository
        
        repository = RobotRepository()
        robots_data = await repository.get_by_owner(int(self.id))
        return [Robot.from_dict(r) for r in robots_data]


@strawberry.federation.type(keys=["id"])
class Robot:
    """Robot GraphQL type with Federation support"""
    
    id: strawberry.ID
    name: str
    model: str
    status: str
    owner_id: int
    site_id: int
    battery: int
    last_maintenance: Optional[str] = None
    location: Optional[str] = None
    
    @strawberry.field(description="Owner of this robot")
    def owner(self) -> User:
        """Get the owner of this robot (returns User reference)"""
        return User(id=strawberry.ID(str(self.owner_id)))
    
    @classmethod
    def from_dict(cls, data: dict) -> "Robot":
        """Create Robot from dictionary"""
        return cls(
            id=strawberry.ID(str(data["id"])),
            name=data["name"],
            model=data["model"],
            status=data["status"],
            owner_id=data["owner_id"],
            site_id=data["site_id"],
            battery=data["battery"],
            last_maintenance=data.get("last_maintenance"),
            location=data.get("location")
        )
    
    @classmethod
    async def resolve_reference(cls, id: strawberry.ID, info: "Info") -> Optional["Robot"]:
        """Resolve Federation reference"""
        from data.repository import RobotRepository
        
        repository = RobotRepository()
        robot_data = await repository.get_by_id(int(id))
        
        if not robot_data:
            return None
        
        return cls.from_dict(robot_data)
