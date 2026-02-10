from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_fastapi_instrumentator import Instrumentator
from typing import List

from shared.db.database import get_session, create_tables
from shared.schemas.robot import RobotResponse
from app.service import get_all_robots, get_robot_by_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Creates database tables on startup.
    """
    await create_tables()
    yield


app = FastAPI(
    title="Robot Service",
    description="Provides robot data",
    version="1.0.0",
    lifespan=lifespan,
)

# Initialize Prometheus metrics
Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "ok"}


@app.get("/robots", response_model=List[RobotResponse])
async def list_robots(session: AsyncSession = Depends(get_session)):
    """
    Retrieve all robots.

    Returns:
        List of all robots in the system
    """
    try:
        robots = await get_all_robots(session)
        return robots
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/robots/{robot_id}", response_model=RobotResponse)
async def get_robot(robot_id: str, session: AsyncSession = Depends(get_session)):
    """
    Retrieve a single robot by ID.

    Args:
        robot_id: The robot identifier

    Returns:
        Robot details

    Raises:
        404: Robot not found
    """
    try:
        robot = await get_robot_by_id(session, robot_id)
        if robot is None:
            raise HTTPException(status_code=404, detail=f"Robot {robot_id} not found")
        return robot
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
