"""Configuration settings for User Service"""

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Service Info
    service_name: str = "rest-user-service"
    environment: str = "development"
    debug: bool = True
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Data Configuration
    num_users: int = 100

    # Service URLs (for internal service-to-service calls)
    robot_service_url: str = "http://rest-robot-service:8001"

    # Latency Simulation (seconds)
    latency_user_list: float = 0.010  # 10ms
    latency_user_single: float = 0.005  # 5ms
    latency_user_batch: float = 0.008  # 8ms
    
    # CORS
    cors_origins: list[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get settings instance (singleton)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
