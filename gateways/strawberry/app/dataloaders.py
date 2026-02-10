from typing import Any

import httpx
from strawberry.dataloader import DataLoader

from .config import ALERT_SERVICE_URL, ROBOT_SERVICE_URL, TELEMETRY_SERVICE_URL


async def load_telemetry_batch(keys: list[str]) -> list[dict[str, Any] | None]:
    """
    DataLoader for telemetry data.
    Batches multiple robot_id requests into a single POST /telemetry/batch call.
    """
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


async def load_alerts_batch(keys: list[str]) -> list[list[dict[str, Any]]]:
    """
    DataLoader for alerts.
    Batches multiple robot_id requests into a single POST /alerts/batch call.
    """
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


async def load_robots_batch(keys: list[str]) -> list[dict[str, Any] | None]:
    """
    DataLoader for robots.
    Fetches individual robots. For better performance, could fetch all robots
    and filter, but this demonstrates individual fetching with batching.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        results = []
        for robot_id in keys:
            try:
                response = await client.get(f"{ROBOT_SERVICE_URL}/robots/{robot_id}")
                response.raise_for_status()
                results.append(response.json())
            except Exception:
                results.append(None)
        return results


def create_telemetry_loader() -> DataLoader[str, dict[str, Any] | None]:
    """Create a new telemetry DataLoader instance (request-scoped)."""
    return DataLoader(load_fn=load_telemetry_batch)


def create_alert_loader() -> DataLoader[str, list[dict[str, Any]]]:
    """Create a new alert DataLoader instance (request-scoped)."""
    return DataLoader(load_fn=load_alerts_batch)


def create_robot_loader() -> DataLoader[str, dict[str, Any] | None]:
    """Create a new robot DataLoader instance (request-scoped)."""
    return DataLoader(load_fn=load_robots_batch)
