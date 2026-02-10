from typing import Any

import httpx
import strawberry
from strawberry.dataloader import DataLoader
from strawberry.federation import Schema
from strawberry.types import Info

from .config import ALERT_SERVICE_URL


@strawberry.type
class Alert:
    id: int
    robot_id: str
    severity: str
    message: str
    created_at: str


@strawberry.federation.type(keys=["id"])
class Robot:
    id: strawberry.ID = strawberry.federation.field(external=True)

    @strawberry.field
    async def active_alerts(self, info: Info) -> list[Alert]:
        """
        Extend Robot with active alerts.
        Use DataLoader for batching.
        """
        alert_loader = info.context["alert_loader"]
        alerts = await alert_loader.load(str(self.id))
        return [
            Alert(
                id=alert["id"],
                robot_id=alert["robot_id"],
                severity=alert["severity"],
                message=alert["message"],
                created_at=alert["created_at"],
            )
            for alert in alerts
        ]

    @classmethod
    async def resolve_reference(cls, info: Info, id: strawberry.ID) -> "Robot":
        """
        Resolve Robot reference.
        Just return stub - actual data comes from robot subgraph.
        """
        return Robot(id=id)


async def load_alerts_batch(keys: list[str]) -> list[list[dict[str, Any]]]:
    """DataLoader batch function for alerts."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{ALERT_SERVICE_URL}/alerts/batch",
                json={"robot_ids": keys},
            )
            response.raise_for_status()
            data = response.json()
            return [data.get(robot_id, []) for robot_id in keys]
        except Exception:
            return [[] for _ in keys]


def create_alert_loader() -> DataLoader[str, list[dict[str, Any]]]:
    """Create request-scoped alert DataLoader."""
    return DataLoader(load_fn=load_alerts_batch)


@strawberry.type
class Query:
    @strawberry.field
    async def critical_alerts(self, info: Info) -> list[Alert]:
        """
        Fetch critical alerts from alert service.
        This is a root query in the alert subgraph.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{ALERT_SERVICE_URL}/alerts/critical")
            response.raise_for_status()
            alerts_data = response.json()

        return [
            Alert(
                id=alert["id"],
                robot_id=alert["robot_id"],
                severity=alert["severity"],
                message=alert["message"],
                created_at=alert["created_at"],
            )
            for alert in alerts_data
        ]


schema = Schema(query=Query, types=[Robot], enable_federation_2=True)
