"""
Исключения базы данных.
"""

from __future__ import annotations

from .base import EspMonitorError


class DatabaseError(EspMonitorError):
    """Общая ошибка базы данных."""


class DatabaseConnectionError(DatabaseError):
    """Ошибка подключения к базе данных."""


class DatabaseTransactionError(DatabaseError):
    """Ошибка выполнения транзакции."""


class DatabaseQueryError(DatabaseError):
    """Ошибка выполнения SQL-запроса."""