from pydantic import BaseModel


class RobotResponse(BaseModel):
    id: str
    name: str
    model: str
    location: str
    status: str
