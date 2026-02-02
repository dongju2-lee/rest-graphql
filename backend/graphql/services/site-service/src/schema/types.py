"""GraphQL types for Site Service"""

from typing import Optional, TYPE_CHECKING
import strawberry

if TYPE_CHECKING:
    from strawberry.types import Info


@strawberry.federation.type(keys=["id"])
class Site:
    """Site GraphQL type with Federation support"""
    
    id: strawberry.ID
    name: str
    location: str
    timezone: str
    capacity: int
    description: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "Site":
        """Create Site from dictionary"""
        return cls(
            id=strawberry.ID(str(data["id"])),
            name=data["name"],
            location=data["location"],
            timezone=data["timezone"],
            capacity=data["capacity"],
            description=data.get("description")
        )
    
    @classmethod
    async def resolve_reference(cls, id: strawberry.ID, info: "Info") -> Optional["Site"]:
        """Resolve Federation reference"""
        from data.repository import SiteRepository
        
        repository = SiteRepository()
        site_data = await repository.get_by_id(int(id))
        
        if not site_data:
            return None
        
        return cls.from_dict(site_data)
