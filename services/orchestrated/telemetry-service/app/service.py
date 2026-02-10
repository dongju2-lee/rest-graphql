from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from shared.db.models import TelemetryData
from shared.schemas.telemetry import TelemetryResponse
from typing import Optional, Dict


async def get_latest_telemetry(session: AsyncSession, robot_id: str) -> Optional[TelemetryResponse]:
    """
    Fetch the latest telemetry data for a specific robot.

    Args:
        robot_id: The robot identifier

    Returns:
        TelemetryResponse if found, None otherwise
    """
    stmt = (
        select(TelemetryData)
        .where(TelemetryData.robot_id == robot_id)
        .order_by(desc(TelemetryData.timestamp))
        .limit(1)
    )
    result = await session.execute(stmt)
    telemetry = result.scalar_one_or_none()

    if telemetry is None:
        return None

    return TelemetryResponse(
        robot_id=telemetry.robot_id,
        battery_level=telemetry.battery_level,
        cpu_usage=telemetry.cpu_usage,
        temperature=telemetry.temperature,
        timestamp=telemetry.timestamp,
    )


async def get_batch_telemetry(
    session: AsyncSession, robot_ids: list[str]
) -> Dict[str, Optional[TelemetryResponse]]:
    """
    Fetch latest telemetry data for multiple robots.

    Args:
        robot_ids: List of robot identifiers

    Returns:
        Dictionary mapping robot_id to TelemetryResponse (or None if not found)
    """
    result = {}

    for robot_id in robot_ids:
        telemetry = await get_latest_telemetry(session, robot_id)
        result[robot_id] = telemetry

    return result
