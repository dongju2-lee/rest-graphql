"""GraphQL mutations for User Service (future expansion)"""

import strawberry


@strawberry.type
class Mutation:
    """User service mutations (placeholder for future)"""
    
    @strawberry.field(description="Placeholder mutation")
    async def placeholder(self) -> bool:
        """Placeholder for future mutations"""
        return True
