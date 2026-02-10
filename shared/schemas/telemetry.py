from pydantic import BaseModel
from datetime import datetime


class TelemetryResponse(BaseModel):
    robot_id: str
    battery_level: float
    cpu_usage: float
    temperature: float
    timestamp: datetime


class TelemetryBatchRequest(BaseModel):
    robot_ids: list[str]
