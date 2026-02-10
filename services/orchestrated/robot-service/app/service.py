from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shared.db.models import Robot
from shared.schemas.robot import RobotResponse
from typing import List, Optional


async def get_all_robots(session: AsyncSession) -> List[RobotResponse]:
    """
    Fetch all robots from the database.

    Returns:
        List of RobotResponse objects
    """
    stmt = select(Robot).order_by(Robot.id)
    result = await session.execute(stmt)
    robots = result.scalars().all()

    return [
        RobotResponse(
            id=robot.id,
            name=robot.name,
            model=robot.model,
            location=robot.location,
            status=robot.status,
        )
        for robot in robots
    ]


async def get_robot_by_id(session: AsyncSession, robot_id: str) -> Optional[RobotResponse]:
    """
    Fetch a single robot by ID.

    Args:
        robot_id: The robot identifier

    Returns:
        RobotResponse if found, None otherwise
    """
    stmt = select(Robot).where(Robot.id == robot_id)
    result = await session.execute(stmt)
    robot = result.scalar_one_or_none()

    if robot is None:
        return None

    return RobotResponse(
        id=robot.id,
        name=robot.name,
        model=robot.model,
        location=robot.location,
        status=robot.status,
    )
