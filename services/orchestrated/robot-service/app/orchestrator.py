import os
import httpx
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.service import get_all_robots, get_robot_by_id
from sqlalchemy import select
from shared.db.models import Alert

# Environment variables for service URLs
TELEMETRY_SERVICE_URL = os.getenv("TELEMETRY_SERVICE_URL", "http://localhost:10002")
ALERT_SERVICE_URL = os.getenv("ALERT_SERVICE_URL", "http://localhost:10003")


async def get_dashboard_data(session: AsyncSession) -> List[Dict[str, Any]]:
    """
    Get dashboard data for all robots (first 15).
    Demonstrates N+1 problem: fetches robots, then makes individual calls for each robot's data.

    This intentionally uses sequential calls (not asyncio.gather) to maximize N+1 overhead.

    Returns:
        List of robot data with telemetry and alerts
    """
    # Get first 15 robots
    robots = await get_all_robots(session)
    robots_limited = robots[:15]

    dashboard_data = []

    # N+1: Individual sequential calls for each robot
    async with httpx.AsyncClient(timeout=30.0) as client:
        for robot in robots_limited:
            robot_data = {
                "id": robot.id,
                "name": robot.name,
                "model": robot.model,
                "location": robot.location,
                "status": robot.status,
                "telemetry": None,
                "alerts": [],
            }

            # Call 1: Get telemetry for this robot
            try:
                telemetry_response = await client.get(
                    f"{TELEMETRY_SERVICE_URL}/telemetry/{robot.id}/latest"
                )
                if telemetry_response.status_code == 200:
                    robot_data["telemetry"] = telemetry_response.json()
            except Exception:
                pass  # Telemetry is optional

            # Call 2: Get alerts for this robot
            try:
                alerts_response = await client.get(
                    f"{ALERT_SERVICE_URL}/alerts/{robot.id}"
                )
                if alerts_response.status_code == 200:
                    robot_data["alerts"] = alerts_response.json()
            except Exception:
                pass  # Alerts are optional

            dashboard_data.append(robot_data)

    return dashboard_data


async def get_robot_monitor_data(
    session: AsyncSession, robot_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get monitoring data for a single robot.
    Makes 3 separate calls: robot info, telemetry, alerts.

    Args:
        robot_id: The robot identifier

    Returns:
        Combined robot data or None if robot not found
    """
    # Call 1: Get robot info
    robot = await get_robot_by_id(session, robot_id)
    if robot is None:
        return None

    robot_data = {
        "id": robot.id,
        "name": robot.name,
        "model": robot.model,
        "location": robot.location,
        "status": robot.status,
        "telemetry": None,
        "alerts": [],
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Call 2: Get telemetry
        try:
            telemetry_response = await client.get(
                f"{TELEMETRY_SERVICE_URL}/telemetry/{robot_id}/latest"
            )
            if telemetry_response.status_code == 200:
                robot_data["telemetry"] = telemetry_response.json()
        except Exception:
            pass

        # Call 3: Get alerts
        try:
            alerts_response = await client.get(
                f"{ALERT_SERVICE_URL}/alerts/{robot_id}"
            )
            if alerts_response.status_code == 200:
                robot_data["alerts"] = alerts_response.json()
        except Exception:
            pass

    return robot_data


async def get_critical_alerts_with_context(session: AsyncSession) -> List[Dict[str, Any]]:
    """
    Get all critical alerts with robot and telemetry context.
    Demonstrates N+1: gets critical alerts, then fetches robot + telemetry for each.

    Returns:
        List of critical alerts with robot and telemetry data
    """
    # Get critical alerts directly from database
    stmt = select(Alert).where(Alert.severity == "critical").order_by(Alert.created_at.desc())
    result = await session.execute(stmt)
    critical_alerts = result.scalars().all()

    alerts_with_context = []

    # N+1: Individual sequential calls for each alert's robot
    async with httpx.AsyncClient(timeout=30.0) as client:
        for alert in critical_alerts:
            alert_data = {
                "alert_id": alert.id,
                "robot_id": alert.robot_id,
                "severity": alert.severity,
                "message": alert.message,
                "created_at": alert.created_at.isoformat(),
                "robot": None,
                "telemetry": None,
            }

            # Call 1: Get robot info
            robot = await get_robot_by_id(session, alert.robot_id)
            if robot:
                alert_data["robot"] = {
                    "id": robot.id,
                    "name": robot.name,
                    "model": robot.model,
                    "location": robot.location,
                    "status": robot.status,
                }

            # Call 2: Get telemetry
            try:
                telemetry_response = await client.get(
                    f"{TELEMETRY_SERVICE_URL}/telemetry/{alert.robot_id}/latest"
                )
                if telemetry_response.status_code == 200:
                    alert_data["telemetry"] = telemetry_response.json()
            except Exception:
                pass

            alerts_with_context.append(alert_data)

    return alerts_with_context
