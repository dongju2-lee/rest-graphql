"""GraphQL types for Robot Service"""

from typing import Optional, TYPE_CHECKING
import strawberry

if TYPE_CHECKING:
    from strawberry.types import Info


@strawberry.type
class Telemetry:
    """Telemetry data for a robot"""

    robot_id: int
    cpu: float
    memory: float
    disk: float
    temperature: float
    error_count: int
    timestamp: str

    @classmethod
    def from_dict(cls, data: dict) -> "Telemetry":
        """Create Telemetry from dictionary"""
        return cls(
            robot_id=data["robot_id"],
            cpu=data["cpu"],
            memory=data["memory"],
            disk=data["disk"],
            temperature=data["temperature"],
            error_count=data["error_count"],
            timestamp=data["timestamp"]
        )


@strawberry.federation.type(keys=["id"], extend=True)
class User:
    """Extended User type (reference from user-service)"""
    id: strawberry.ID = strawberry.federation.field(external=True)

    @strawberry.field(description="Robots owned by this user")
    async def robots(self, info: "Info") -> list["Robot"]:
        """Get all robots owned by this user"""
        from data.repository import RobotRepository

        repository = RobotRepository()
        robots_data = await repository.get_by_owner(int(self.id))
        return [Robot.from_dict(r) for r in robots_data]


@strawberry.federation.type(keys=["id"], extend=True)
class Site:
    """Extended Site type (reference from site-service)"""
    id: strawberry.ID = strawberry.federation.field(external=True)

    @strawberry.field(description="Robots at this site")
    async def robots(self, info: "Info") -> list["Robot"]:
        """Get all robots at this site"""
        from data.repository import RobotRepository

        repository = RobotRepository()
        robots_data = await repository.get_by_site(int(self.id))
        return [Robot.from_dict(r) for r in robots_data]


@strawberry.federation.type(keys=["id"])
class Robot:
    """Robot GraphQL type with Federation support"""

    id: strawberry.ID
    name: str
    model: str
    status: str
    owner_id: int
    site_id: int
    battery: int
    last_maintenance: Optional[str] = None
    location: Optional[str] = None

    @strawberry.field(description="Owner of this robot")
    def owner(self) -> User:
        """Get the owner of this robot (returns User reference)"""
        return User(id=strawberry.ID(str(self.owner_id)))

    @strawberry.field(description="Site where this robot is located")
    def site(self) -> Site:
        """Get the site of this robot (returns Site reference)"""
        return Site(id=strawberry.ID(str(self.site_id)))

    @strawberry.field(description="Telemetry data for this robot")
    async def telemetry(self, info: "Info") -> Optional[Telemetry]:
        """
        Get telemetry data for this robot.
        Uses DataLoader for automatic batching (N+1 solution).
        """
        # Use DataLoader from context for batching
        dataloaders = info.context.get("dataloaders")
        if dataloaders:
            telemetry_data = await dataloaders.telemetry_loader.load(int(self.id))
        else:
            # Fallback if no DataLoader (e.g., in tests)
            from data.repository import TelemetryRepository
            repository = TelemetryRepository()
            telemetry_data = await repository.get_by_robot_id(int(self.id))

        if not telemetry_data:
            return None

        return Telemetry.from_dict(telemetry_data)

    @classmethod
    def from_dict(cls, data: dict) -> "Robot":
        """Create Robot from dictionary"""
        return cls(
            id=strawberry.ID(str(data["id"])),
            name=data["name"],
            model=data["model"],
            status=data["status"],
            owner_id=data["owner_id"],
            site_id=data["site_id"],
            battery=data["battery"],
            last_maintenance=data.get("last_maintenance"),
            location=data.get("location")
        )

    @classmethod
    async def resolve_reference(cls, id: strawberry.ID, info: "Info") -> Optional["Robot"]:
        """Resolve Federation reference"""
        from data.repository import RobotRepository

        repository = RobotRepository()
        robot_data = await repository.get_by_id(int(id))

        if not robot_data:
            return None

        return cls.from_dict(robot_data)
