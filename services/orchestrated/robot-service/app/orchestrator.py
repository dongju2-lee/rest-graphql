import os
import httpx
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.service import get_all_robots, get_robot_by_id, get_robots_by_ids
from sqlalchemy import select
from shared.db.models import Alert

# Environment variables for service URLs
TELEMETRY_SERVICE_URL = os.getenv("TELEMETRY_SERVICE_URL", "http://localhost:10002")
ALERT_SERVICE_URL = os.getenv("ALERT_SERVICE_URL", "http://localhost:10003")


async def get_dashboard_data(session: AsyncSession) -> List[Dict[str, Any]]:
    """
    Get dashboard data for all robots (first 15).
    Uses batch endpoints to fetch telemetry and alerts in single calls.

    Returns:
        List of robot data with telemetry and alerts
    """
    # 1. Get first 15 robots (DB 1번)
    robots = await get_all_robots(session)
    robots_limited = robots[:15]

    robot_ids = [r.id for r in robots_limited]

    # 2. Batch fetch telemetry and alerts (HTTP 2번)
    telemetry_map: Dict[str, Any] = {}
    alerts_map: Dict[str, list] = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Batch call 1: POST /telemetry/batch
        try:
            telemetry_response = await client.post(
                f"{TELEMETRY_SERVICE_URL}/telemetry/batch",
                json={"robot_ids": robot_ids},
            )
            if telemetry_response.status_code == 200:
                telemetry_map = telemetry_response.json()
        except Exception:
            pass

        # Batch call 2: POST /alerts/batch
        try:
            alerts_response = await client.post(
                f"{ALERT_SERVICE_URL}/alerts/batch",
                json={"robot_ids": robot_ids},
            )
            if alerts_response.status_code == 200:
                alerts_map = alerts_response.json()
        except Exception:
            pass

    # 3. Combine results
    dashboard_data = []
    for robot in robots_limited:
        dashboard_data.append({
            "id": robot.id,
            "name": robot.name,
            "model": robot.model,
            "location": robot.location,
            "status": robot.status,
            "telemetry": telemetry_map.get(robot.id),
            "alerts": alerts_map.get(robot.id, []),
        })

    return dashboard_data


async def get_robot_monitor_data(
    session: AsyncSession, robot_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get monitoring data for a single robot.
    Makes 3 separate calls: robot info, telemetry, alerts.
    1:1 relationship - no batch needed.

    Args:
        robot_id: The robot identifier

    Returns:
        Combined robot data or None if robot not found
    """
    # Call 1: Get robot info (DB 1번)
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
        # Call 2: Get telemetry (HTTP 1번)
        try:
            telemetry_response = await client.get(
                f"{TELEMETRY_SERVICE_URL}/telemetry/{robot_id}/latest"
            )
            if telemetry_response.status_code == 200:
                robot_data["telemetry"] = telemetry_response.json()
        except Exception:
            pass

        # Call 3: Get alerts (HTTP 1번)
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
    Uses batch DB query and batch HTTP call to avoid N+1.

    Returns:
        List of critical alerts with robot and telemetry data
    """
    # 1. Get critical alerts from database (DB 1번)
    stmt = select(Alert).where(Alert.severity == "critical").order_by(Alert.created_at.desc())
    result = await session.execute(stmt)
    critical_alerts = result.scalars().all()

    # 2. Collect unique robot_ids
    robot_ids = list({alert.robot_id for alert in critical_alerts})

    # 3. Batch fetch robot info (DB 1번 - WHERE id IN (...))
    robots_map = await get_robots_by_ids(session, robot_ids)

    # 4. Batch fetch telemetry (HTTP 1번)
    telemetry_map: Dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            telemetry_response = await client.post(
                f"{TELEMETRY_SERVICE_URL}/telemetry/batch",
                json={"robot_ids": robot_ids},
            )
            if telemetry_response.status_code == 200:
                telemetry_map = telemetry_response.json()
        except Exception:
            pass

    # 5. Combine results
    alerts_with_context = []
    for alert in critical_alerts:
        robot = robots_map.get(alert.robot_id)
        alert_data = {
            "alert_id": alert.id,
            "robot_id": alert.robot_id,
            "severity": alert.severity,
            "message": alert.message,
            "created_at": alert.created_at.isoformat(),
            "robot": {
                "id": robot.id,
                "name": robot.name,
                "model": robot.model,
                "location": robot.location,
                "status": robot.status,
            } if robot else None,
            "telemetry": telemetry_map.get(alert.robot_id),
        }
        alerts_with_context.append(alert_data)

    return alerts_with_context
