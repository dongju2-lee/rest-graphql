"""Seed data: 15 robots, telemetry per robot, alerts per robot."""
import asyncio
import random
from datetime import datetime, timedelta
from sqlalchemy import select
from shared.db.database import engine, async_session, create_tables
from shared.db.models import Robot, TelemetryData, Alert

ROBOT_MODELS = ["AGV-X100", "AGV-X200", "AGV-X300", "ARM-A1", "ARM-A2"]
LOCATIONS = [
    "Building-1-Floor-1", "Building-1-Floor-2", "Building-2-Floor-1",
    "Building-2-Floor-2", "Building-3-Floor-1",
]
ALERT_TYPES = [
    ("critical", "Temperature exceeds threshold"),
    ("critical", "Battery critically low"),
    ("warning", "Battery below 30%"),
    ("warning", "CPU usage high"),
    ("info", "Scheduled maintenance due"),
    ("info", "Firmware update available"),
]


async def seed():
    await create_tables()

    async with async_session() as session:
        existing = await session.execute(select(Robot).limit(1))
        if existing.scalar_one_or_none():
            print("Seed data already exists, skipping.")
            return

        now = datetime.utcnow()

        # 15 robots
        robots = []
        for i in range(1, 16):
            robot = Robot(
                id=f"robot-{i:03d}",
                name=f"AGV-{chr(64 + i)}",
                model=random.choice(ROBOT_MODELS),
                location=random.choice(LOCATIONS),
                status="active" if i <= 13 else "maintenance",
            )
            robots.append(robot)
        session.add_all(robots)
        await session.flush()

        # telemetry: 100 records per robot (last 100 minutes)
        telemetry_records = []
        for robot in robots:
            for j in range(100):
                ts = now - timedelta(minutes=100 - j)
                telemetry_records.append(TelemetryData(
                    robot_id=robot.id,
                    battery_level=round(random.uniform(10.0, 100.0), 1),
                    cpu_usage=round(random.uniform(5.0, 95.0), 1),
                    temperature=round(random.uniform(25.0, 75.0), 1),
                    timestamp=ts,
                ))
        session.add_all(telemetry_records)

        # alerts: 5-10 per robot, some critical
        alert_records = []
        for robot in robots:
            num_alerts = random.randint(5, 10)
            for j in range(num_alerts):
                severity, message = random.choice(ALERT_TYPES)
                alert_records.append(Alert(
                    robot_id=robot.id,
                    severity=severity,
                    message=f"{message} on {robot.name}",
                    created_at=now - timedelta(minutes=random.randint(1, 1440)),
                ))
        session.add_all(alert_records)

        await session.commit()
        print(f"Seeded: {len(robots)} robots, {len(telemetry_records)} telemetry, {len(alert_records)} alerts")


if __name__ == "__main__":
    asyncio.run(seed())
