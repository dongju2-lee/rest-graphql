from typing import Any

import httpx
import strawberry
from strawberry.dataloader import DataLoader
from strawberry.federation import Schema
from strawberry.types import Info

from .config import TELEMETRY_SERVICE_URL


@strawberry.type
class Telemetry:
    robot_id: str
    battery_level: float
    cpu_usage: float
    temperature: float
    timestamp: str


@strawberry.federation.type(keys=["id"])
class Robot:
    id: strawberry.ID = strawberry.federation.field(external=True)

    @strawberry.field
    async def latest_telemetry(self, info: Info) -> Telemetry | None:
        """
        Extend Robot with telemetry data.
        Use DataLoader for batching.
        """
        telemetry_loader = info.context["telemetry_loader"]
        data = await telemetry_loader.load(str(self.id))
        if data is None:
            return None
        return Telemetry(
            robot_id=data["robot_id"],
            battery_level=data["battery_level"],
            cpu_usage=data["cpu_usage"],
            temperature=data["temperature"],
            timestamp=data["timestamp"],
        )

    @classmethod
    async def resolve_reference(cls, info: Info, id: strawberry.ID) -> "Robot":
        """
        Resolve Robot reference.
        Just return stub - actual data comes from robot subgraph.
        """
        return Robot(id=id)


async def load_telemetry_batch(keys: list[str]) -> list[dict[str, Any] | None]:
    """DataLoader batch function for telemetry."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{TELEMETRY_SERVICE_URL}/telemetry/batch",
                json={"robot_ids": keys},
            )
            response.raise_for_status()
            data = response.json()
            return [data.get(robot_id) for robot_id in keys]
        except Exception:
            return [None] * len(keys)


def create_telemetry_loader() -> DataLoader[str, dict[str, Any] | None]:
    """Create request-scoped telemetry DataLoader."""
    return DataLoader(load_fn=load_telemetry_batch)


@strawberry.type
class Query:
    @strawberry.field
    async def _dummy(self) -> str:
        """Dummy field - this subgraph only extends Robot."""
        return "telemetry"


schema = Schema(query=Query, types=[Robot], enable_federation_2=True)
