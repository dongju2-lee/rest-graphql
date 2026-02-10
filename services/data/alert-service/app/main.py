from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_fastapi_instrumentator import Instrumentator
from typing import List, Dict

from shared.db.database import get_session, create_tables
from shared.schemas.alert import AlertResponse, AlertBatchRequest
from app.service import get_alerts_by_robot, get_critical_alerts, get_batch_alerts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Creates database tables on startup.
    """
    await create_tables()
    yield


app = FastAPI(
    title="Alert Service",
    description="Provides robot alert data",
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


# Static routes MUST come before parameterized routes
@app.get("/alerts/critical", response_model=List[AlertResponse])
async def get_critical_alerts_list(session: AsyncSession = Depends(get_session)):
    """
    Retrieve all critical severity alerts.

    Returns:
        List of critical alerts
    """
    try:
        alerts = await get_critical_alerts(session)
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/alerts/{robot_id}", response_model=List[AlertResponse])
async def get_robot_alerts(robot_id: str, session: AsyncSession = Depends(get_session)):
    try:
        alerts = await get_alerts_by_robot(session, robot_id)
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/alerts/batch", response_model=Dict[str, List[AlertResponse]])
async def get_batch_alerts_data(
    request: AlertBatchRequest, session: AsyncSession = Depends(get_session)
):
    """
    Retrieve alerts for multiple robots in batch.

    Args:
        request: Batch request containing list of robot IDs

    Returns:
        Dictionary mapping robot_id to list of alerts
    """
    try:
        alerts_data = await get_batch_alerts(session, request.robot_ids)
        return alerts_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
