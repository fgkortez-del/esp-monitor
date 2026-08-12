"""
Пакет исключений проекта.
"""

from .base import EspMonitorError

from .database import (
    DatabaseConnectionError,
    DatabaseError,
    DatabaseQueryError,
    DatabaseTransactionError,
)

from .migrations import (
    MigrationAlreadyApplied,
    MigrationChecksumError,
    MigrationError,
    MigrationFileError,
    MigrationValidationError,
)

from .resources import (
    InvalidResource,
    ResourceError,
    ResourceNotFound,
)

__all__ = [
    "EspMonitorError",

    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseTransactionError",
    "DatabaseQueryError",

    "MigrationError",
    "MigrationFileError",
    "MigrationChecksumError",
    "MigrationAlreadyApplied",
    "MigrationValidationError",

    "ResourceError",
    "ResourceNotFound",
    "InvalidResource",
]