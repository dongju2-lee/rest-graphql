"""Robot domain models"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class RobotModel(BaseModel):
    """Robot domain model"""
    
    # Pydantic V2 configuration
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Robot-1",
                "model": "Model-X1",
                "status": "active",
                "owner_id": 1,
                "site_id": 1,
                "battery": 85,
                "last_maintenance": "2026-01-15",
                "location": "Zone-A"
            }
        }
    )
    
    id: int
    name: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    status: str = Field(..., pattern="^(active|idle|maintenance|offline)$")
    owner_id: int
    site_id: int
    battery: int = Field(..., ge=0, le=100)
    last_maintenance: Optional[str] = None
    location: Optional[str] = None
