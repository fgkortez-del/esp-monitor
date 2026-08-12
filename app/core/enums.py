"""
Перечисления ESP Monitor.
"""

from __future__ import annotations

from enum import Enum


class DeviceType(str, Enum):
    """
    Тип измерительного устройства.
    """

    CLIMATE = "climate"
    SOIL_MOISTURE = "soil_moisture"


class EventLevel(str, Enum):
    """
    Уровень события.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SchemaStatus(str, Enum):
    """
    Состояние схемы базы данных.
    """

    OK = "ok"
    ERROR = "error"