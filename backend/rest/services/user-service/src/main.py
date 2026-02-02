"""
REST User Service - Production-grade implementation

FastAPI service for user management with Clean Architecture.
For performance comparison with GraphQL.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.logging import setup_logger
from api.routes import router
from data.repository import UserRepository


# Settings and logger
settings = get_settings()
logger = setup_logger(settings.service_name, "INFO" if not settings.debug else "DEBUG")

# FastAPI app
app = FastAPI(
    title="REST User Service",
    description="User management REST API - Production-grade with Clean Architecture",
    version="1.0.0",
    debug=settings.debug
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    repository = UserRepository()
    return {
        "status": "healthy",
        "service": settings.service_name,
        "total_users": repository.get_count()
    }


# Root
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "architecture": "Clean Architecture (REST)",
        "endpoints": ["/users", "/users/{id}", "/users/batch", "/users/by-site/{site_id}"]
    }


@app.on_event("startup")
async def startup_event():
    """Startup event"""
    logger.info(f"🚀 {settings.service_name} starting up...")
    logger.info(f"📊 Environment: {settings.environment}")
    logger.info(f"🏗️ Architecture: Clean Architecture")
    logger.info(f"🌐 Endpoints: http://{settings.host}:{settings.port}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event"""
    logger.info(f"🛑 {settings.service_name} shutting down...")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
