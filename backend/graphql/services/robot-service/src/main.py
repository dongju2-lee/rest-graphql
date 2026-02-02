"""
Robot Service GraphQL Subgraph

FastAPI + Strawberry GraphQL service for robot management with DataLoader.
Part of Apollo Federation for Robot Monitoring System.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.logging import setup_logger
from schema import create_graphql_router
from data.repository import RobotRepository


# Settings and logger
settings = get_settings()
logger = setup_logger(settings.service_name, "INFO" if not settings.debug else "DEBUG")

# FastAPI app
app = FastAPI(
    title="Robot Service GraphQL",
    description="Robot management service - GraphQL Subgraph with Apollo Federation & DataLoader",
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

# GraphQL router
graphql_router = create_graphql_router()
app.include_router(graphql_router, prefix="/graphql")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    repository = RobotRepository()
    return {
        "status": "healthy",
        "service": settings.service_name,
        "total_robots": repository.get_count()
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "graphql": "/graphql",
        "graphiql": "/graphql (browser)"
    }


@app.on_event("startup")
async def startup_event():
    """Startup event"""
    logger.info(f"🚀 {settings.service_name} starting up...")
    logger.info(f"📊 Environment: {settings.environment}")
    logger.info(f"🤖 DataLoader enabled for N+1 optimization")
    logger.info(f"🌐 GraphQL endpoint: http://{settings.host}:{settings.port}/graphql")


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
