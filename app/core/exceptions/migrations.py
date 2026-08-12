"""
Исключения системы миграций.
"""

from __future__ import annotations

from .base import EspMonitorError


class MigrationError(EspMonitorError):
    """Общая ошибка миграций."""


class MigrationFileError(MigrationError):
    """Ошибка чтения файла миграции."""


class MigrationChecksumError(MigrationError):
    """Контрольная сумма миграции не совпадает."""


class MigrationAlreadyApplied(MigrationError):
    """Попытка повторного применения миграции."""


class MigrationValidationError(MigrationError):
    """Ошибка проверки миграций."""