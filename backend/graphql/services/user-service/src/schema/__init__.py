"""GraphQL schema"""

import strawberry
from strawberry.fastapi import GraphQLRouter

from schema.types import User
from schema.queries import Query
from schema.mutations import Mutation


# Create Federation schema
schema = strawberry.federation.Schema(
    query=Query,
    mutation=Mutation
)


def create_graphql_router() -> GraphQLRouter:
    """Create GraphQL router for FastAPI"""
    return GraphQLRouter(
        schema,
        graphiql=True,  # Enable GraphiQL interface
    )


__all__ = ["schema", "create_graphql_router", "User", "Query", "Mutation"]
