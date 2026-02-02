"""
REST Robot Service - Production-grade implementation

FastAPI service for robot management with Clean Architecture.
Includes cross-service communication for performance comparison.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.logging import setup_logger
from api.routes import router
from data.repository import RobotRepository


settings = get_settings()
logger = setup_logger(settings.service_name, "INFO" if not settings.debug else "DEBUG")

app = FastAPI(
    title="REST Robot Service",
    description="Robot management REST API - Production-grade with Clean Architecture",
    version="1.0.0",
    debug=settings.debug
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health_check():
    repository = RobotRepository()
    return {
        "status": "healthy",
        "service": settings.service_name,
        "total_robots": repository.get_count()
    }


@app.get("/")
async def root():
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "architecture": "Clean Architecture (REST)",
        "endpoints": [
            "/robots", 
            "/robots/{id}", 
            "/robots/batch",
            "/robots/by-owner/{owner_id}",
            "/robots/by-site/{site_id}",
            "/robots/{id}/with-owner"
        ]
    }


@app.on_event("startup")
async def startup_event():
    logger.info(f"🚀 {settings.service_name} starting up...")
    logger.info(f"📊 Environment: {settings.environment}")
    logger.info(f"🏗️ Architecture: Clean Architecture")
    logger.info(f"🔗 Cross-service: {settings.user_service_url}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"🛑 {settings.service_name} shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=settings.debug)
