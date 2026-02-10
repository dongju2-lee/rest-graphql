import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://fleet:fleet123@localhost:15432/robot_fleet",
)
