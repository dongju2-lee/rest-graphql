"""DataLoader implementation for batching robot queries"""

from typing import List
from strawberry.dataloader import DataLoader

from data.repository import RobotRepository


async def load_robots_batch(keys: List[int]) -> List[dict]:
    """
    Batch load function for robots
    
    This is the key to solving N+1 problem in GraphQL.
    Instead of making N individual queries, DataLoader batches them
    into a single query.
    
    Args:
        keys: List of robot IDs to load
    
    Returns:
        List of robot dictionaries in the same order as keys
    """
    repository = RobotRepository()
    robots = await repository.get_by_ids(keys)
    
    # Create a map for O(1) lookup
    robot_map = {r["id"]: r for r in robots}
    
    # Return in the same order as keys (important!)
    return [robot_map.get(key) for key in keys]


def get_robot_loader() -> DataLoader:
    """
    Create a new DataLoader instance for robots
    
    Usage:
        loader = get_robot_loader()
        robot = await loader.load(robot_id)
    """
    return DataLoader(load_fn=load_robots_batch)
