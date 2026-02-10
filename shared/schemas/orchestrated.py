from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class RobotMonitorResponse(BaseModel):
    """
    Combined robot, telemetry, and alert data for single robot monitoring.
    """
    id: str
    name: str
    model: str
    location: str
    status: str
    telemetry: Optional[dict] = None
    alerts: List[dict] = []


class DashboardRobotData(BaseModel):
    """
    Dashboard data for a single robot including telemetry and alerts.
    """
    id: str
    name: str
    model: str
    location: str
    status: str
    telemetry: Optional[dict] = None
    alerts: List[dict] = []


class CriticalAlertData(BaseModel):
    """
    Critical alert with associated robot and telemetry data.
    """
    alert_id: int
    robot_id: str
    severity: str
    message: str
    created_at: datetime
    robot: Optional[dict] = None
    telemetry: Optional[dict] = None
