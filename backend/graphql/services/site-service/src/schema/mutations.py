"""GraphQL mutations for Site Service (future expansion)"""

import strawberry


@strawberry.type
class Mutation:
    """Site service mutations (placeholder)"""
    
    @strawberry.field(description="Placeholder mutation")
    async def placeholder(self) -> bool:
        return True
