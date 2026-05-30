from typing import Dict, Any

# Define common types/exceptions
class RepoError(Exception):
    """Base exception for Repository layer."""
    pass

RowDict = Dict[str, Any]

# Export Repositories
from .base_repository import BaseRepository
from .audit_repository import AuditRepository
from .driver_repository import DriverRepository
from .trip_repository import TripRepository
from .trip_repo import TripRepo
from .driver_repo import DriverRepo
from .request_repo import RequestRepo
from .employee_repo import EmployeeRepo
from .admin_repo import AdminRepo
