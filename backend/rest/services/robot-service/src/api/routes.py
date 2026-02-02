"""REST API routes for Robot Service"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
import httpx

from models.robot import RobotModel
from data.repository import RobotRepository
from core.config import get_settings


router = APIRouter(prefix="", tags=["robots"])

_repository: Optional[RobotRepository] = None


def get_repository() -> RobotRepository:
    """Get repository instance (singleton)"""
    global _repository
    if _repository is None:
        _repository = RobotRepository()
    return _repository


@router.get("/robots", response_model=List[RobotModel])
async def get_robots():
    """Get all robots"""
    repository = get_repository()
    robots_data = await repository.get_all()
    return robots_data


@router.get("/robots/{robot_id}", response_model=RobotModel)
async def get_robot(robot_id: int):
    """Get single robot by ID"""
    repository = get_repository()
    robot_data = await repository.get_by_id(robot_id)
    
    if not robot_data:
        raise HTTPException(status_code=404, detail=f"Robot {robot_id} not found")
    
    return robot_data


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
        except Exception as e:
            # If user service is unavailable, continue without owner info
            owner = None
    
    return {
        **robot_data,
        "owner": owner
    }
