from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from strawberry.fastapi import GraphQLRouter

from .dataloaders import (
    create_alert_loader,
    create_robot_loader,
    create_telemetry_loader,
)
from .schema import schema

http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=30.0)
    yield
    await http_client.aclose()


app = FastAPI(title="Strawberry GraphQL Gateway", lifespan=lifespan)

Instrumentator().instrument(app).expose(app)


async def get_context():
    """
    Create request-scoped DataLoader instances.
    Each request gets fresh DataLoaders to properly batch requests.
    """
    return {
        "telemetry_loader": create_telemetry_loader(),
        "alert_loader": create_alert_loader(),
        "robot_loader": create_robot_loader(),
    }


graphql_app = GraphQLRouter(schema, context_getter=get_context)

app.include_router(graphql_app, prefix="/graphql")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
