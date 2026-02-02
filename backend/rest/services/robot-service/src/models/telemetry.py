"""Telemetry domain models"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class TelemetryModel(BaseModel):
    """Telemetry domain model - same structure for REST and GraphQL"""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "robot_id": 1,
                "cpu": 45.5,
                "memory": 62.3,
                "disk": 78.1,
                "temperature": 42.0,
                "error_count": 0,
                "timestamp": "2024-02-02T12:00:00Z"
            }
        }
    )

    robot_id: int
    cpu: float = Field(..., ge=0, le=100, description="CPU usage percentage")
    memory: float = Field(..., ge=0, le=100, description="Memory usage percentage")
    disk: float = Field(..., ge=0, le=100, description="Disk usage percentage")
    temperature: float = Field(..., description="Temperature in Celsius")
    error_count: int = Field(..., ge=0, description="Number of errors")
    timestamp: str = Field(..., description="ISO format timestamp")
