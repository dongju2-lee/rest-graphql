import os

ROBOT_SERVICE_URL = os.getenv("ROBOT_SERVICE_URL", "http://robot-service:10001")
TELEMETRY_SERVICE_URL = os.getenv(
    "TELEMETRY_SERVICE_URL", "http://telemetry-service:10002"
)
ALERT_SERVICE_URL = os.getenv("ALERT_SERVICE_URL", "http://alert-service:10003")
