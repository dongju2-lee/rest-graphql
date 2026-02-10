from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Robot(Base):
    __tablename__ = "robots"

    id = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    model = Column(String(50), nullable=False)
    location = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="active")


class TelemetryData(Base):
    __tablename__ = "telemetry_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    robot_id = Column(String(20), ForeignKey("robots.id"), nullable=False)
    battery_level = Column(Float, nullable=False)
    cpu_usage = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_telemetry_robot_ts", "robot_id", timestamp.desc()),
    )


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    robot_id = Column(String(20), ForeignKey("robots.id"), nullable=False)
    severity = Column(String(20), nullable=False)
    message = Column(String(500), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_alerts_robot", "robot_id"),
        Index("idx_alerts_severity", "severity"),
    )
