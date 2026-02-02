"""REST API routes for Robot Service"""

from typing import List, Optional
import asyncio
from fastapi import APIRouter, HTTPException, Query
import httpx

from models.robot import RobotModel
from models.telemetry import TelemetryModel
from data.repository import RobotRepository, TelemetryRepository
from core.config import get_settings


router = APIRouter(prefix="", tags=["robots"])

_repository: Optional[RobotRepository] = None
_telemetry_repository: Optional[TelemetryRepository] = None


def get_repository() -> RobotRepository:
    """Get repository instance (singleton)"""
    global _repository
    if _repository is None:
        _repository = RobotRepository()
    return _repository


def get_telemetry_repository() -> TelemetryRepository:
    """Get telemetry repository instance (singleton)"""
    global _telemetry_repository
    if _telemetry_repository is None:
        _telemetry_repository = TelemetryRepository()
    return _telemetry_repository


@router.get("/robots", response_model=List[RobotModel])
async def get_robots():
    """Get all robots"""
    repository = get_repository()
    robots_data = await repository.get_all()
    return robots_data


@router.get("/robots/batch", response_model=List[RobotModel])
async def get_robots_batch(
    ids: str = Query(..., description="Comma-separated robot IDs")
):
    """Get multiple robots by IDs (batch operation)"""
    repository = get_repository()

    try:
        robot_ids = [int(id.strip()) for id in ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid robot IDs format")

    robots_data = await repository.get_by_ids(robot_ids)
    return robots_data


@router.get("/robots/by-owner/{owner_id}", response_model=List[RobotModel])
async def get_robots_by_owner(owner_id: int):
    """Get all robots by owner ID"""
    repository = get_repository()
    robots_data = await repository.get_by_owner(owner_id)
    return robots_data


@router.get("/robots/by-site/{site_id}", response_model=List[RobotModel])
async def get_robots_by_site(site_id: int):
    """Get all robots by site ID"""
    repository = get_repository()
    robots_data = await repository.get_by_site(site_id)
    return robots_data


# ============== Microservice Orchestration Endpoints ==============
# NOTE: These must be defined BEFORE /robots/{robot_id} to avoid route conflicts

@router.get("/robots/with-telemetry")
async def get_robots_with_telemetry():
    """
    Get all robots with embedded telemetry (microservice orchestration)

    This endpoint returns robots with telemetry in a single call,
    similar to how GraphQL resolves N+1 with DataLoader.
    """
    robot_repository = get_repository()
    telemetry_repository = get_telemetry_repository()

    # Get all robots and telemetry
    robots = await robot_repository.get_all()
    all_telemetry = await telemetry_repository.get_all()

    # Create telemetry map for efficient lookup
    telemetry_map = {t["robot_id"]: t for t in all_telemetry}

    # Combine robots with telemetry
    result = []
    for robot in robots:
        result.append({
            **robot,
            "telemetry": telemetry_map.get(robot["id"])
        })

    return result


@router.get("/robots/{robot_id}/with-owner")
async def get_robot_with_owner(robot_id: int):
    """
    Get robot with owner info (demonstrates cross-service call)

    This is an example of REST N+1 problem - requires 2 separate requests
    """
    repository = get_repository()
    robot_data = await repository.get_by_id(robot_id)

    if not robot_data:
        raise HTTPException(status_code=404, detail=f"Robot {robot_id} not found")

    # Cross-service call to User Service
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        try:
            owner_response = await client.get(
                f"{settings.user_service_url}/users/{robot_data['owner_id']}",
                timeout=5.0
            )
            owner = owner_response.json() if owner_response.status_code == 200 else None
        except Exception:
            owner = None

    return {
        **robot_data,
        "owner": owner
    }


@router.get("/robots/{robot_id}", response_model=RobotModel)
async def get_robot(robot_id: int):
    """Get single robot by ID"""
    repository = get_repository()
    robot_data = await repository.get_by_id(robot_id)

    if not robot_data:
        raise HTTPException(status_code=404, detail=f"Robot {robot_id} not found")

    return robot_data


@router.get("/robots/{robot_id}/full")
async def get_robot_full(robot_id: int):
    """
    Get robot with all related data (owner + site + telemetry)

    This endpoint internally orchestrates calls to:
    - user-service: get owner info
    - site-service: get site info
    - local telemetry: get telemetry data

    Similar to how GraphQL Federation resolves nested relations.
    """
    robot_repository = get_repository()
    telemetry_repository = get_telemetry_repository()
    settings = get_settings()

    # Get robot
    robot_data = await robot_repository.get_by_id(robot_id)
    if not robot_data:
        raise HTTPException(status_code=404, detail=f"Robot {robot_id} not found")

    # Get telemetry locally
    telemetry = await telemetry_repository.get_by_robot_id(robot_id)

    # Parallel calls to user-service and site-service
    async with httpx.AsyncClient() as client:
        owner_task = client.get(
            f"{settings.user_service_url}/users/{robot_data['owner_id']}",
            timeout=5.0
        )
        site_task = client.get(
            f"{settings.site_service_url}/sites/{robot_data['site_id']}",
            timeout=5.0
        )

        # Execute in parallel
        owner_response, site_response = await asyncio.gather(
            owner_task, site_task, return_exceptions=True
        )

        # Parse responses
        owner = None
        if not isinstance(owner_response, Exception) and owner_response.status_code == 200:
            owner = owner_response.json()

        site = None
        if not isinstance(site_response, Exception) and site_response.status_code == 200:
            site = site_response.json()

    return {
        **robot_data,
        "owner": owner,
        "site": site,
        "telemetry": telemetry
    }


# ============== Telemetry Endpoints ==============

@router.get("/telemetry", response_model=List[TelemetryModel])
async def get_all_telemetry():
    """Get all telemetry data"""
    repository = get_telemetry_repository()
    telemetry_data = await repository.get_all()
    return telemetry_data


@router.get("/telemetry/batch", response_model=List[TelemetryModel])
async def get_telemetry_batch(
    ids: str = Query(..., description="Comma-separated robot IDs")
):
    """Get telemetry for multiple robots (batch operation)"""
    repository = get_telemetry_repository()

    try:
        robot_ids = [int(id.strip()) for id in ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid robot IDs format")

    telemetry_data = await repository.get_by_robot_ids(robot_ids)
    return telemetry_data


@router.get("/telemetry/{robot_id}", response_model=TelemetryModel)
async def get_telemetry(robot_id: int):
    """Get telemetry for a single robot"""
    repository = get_telemetry_repository()
    telemetry_data = await repository.get_by_robot_id(robot_id)

    if not telemetry_data:
        raise HTTPException(status_code=404, detail=f"Telemetry for robot {robot_id} not found")

    return telemetry_data
