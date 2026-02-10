import os

TELEMETRY_SERVICE_URL = os.getenv(
    "TELEMETRY_SERVICE_URL", "http://telemetry-service:10002"
)
