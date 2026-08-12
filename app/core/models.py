"""
Модели данных ESP Monitor.

Модели не содержат бизнес-логику и не работают
непосредственно с базой данных.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.core.enums import DeviceType, EventLevel


# ======================================================================
# Apartment
# ======================================================================

@dataclass
class Apartment:
    """
    Квартира, к которой относятся устройства.
    """

    id: int | None = None

    name: str = ""

    description: str | None = None

    created_at: datetime | None = None

    updated_at: datetime | None = None


# ======================================================================
# Device
# ======================================================================

@dataclass
class Device:
    """
    Измерительное устройство.

    Один ESP/ATtiny85 соответствует одному типу измерения.
    """

    id: int | None = None

    apartment_id: int | None = None

    name: str = ""

    serial: str | None = None

    device_type: DeviceType = DeviceType.CLIMATE

    plant_name: str | None = None

    description: str | None = None

    firmware: str | None = None

    created_at: datetime | None = None

    updated_at: datetime | None = None

    last_seen: datetime | None = None


# ======================================================================
# Reading
# ======================================================================

@dataclass
class Reading:
    """
    Одно измерение устройства.

    В зависимости от типа устройства используются
    разные поля.

    climate:
        temperature
        humidity
        battery

    soil_moisture:
        soil_moisture
        battery

    Для устройств без измерения батареи:
        battery = None
    """

    id: int | None = None

    device_id: int | None = None

    timestamp: datetime | None = None

    temperature: float | None = None

    humidity: float | None = None

    soil_moisture: float | None = None

    battery: float | None = None


# ======================================================================
# Event
# ======================================================================

@dataclass
class Event:
    """
    Системное событие устройства.
    """

    id: int | None = None

    device_id: int | None = None

    timestamp: datetime | None = None

    level: EventLevel = EventLevel.INFO

    message: str = ""


# ======================================================================
# Setting
# ======================================================================

@dataclass
class Setting:
    """
    Настройка приложения.
    """

    key: str

    value: str


# ======================================================================
# SchemaInfo
# ======================================================================

@dataclass
class SchemaInfo:
    """
    Информация о версии схемы БД.
    """

    version: int

    applied_at: datetime | None = None