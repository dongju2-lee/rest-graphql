"""GraphQL schema"""

import strawberry
from strawberry.fastapi import GraphQLRouter

from schema.types import Robot, User
from schema.queries import Query
from schema.mutations import Mutation


# Create Federation schema
schema = strawberry.federation.Schema(
    query=Query,
    mutation=Mutation,
    types=[User, Robot]  # Include extended types
)


def create_graphql_router() -> GraphQLRouter:
    """Create GraphQL router for FastAPI"""
    return GraphQLRouter(
        schema,
        graphiql=True,
    )


__all__ = ["schema", "create_graphql_router", "Robot", "User", "Query", "Mutation"]
