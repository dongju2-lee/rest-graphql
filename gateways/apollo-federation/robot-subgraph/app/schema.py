import httpx
import strawberry
from strawberry.federation import Schema
from strawberry.types import Info

from .config import ROBOT_SERVICE_URL


@strawberry.federation.type(keys=["id"])
class Robot:
    id: strawberry.ID
    name: str
    model: str
    location: str
    status: str

    @classmethod
    async def resolve_reference(cls, info: Info, id: strawberry.ID) -> "Robot | None":
        """
        Resolve Robot entity from reference.
        Called when other subgraphs need Robot data via _entities query.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{ROBOT_SERVICE_URL}/robots/{id}")
                response.raise_for_status()
                data = response.json()
                return Robot(
                    id=strawberry.ID(data["id"]),
                    name=data["name"],
                    model=data["model"],
                    location=data["location"],
                    status=data["status"],
                )
            except Exception:
                return None


@strawberry.type
class Query:
    @strawberry.field
    async def robots(self, info: Info) -> list[Robot]:
        """Fetch all robots from the robot service."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{ROBOT_SERVICE_URL}/robots")
            response.raise_for_status()
            robots_data = response.json()

        return [
            Robot(
                id=strawberry.ID(r["id"]),
                name=r["name"],
                model=r["model"],
                location=r["location"],
                status=r["status"],
            )
            for r in robots_data
        ]

    @strawberry.field
    async def robot(self, info: Info, id: strawberry.ID) -> Robot | None:
        """Fetch a single robot by ID."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{ROBOT_SERVICE_URL}/robots/{id}")
                response.raise_for_status()
                data = response.json()
                return Robot(
                    id=strawberry.ID(data["id"]),
                    name=data["name"],
                    model=data["model"],
                    location=data["location"],
                    status=data["status"],
                )
            except Exception:
                return None


schema = Schema(query=Query, enable_federation_2=True)
