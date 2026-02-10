from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator

from .config import ROBOT_SERVICE_URL

http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=30.0)
    yield
    await http_client.aclose()


app = FastAPI(title="REST Gateway", lifespan=lifespan)

Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/fleet/dashboard")
async def fleet_dashboard() -> Any:
    """
    Proxy to Robot Service orchestration endpoint.
    Robot Service will handle N+1 calls to other services.
    """
    if http_client is None:
        raise HTTPException(status_code=500, detail="HTTP client not initialized")

    try:
        response = await http_client.get(f"{ROBOT_SERVICE_URL}/robots/dashboard")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")


@app.get("/api/robots/{robot_id}/monitor")
async def robot_monitor(robot_id: str) -> Any:
    """
    Proxy to Robot Service monitor endpoint.
    Robot Service will fetch telemetry and alerts.
    """
    if http_client is None:
        raise HTTPException(status_code=500, detail="HTTP client not initialized")

    try:
        response = await http_client.get(
            f"{ROBOT_SERVICE_URL}/robots/{robot_id}/monitor"
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")


@app.get("/api/alerts/critical")
async def critical_alerts() -> Any:
    """
    Proxy to Robot Service critical alerts endpoint.
    Robot Service will orchestrate data from alert and telemetry services.
    """
    if http_client is None:
        raise HTTPException(status_code=500, detail="HTTP client not initialized")

    try:
        response = await http_client.get(f"{ROBOT_SERVICE_URL}/robots/alerts/critical")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")
