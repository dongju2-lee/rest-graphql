"""
REST Site Service - Production-grade implementation

FastAPI service for site management with Clean Architecture.
For performance comparison with GraphQL.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.logging import setup_logger
from api.routes import router
from data.repository import SiteRepository


settings = get_settings()
logger = setup_logger(settings.service_name, "INFO" if not settings.debug else "DEBUG")

app = FastAPI(
    title="REST Site Service",
    description="Site management REST API - Production-grade with Clean Architecture",
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
    repository = SiteRepository()
    return {
        "status": "healthy",
        "service": settings.service_name,
        "total_sites": repository.get_count()
    }


@app.get("/")
async def root():
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "architecture": "Clean Architecture (REST)",
        "endpoints": ["/sites", "/sites/{id}", "/sites/batch"]
    }


@app.on_event("startup")
async def startup_event():
    logger.info(f"🚀 {settings.service_name} starting up...")
    logger.info(f"📊 Environment: {settings.environment}")
    logger.info(f"🏗️ Architecture: Clean Architecture")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"🛑 {settings.service_name} shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=settings.debug)
