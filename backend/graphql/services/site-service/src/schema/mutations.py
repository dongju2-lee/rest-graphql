"""GraphQL mutations for Site Service (future expansion)"""

import strawberry


@strawberry.type
class Mutation:
    """Site service mutations (placeholder)"""
    
    @strawberry.field(description="Placeholder mutation for site service")
    async def site_placeholder(self) -> bool:
        """Placeholder for future site mutations"""
        return True
