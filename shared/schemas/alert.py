from pydantic import BaseModel
from datetime import datetime


class AlertResponse(BaseModel):
    id: int
    robot_id: str
    severity: str
    message: str
    created_at: datetime


class AlertBatchRequest(BaseModel):
    robot_ids: list[str]
