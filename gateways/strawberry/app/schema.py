from typing import Any

import httpx
import strawberry
from strawberry.types import Info

from .config import ALERT_SERVICE_URL, ROBOT_SERVICE_URL, TELEMETRY_SERVICE_URL


@strawberry.type
class TelemetryType:
    robot_id: str
    battery_level: float
    cpu_usage: float
    temperature: float
    timestamp: str


@strawberry.type
class AlertType:
    id: int
    robot_id: str
    severity: str
    message: str
    created_at: str


@strawberry.type
class RobotType:
    id: str
    name: str
    model: str
    location: str
    status: str

    @strawberry.field
    async def latest_telemetry(self, info: Info) -> TelemetryType | None:
        """Use DataLoader to batch fetch telemetry."""
        telemetry_loader = info.context["telemetry_loader"]
        data = await telemetry_loader.load(self.id)
        if data is None:
            return None
        return TelemetryType(
            robot_id=data["robot_id"],
            battery_level=data["battery_level"],
            cpu_usage=data["cpu_usage"],
            temperature=data["temperature"],
            timestamp=data["timestamp"],
        )

    @strawberry.field
    async def active_alerts(self, info: Info) -> list[AlertType]:
        """Use DataLoader to batch fetch alerts."""
        alert_loader = info.context["alert_loader"]
        alerts = await alert_loader.load(self.id)
        return [
            AlertType(
                id=alert["id"],
                robot_id=alert["robot_id"],
                severity=alert["severity"],
                message=alert["message"],
                created_at=alert["created_at"],
            )
            for alert in alerts
        ]


@strawberry.type
class FleetDashboardType:
    robots: list[RobotType]


@strawberry.type
class RobotMonitorType:
    robot: RobotType
    telemetry: TelemetryType | None
    recent_alerts: list[AlertType]


@strawberry.type
class CriticalAlertType:
    id: int
    message: str
    robot: RobotType | None
    telemetry_snapshot: TelemetryType | None


@strawberry.type
class Query:
    @strawberry.field
    async def fleet_dashboard(self, info: Info) -> FleetDashboardType:
        """
        Fetch all robots and use DataLoader to automatically batch
        telemetry and alerts requests.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{ROBOT_SERVICE_URL}/robots")
            response.raise_for_status()
            robots_data = response.json()

        robots = [
            RobotType(
                id=r["id"],
                name=r["name"],
                model=r["model"],
                location=r["location"],
                status=r["status"],
            )
            for r in robots_data
        ]

        return FleetDashboardType(robots=robots)

    @strawberry.field
    async def robot_monitor(self, info: Info, id: str) -> RobotMonitorType | None:
        """
        Fetch a single robot with its telemetry and alerts.
        No N+1 issue here as it's 1:1 relationship.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                robot_response = await client.get(f"{ROBOT_SERVICE_URL}/robots/{id}")
                robot_response.raise_for_status()
                robot_data = robot_response.json()

                telemetry_response = await client.get(
                    f"{TELEMETRY_SERVICE_URL}/telemetry/{id}/latest"
                )
                telemetry_data = (
                    telemetry_response.json()
                    if telemetry_response.status_code == 200
                    else None
                )

                alerts_response = await client.get(f"{ALERT_SERVICE_URL}/alerts/{id}")
                alerts_data = (
                    alerts_response.json()
                    if alerts_response.status_code == 200
                    else []
                )

                robot = RobotType(
                    id=robot_data["id"],
                    name=robot_data["name"],
                    model=robot_data["model"],
                    location=robot_data["location"],
                    status=robot_data["status"],
                )

                telemetry = (
                    TelemetryType(
                        robot_id=telemetry_data["robot_id"],
                        battery_level=telemetry_data["battery_level"],
                        cpu_usage=telemetry_data["cpu_usage"],
                        temperature=telemetry_data["temperature"],
                        timestamp=telemetry_data["timestamp"],
                    )
                    if telemetry_data
                    else None
                )

                alerts = [
                    AlertType(
                        id=a["id"],
                        robot_id=a["robot_id"],
                        severity=a["severity"],
                        message=a["message"],
                        created_at=a["created_at"],
                    )
                    for a in alerts_data
                ]

                return RobotMonitorType(
                    robot=robot, telemetry=telemetry, recent_alerts=alerts
                )
            except httpx.HTTPStatusError:
                return None

    @strawberry.field
    async def critical_alerts(self, info: Info) -> list[CriticalAlertType]:
        """
        Fetch critical alerts and use DataLoader to batch fetch
        robot and telemetry data.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{ALERT_SERVICE_URL}/alerts/critical")
            response.raise_for_status()
            alerts_data = response.json()

        robot_loader = info.context["robot_loader"]
        telemetry_loader = info.context["telemetry_loader"]

        results = []
        for alert_data in alerts_data:
            robot_id = alert_data["robot_id"]

            robot_data = await robot_loader.load(robot_id)
            telemetry_data = await telemetry_loader.load(robot_id)

            robot = (
                RobotType(
                    id=robot_data["id"],
                    name=robot_data["name"],
                    model=robot_data["model"],
                    location=robot_data["location"],
                    status=robot_data["status"],
                )
                if robot_data
                else None
            )

            telemetry = (
                TelemetryType(
                    robot_id=telemetry_data["robot_id"],
                    battery_level=telemetry_data["battery_level"],
                    cpu_usage=telemetry_data["cpu_usage"],
                    temperature=telemetry_data["temperature"],
                    timestamp=telemetry_data["timestamp"],
                )
                if telemetry_data
                else None
            )

            results.append(
                CriticalAlertType(
                    id=alert_data["id"],
                    message=alert_data["message"],
                    robot=robot,
                    telemetry_snapshot=telemetry,
                )
            )

        return results


schema = strawberry.Schema(query=Query)
