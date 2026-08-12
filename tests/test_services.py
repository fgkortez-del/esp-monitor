"""
Тесты сервисного слоя.
"""

from __future__ import annotations

import sqlite3

from app.core.database import Database
from app.core.enums import DeviceType
from app.core.models import Device
from app.repositories.device_repository import DeviceRepository
from app.repositories.event_repository import EventRepository
from app.repositories.reading_repository import ReadingRepository
from app.services.reading_service import ReadingService


def create_test_database() -> Database:
    """
    Создать отдельную SQLite БД для тестов.
    """

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    db = Database()

    db.connection = connection

    db.initialize()

    return db


def create_service(
    db: Database,
) -> ReadingService:
    """
    Создать ReadingService с репозиториями.
    """

    return ReadingService(
        database=db,
        device_repository=DeviceRepository(db),
        reading_repository=ReadingRepository(db),
        event_repository=EventRepository(db),
    )


def create_device(
    db: Database,
    *,
    name: str,
    device_type: DeviceType,
) -> int:
    """
    Создать тестовое устройство.
    """

    repository = DeviceRepository(db)

    device_id = repository.create(
        Device(
            apartment_id=1,
            name=name,
            device_type=device_type,
            firmware="test",
        )
    )

    db.commit()

    return device_id


# ======================================================================
# Successful cases
# ======================================================================


def test_receive_climate_reading() -> None:
    """
    Проверить успешное сохранение климатического измерения.
    """

    db = create_test_database()

    device_id = create_device(
        db,
        name="test_climate",
        device_type=DeviceType.CLIMATE,
    )

    service = create_service(db)

    reading = service.receive(
        device_name="test_climate",
        temperature=24.5,
        humidity=42.0,
        battery=3.8,
    )

    assert reading.id is not None
    assert reading.device_id == device_id

    assert reading.temperature == 24.5
    assert reading.humidity == 42.0
    assert reading.soil_moisture is None
    assert reading.battery == 3.8

    repository = ReadingRepository(db)

    saved = repository.get(reading.id)

    assert saved is not None

    assert saved.device_id == device_id
    assert saved.temperature == 24.5
    assert saved.humidity == 42.0
    assert saved.battery == 3.8

    assert repository.count() == 1

    print("test_receive_climate_reading: OK")


# ======================================================================
# Unknown device
# ======================================================================


def test_receive_unknown_device() -> None:
    """
    Неизвестное устройство должно быть отклонено.
    """

    db = create_test_database()

    service = create_service(db)

    repository = ReadingRepository(db)

    before = repository.count()

    try:
        service.receive(
            device_name="unknown_device",
            temperature=24.5,
            humidity=42.0,
            battery=3.8,
        )
    except ValueError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for unknown device."
        )

    assert repository.count() == before

    print("test_receive_unknown_device: OK")


# ======================================================================
# Climate validation
# ======================================================================


def test_climate_requires_temperature_or_humidity() -> None:
    """
    Климатическое устройство должно передать
    температуру или влажность.
    """

    db = create_test_database()

    create_device(
        db,
        name="test_climate",
        device_type=DeviceType.CLIMATE,
    )

    service = create_service(db)

    repository = ReadingRepository(db)

    before = repository.count()

    try:
        service.receive(
            device_name="test_climate",
            battery=3.8,
        )
    except ValueError as exc:
        assert "temperature or humidity" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError."
        )

    assert repository.count() == before

    print("test_climate_requires_temperature_or_humidity: OK")


def test_climate_rejects_soil_moisture() -> None:
    """
    Климатическое устройство не должно принимать
    soil_moisture.
    """

    db = create_test_database()

    create_device(
        db,
        name="test_climate",
        device_type=DeviceType.CLIMATE,
    )

    service = create_service(db)

    repository = ReadingRepository(db)

    before = repository.count()

    try:
        service.receive(
            device_name="test_climate",
            temperature=24.5,
            soil_moisture=50.0,
            battery=3.8,
        )
    except ValueError as exc:
        assert "soil_moisture" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError."
        )

    assert repository.count() == before

    print("test_climate_rejects_soil_moisture: OK")


# ======================================================================
# Soil moisture validation
# ======================================================================


def test_soil_moisture_requires_soil_moisture() -> None:
    """
    Датчик влажности почвы обязан передать
    soil_moisture.
    """

    db = create_test_database()

    create_device(
        db,
        name="test_soil",
        device_type=DeviceType.SOIL_MOISTURE,
    )

    service = create_service(db)

    repository = ReadingRepository(db)

    before = repository.count()

    try:
        service.receive(
            device_name="test_soil",
            battery=3.8,
        )
    except ValueError as exc:
        assert "soil_moisture" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError."
        )

    assert repository.count() == before

    print("test_soil_moisture_requires_soil_moisture: OK")


