"""GraphQL schema"""

import strawberry
from strawberry.fastapi import GraphQLRouter
from starlette.requests import Request

from schema.types import Robot, User, Site, Telemetry
from schema.queries import Query
from schema.mutations import Mutation
from data.dataloader import get_dataloaders


# Create Federation schema
schema = strawberry.federation.Schema(
    query=Query,
    mutation=Mutation,
    types=[User, Robot, Site, Telemetry]  # Include extended types
)


async def get_context(request: Request):
    """
    Create context for each GraphQL request.
    DataLoaders are created per-request to ensure proper batching.
    """
    return {
        "request": request,
        "dataloaders": get_dataloaders(),
    }


def create_graphql_router() -> GraphQLRouter:
    """Create GraphQL router for FastAPI"""
    return GraphQLRouter(
        schema,
        graphiql=True,
        context_getter=get_context,
    )


__all__ = ["schema", "create_graphql_router", "Robot", "User", "Site", "Telemetry", "Query", "Mutation"]
