"""GraphQL mutations for Robot Service (future expansion)"""

import strawberry


@strawberry.type
class Mutation:
    """Robot service mutations (placeholder for future)"""
    
    @strawberry.field(description="Placeholder mutation for robot service")
    async def robot_placeholder(self) -> bool:
        """Placeholder for future robot mutations"""
        return True
