"""REST API routes for Site Service"""

from typing import List, Optional
import asyncio
from fastapi import APIRouter, HTTPException, Query
import httpx

from models.site import SiteModel
from data.repository import SiteRepository
from core.config import get_settings


router = APIRouter(prefix="", tags=["sites"])

_repository: Optional[SiteRepository] = None


def get_repository() -> SiteRepository:
    """Get repository instance (singleton)"""
    global _repository
    if _repository is None:
        _repository = SiteRepository()
    return _repository


@router.get("/sites", response_model=List[SiteModel])
async def get_sites():
    """Get all sites"""
    repository = get_repository()
    sites_data = await repository.get_all()
    return sites_data


@router.get("/sites/{site_id}", response_model=SiteModel)
async def get_site(site_id: int):
    """Get single site by ID"""
    repository = get_repository()
    site_data = await repository.get_by_id(site_id)
    
    if not site_data:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found")
    
    return site_data


@router.get("/sites/batch", response_model=List[SiteModel])
async def get_sites_batch(
    ids: str = Query(..., description="Comma-separated site IDs")
):
    """Get multiple sites by IDs (batch operation)"""
    repository = get_repository()
    
    try:
        site_ids = [int(id.strip()) for id in ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid site IDs format")
    
    sites_data = await repository.get_by_ids(site_ids)
    return sites_data


# ============== Dashboard (Complex Aggregation) ==============

@router.get("/sites/{site_id}/dashboard")
async def get_site_dashboard(site_id: int):
    """
    Get site dashboard with robots, owners, and telemetry.

    This demonstrates REST's approach to complex aggregation:
    - Multiple cross-service calls
    - Manual orchestration with asyncio.gather for parallel requests
    - Client/Server-side data joining

    Compare with GraphQL's single query approach.
    """
    settings = get_settings()
    repository = get_repository()

    # 1. Get site info
    site_data = await repository.get_by_id(site_id)
    if not site_data:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 2. Get robots at this site (from robot-service)
        try:
            robots_response = await client.get(
                f"{settings.robot_service_url}/robots/by-site/{site_id}"
            )
            robots = robots_response.json() if robots_response.status_code == 200 else []
        except Exception:
            robots = []

        if not robots:
            return {
                **site_data,
                "robots": [],
                "stats": {"total_robots": 0, "active_robots": 0, "avg_battery": 0}
            }

        # 3. Parallel batch calls for owners and telemetry
        robot_ids = [r["id"] for r in robots]
        owner_ids = list(set(r["owner_id"] for r in robots))

        # Batch calls in parallel (REST optimization)
        owners_task = client.get(
            f"{settings.user_service_url}/users/batch",
            params={"ids": ",".join(map(str, owner_ids))}
        )
        telemetry_task = client.get(
            f"{settings.robot_service_url}/telemetry/batch",
            params={"ids": ",".join(map(str, robot_ids))}
        )

        try:
            owners_response, telemetry_response = await asyncio.gather(
                owners_task, telemetry_task, return_exceptions=True
            )

            owners = owners_response.json() if not isinstance(owners_response, Exception) and owners_response.status_code == 200 else []
            telemetry_list = telemetry_response.json() if not isinstance(telemetry_response, Exception) and telemetry_response.status_code == 200 else []
        except Exception:
            owners = []
            telemetry_list = []

    # 4. Join data (manual merge)
    owner_map = {o["id"]: o for o in owners}
    telemetry_map = {t["robot_id"]: t for t in telemetry_list}

    robots_with_details = []
    for robot in robots:
        robots_with_details.append({
            **robot,
            "owner": owner_map.get(robot["owner_id"]),
            "telemetry": telemetry_map.get(robot["id"])
        })

    # 5. Calculate stats
    active_count = sum(1 for r in robots if r["status"] == "active")
    avg_battery = sum(r["battery"] for r in robots) / len(robots) if robots else 0

    return {
        **site_data,
        "robots": robots_with_details,
        "stats": {
            "total_robots": len(robots),
            "active_robots": active_count,
            "avg_battery": round(avg_battery, 1)
        }
    }
