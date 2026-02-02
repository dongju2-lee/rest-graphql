"""GraphQL mutations for User Service (future expansion)"""

import strawberry


@strawberry.type
class Mutation:
    """User service mutations (placeholder for future)"""
    
    @strawberry.field(description="Placeholder mutation for user service")
    async def user_placeholder(self) -> bool:
        """Placeholder for future user mutations"""
        return True
