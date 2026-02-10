from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_fastapi_instrumentator import Instrumentator
from typing import List, Dict, Any

from shared.db.database import get_session, create_tables
from shared.schemas.robot import RobotResponse
from app.service import get_all_robots, get_robot_by_id
from app.orchestrator import (
    get_dashboard_data,
    get_robot_monitor_data,
    get_critical_alerts_with_context,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Creates database tables on startup.
    """
    await create_tables()
    yield


app = FastAPI(
    title="Robot Service (Orchestrated)",
    description="Provides robot data with orchestration capabilities",
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
    try:
        robots = await get_all_robots(session)
        return robots
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Static routes MUST come before parameterized routes
@app.get("/robots/dashboard", response_model=List[Dict[str, Any]])
async def get_dashboard(session: AsyncSession = Depends(get_session)):
    """
    Get dashboard data for all robots with telemetry and alerts.
    Demonstrates N+1 problem: 1 + 15 + 15 = 31 calls.
    """
    try:
        dashboard_data = await get_dashboard_data(session)
        return dashboard_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/robots/alerts/critical", response_model=List[Dict[str, Any]])
async def get_critical_alerts(session: AsyncSession = Depends(get_session)):
    """
    Get all critical alerts with robot and telemetry context.
    Demonstrates N+1 problem: 2N+1 calls for N critical alerts.
    """
    try:
        alerts_data = await get_critical_alerts_with_context(session)
        return alerts_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/robots/{robot_id}", response_model=RobotResponse)
async def get_robot(robot_id: str, session: AsyncSession = Depends(get_session)):
    try:
        robot = await get_robot_by_id(session, robot_id)
        if robot is None:
            raise HTTPException(status_code=404, detail=f"Robot {robot_id} not found")
        return robot
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/robots/{robot_id}/monitor", response_model=Dict[str, Any])
async def get_robot_monitor(robot_id: str, session: AsyncSession = Depends(get_session)):
    """Get monitoring data for a single robot. Makes 3 separate calls."""
    try:
        monitor_data = await get_robot_monitor_data(session, robot_id)
        if monitor_data is None:
            raise HTTPException(status_code=404, detail=f"Robot {robot_id} not found")
        return monitor_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