def test_soil_moisture_rejects_climate_values() -> None:
    """
    Датчик влажности почвы не должен принимать
    temperature/humidity.
    """

    db = create_test_database()

    create_device(
        db,
        name="test_soil",
        device_type=DeviceType.SOIL_MOISTURE,
    )

    service = create_service(db)

    repository = ReadingRepository(db)

    before = repository.count()

    try:
        service.receive(
            device_name="test_soil",
            soil_moisture=50.0,
            temperature=24.5,
        )
    except ValueError as exc:
        assert "temperature or humidity" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError."
        )

    assert repository.count() == before

    print("test_soil_moisture_rejects_climate_values: OK")


# ======================================================================
# Value validation
# ======================================================================


def test_temperature_out_of_range() -> None:
    """
    Температура вне допустимого диапазона должна быть отклонена.
    """

    db = create_test_database()

    create_device(
        db,
        name="test_climate",
        device_type=DeviceType.CLIMATE,
    )

    service = create_service(db)

    repository = ReadingRepository(db)

    before = repository.count()

    try:
        service.receive(
            device_name="test_climate",
            temperature=200,
        )
    except ValueError as exc:
        assert "Temperature" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError."
        )

    assert repository.count() == before

    print("test_temperature_out_of_range: OK")


def test_humidity_out_of_range() -> None:
    """
    Влажность вне диапазона 0..100 должна быть отклонена.
    """

    db = create_test_database()

    create_device(
        db,
        name="test_climate",
        device_type=DeviceType.CLIMATE,
    )

    service = create_service(db)

    repository = ReadingRepository(db)

    before = repository.count()

    try:
        service.receive(
            device_name="test_climate",
            humidity=120,
        )
    except ValueError as exc:
        assert "Humidity" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError."
        )

    assert repository.count() == before

    print("test_humidity_out_of_range: OK")


def test_soil_moisture_out_of_range() -> None:
    """
    Влажность почвы вне диапазона 0..100 должна быть отклонена.
    """

    db = create_test_database()

    create_device(
        db,
        name="test_soil",
        device_type=DeviceType.SOIL_MOISTURE,
    )

    service = create_service(db)

    repository = ReadingRepository(db)

    before = repository.count()

    try:
        service.receive(
            device_name="test_soil",
            soil_moisture=120,
        )
    except ValueError as exc:
        assert "Soil moisture" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError."
        )

    assert repository.count() == before

    print("test_soil_moisture_out_of_range: OK")


def test_battery_out_of_range() -> None:
    """
    Напряжение батареи вне диапазона 0..6 В
    должно быть отклонено.
    """

    db = create_test_database()

    create_device(
        db,
        name="test_climate",
        device_type=DeviceType.CLIMATE,
    )

    service = create_service(db)

    repository = ReadingRepository(db)

    before = repository.count()

    try:
        service.receive(
            device_name="test_climate",
            temperature=24.5,
            battery=7.0,
        )
    except ValueError as exc:
        assert "Battery voltage" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError."
        )

    assert repository.count() == before

    print("test_battery_out_of_range: OK")


# ======================================================================
# Normalization
# ======================================================================


def test_string_values_are_normalized() -> None:
    """
    Строковые числовые значения должны преобразовываться в float.
    """

    db = create_test_database()

    create_device(
        db,
        name="test_climate",
        device_type=DeviceType.CLIMATE,
    )

    service = create_service(db)

    reading = service.receive(
        device_name="test_climate",
        temperature="24.5",
        humidity="42.0",
        battery="3.8",
    )

    assert reading.temperature == 24.5
    assert reading.humidity == 42.0
    assert reading.battery == 3.8

    print("test_string_values_are_normalized: OK")


def test_invalid_string_is_rejected() -> None:
    """
    Некорректное строковое значение должно быть отклонено.
    """

    db = create_test_database()

    create_device(
        db,
        name="test_climate",
        device_type=DeviceType.CLIMATE,
    )

    service = create_service(db)

    repository = ReadingRepository(db)

    before = repository.count()

    try:
        service.receive(
            device_name="test_climate",
            temperature="abc",
        )
    except ValueError as exc:
        assert "must be a number" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError."
        )

    assert repository.count() == before

    print("test_invalid_string_is_rejected: OK")


# ======================================================================
# Main
# ======================================================================


if __name__ == "__main__":
    test_receive_climate_reading()
    test_receive_unknown_device()

    test_climate_requires_temperature_or_humidity()
    test_climate_rejects_soil_moisture()

    test_soil_moisture_requires_soil_moisture()
    test_soil_moisture_rejects_climate_values()

    test_temperature_out_of_range()
    test_humidity_out_of_range()
    test_soil_moisture_out_of_range()
    test_battery_out_of_range()

    test_string_values_are_normalized()
    test_invalid_string_is_rejected()

    print("ALL SERVICE TESTS: OK")