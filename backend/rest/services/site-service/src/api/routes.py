"""REST API routes for Site Service"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from models.site import SiteModel
from data.repository import SiteRepository


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
