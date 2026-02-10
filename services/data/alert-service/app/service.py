from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from shared.db.models import Alert
from shared.schemas.alert import AlertResponse
from typing import List, Dict


async def get_alerts_by_robot(session: AsyncSession, robot_id: str) -> List[AlertResponse]:
    """
    Fetch all alerts for a specific robot.

    Args:
        robot_id: The robot identifier

    Returns:
        List of AlertResponse objects
    """
    stmt = (
        select(Alert)
        .where(Alert.robot_id == robot_id)
        .order_by(desc(Alert.created_at))
    )
    result = await session.execute(stmt)
    alerts = result.scalars().all()

    return [
        AlertResponse(
            id=alert.id,
            robot_id=alert.robot_id,
            severity=alert.severity,
            message=alert.message,
            created_at=alert.created_at,
        )
        for alert in alerts
    ]


async def get_critical_alerts(session: AsyncSession) -> List[AlertResponse]:
    """
    Fetch all critical severity alerts.

    Returns:
        List of critical AlertResponse objects
    """
    stmt = (
        select(Alert)
        .where(Alert.severity == "critical")
        .order_by(desc(Alert.created_at))
    )
    result = await session.execute(stmt)
    alerts = result.scalars().all()

    return [
        AlertResponse(
            id=alert.id,
            robot_id=alert.robot_id,
            severity=alert.severity,
            message=alert.message,
            created_at=alert.created_at,
        )
        for alert in alerts
    ]


async def get_batch_alerts(
    session: AsyncSession, robot_ids: list[str]
) -> Dict[str, List[AlertResponse]]:
    """
    Fetch alerts for multiple robots.

    Args:
        robot_ids: List of robot identifiers

    Returns:
        Dictionary mapping robot_id to list of AlertResponse
    """
    result = {}

    for robot_id in robot_ids:
        alerts = await get_alerts_by_robot(session, robot_id)
        result[robot_id] = alerts

    return result
