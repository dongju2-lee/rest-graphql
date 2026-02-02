"""Configuration settings for Site Service"""

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "site-service-graphql"
    environment: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8002
    num_sites: int = 5
    
    # Latency Simulation (seconds)
    latency_site_list: float = 0.008  # 8ms
    latency_site_single: float = 0.004  # 4ms
    latency_site_batch: float = 0.006  # 6ms
    
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
