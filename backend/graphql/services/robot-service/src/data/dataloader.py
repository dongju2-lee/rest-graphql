"""DataLoader implementation for batching queries - solves N+1 problem"""

from typing import List, Optional
from strawberry.dataloader import DataLoader

from data.repository import RobotRepository, TelemetryRepository


# ============== Robot DataLoader ==============

async def load_robots_batch(keys: List[int]) -> List[Optional[dict]]:
    """
    Batch load function for robots

    This is the key to solving N+1 problem in GraphQL.
    Instead of making N individual queries, DataLoader batches them
    into a single query.
    """
    repository = RobotRepository()
    robots = await repository.get_by_ids(keys)

    # Create a map for O(1) lookup
    robot_map = {r["id"]: r for r in robots}

    # Return in the same order as keys (important!)
    return [robot_map.get(key) for key in keys]


def get_robot_loader() -> DataLoader:
    """Create a new DataLoader instance for robots"""
    return DataLoader(load_fn=load_robots_batch)


# ============== Telemetry DataLoader ==============

async def load_telemetry_batch(keys: List[int]) -> List[Optional[dict]]:
    """
    Batch load function for telemetry

    When multiple robots request their telemetry in a single query,
    DataLoader batches all requests into one database call.
    """
    repository = TelemetryRepository()
    telemetry_list = await repository.get_by_robot_ids(keys)

    # Create a map for O(1) lookup
    telemetry_map = {t["robot_id"]: t for t in telemetry_list}

    # Return in the same order as keys (important!)
    return [telemetry_map.get(key) for key in keys]


def get_telemetry_loader() -> DataLoader:
    """Create a new DataLoader instance for telemetry"""
    return DataLoader(load_fn=load_telemetry_batch)


# ============== Context with DataLoaders ==============

class DataLoaders:
    """Container for all DataLoaders - injected into GraphQL context"""

    def __init__(self):
        self.robot_loader = get_robot_loader()
        self.telemetry_loader = get_telemetry_loader()


def get_dataloaders() -> DataLoaders:
    """Create new DataLoaders instance for a request"""
    return DataLoaders()
