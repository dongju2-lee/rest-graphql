"""REST API routes for User Service"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from models.user import UserModel
from data.repository import UserRepository


# Create router
router = APIRouter(prefix="", tags=["users"])

# Repository instance (singleton pattern)
_repository: Optional[UserRepository] = None


def get_repository() -> UserRepository:
    """Get repository instance (singleton)"""
    global _repository
    if _repository is None:
        _repository = UserRepository()
    return _repository


@router.get("/users", response_model=List[UserModel])
async def get_users(
    fields: Optional[str] = Query(None, description="Comma-separated fields to return")
):
    """
    Get all users

    Args:
        fields: Optional comma-separated list of fields (e.g., "id,name,email")

    Returns:
        List of users
    """
    repository = get_repository()

    field_list = fields.split(",") if fields else None
    users_data = await repository.get_all(fields=field_list)

    return users_data


@router.get("/users/batch", response_model=List[UserModel])
async def get_users_batch(
    ids: str = Query(..., description="Comma-separated user IDs")
):
    """
    Get multiple users by IDs (batch operation for optimization)

    Args:
        ids: Comma-separated user IDs (e.g., "1,2,3")

    Returns:
        List of users
    """
    repository = get_repository()

    try:
        user_ids = [int(id.strip()) for id in ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user IDs format")

    users_data = await repository.get_by_ids(user_ids)
    return users_data


@router.get("/users/by-site/{site_id}", response_model=List[UserModel])
async def get_users_by_site(site_id: int):
    """
    Get all users by site ID

    Args:
        site_id: Site ID

    Returns:
        List of users at the site
    """
    repository = get_repository()
    users_data = await repository.get_by_site(site_id)
    return users_data


@router.get("/users/{user_id}", response_model=UserModel)
async def get_user(user_id: int):
    """
    Get single user by ID

    Args:
        user_id: User ID

    Returns:
        User data

    Raises:
        HTTPException: 404 if user not found
    """
    repository = get_repository()
    user_data = await repository.get_by_id(user_id)

    if not user_data:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    return user_data
