"""Site domain models (DTO)"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SiteModel(BaseModel):
    """Site domain model - DTO"""
    
    # Pydantic V2 configuration
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str = Field(..., min_length=1, max_length=100)
    location: str
    timezone: str
    capacity: int = Field(..., gt=0)
    description: Optional[str] = None
