from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_fastapi_instrumentator import Instrumentator
from typing import Dict, Optional

from shared.db.database import get_session, create_tables
from shared.schemas.telemetry import TelemetryResponse, TelemetryBatchRequest
from app.service import get_latest_telemetry, get_batch_telemetry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Creates database tables on startup.
    """
    await create_tables()
    yield


app = FastAPI(
    title="Telemetry Service",
    description="Provides robot telemetry data",
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


@app.get("/telemetry/{robot_id}/latest", response_model=TelemetryResponse)
async def get_latest_telemetry_for_robot(
    robot_id: str, session: AsyncSession = Depends(get_session)
):
    """
    Retrieve the latest telemetry data for a specific robot.

    Args:
        robot_id: The robot identifier

    Returns:
        Latest telemetry data

    Raises:
        404: Telemetry data not found
    """
    try:
        telemetry = await get_latest_telemetry(session, robot_id)
        if telemetry is None:
            raise HTTPException(
                status_code=404, detail=f"Telemetry data not found for robot {robot_id}"
            )
        return telemetry
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/telemetry/batch", response_model=Dict[str, Optional[TelemetryResponse]])
async def get_batch_telemetry_data(
    request: TelemetryBatchRequest, session: AsyncSession = Depends(get_session)
):
    """
    Retrieve latest telemetry data for multiple robots in batch.

    Args:
        request: Batch request containing list of robot IDs

    Returns:
        Dictionary mapping robot_id to telemetry data (None if not found)
    """
    try:
        telemetry_data = await get_batch_telemetry(session, request.robot_ids)
        return telemetry_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
