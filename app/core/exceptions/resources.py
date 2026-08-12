"""
Исключения ResourceManager.
"""

from __future__ import annotations

from .base import EspMonitorError


class ResourceError(EspMonitorError):
    """Общая ошибка ресурсов."""


class ResourceNotFound(ResourceError):
    """Запрошенный ресурс не найден."""


class InvalidResource(ResourceError):
    """Некорректный ресурс."""