"""GraphQL queries for Site Service"""

from typing import List, Optional
import strawberry

from schema.types import Site
from data.repository import SiteRepository


@strawberry.type
class Query:
    """Site service queries"""
    
    @strawberry.field(description="Get all sites")
    async def sites(self, info: strawberry.Info) -> List[Site]:
        """Get all sites"""
        repository = SiteRepository()
        sites_data = await repository.get_all()
        return [Site.from_dict(s) for s in sites_data]
    
    @strawberry.field(description="Get single site by ID")
    async def site(
        self,
        id: strawberry.ID,
        info: strawberry.Info
    ) -> Optional[Site]:
        """Get single site by ID"""
        repository = SiteRepository()
        site_data = await repository.get_by_id(int(id))
        
        if not site_data:
            return None
        
        return Site.from_dict(site_data)
