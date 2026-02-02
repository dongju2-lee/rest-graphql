"""GraphQL schema"""

import strawberry
from strawberry.fastapi import GraphQLRouter

from schema.types import Site
from schema.queries import Query
from schema.mutations import Mutation


schema = strawberry.federation.Schema(
    query=Query,
    mutation=Mutation
)


def create_graphql_router() -> GraphQLRouter:
    return GraphQLRouter(schema, graphiql=True)


__all__ = ["schema", "create_graphql_router", "Site", "Query", "Mutation"]
