"""Configuration settings for Robot Service"""

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    service_name: str = "rest-robot-service"
    environment: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8001
    num_robots: int = 500
    
    # Latency Simulation (seconds)
    latency_robot_list: float = 0.015  # 15ms
    latency_robot_single: float = 0.007  # 7ms
    latency_robot_batch: float = 0.010  # 10ms
    
    # Cross-service URLs
    user_service_url: str = "http://user-service:8000"
    
    cors_origins: list[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
