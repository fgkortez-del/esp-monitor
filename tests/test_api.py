"""
Тесты HTTP API ESP Monitor.
"""

from __future__ import annotations

import sqlite3
import time

from app.core.database import Database
from app.core.enums import DeviceType
from app.core.models import Device
from app.main import create_app


# ======================================================================
# Test database
# ======================================================================

def create_test_database() -> Database:
    """
    Создать отдельную SQLite БД в памяти.
    """

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    db = Database()
    db.connection = connection
    db.initialize()

    return db


# ======================================================================
# Test application
# ======================================================================

def create_test_app():
    """
    Создать Flask-приложение с SQLite БД в памяти.
    """

    db = create_test_database()

    app = create_app(
        database=db,
    )

    app.config.update(
        TESTING=True,
    )

    return app


# ======================================================================
# POST /api/reading
# ======================================================================

def test_post_reading() -> None:
    """
    Проверить приём климатического измерения через HTTP API.
    """

    app = create_test_app()

    database = app.extensions["database"]

    cursor = database.execute(
        """
        INSERT INTO apartments
        (
            name,
            description,
            created_at,
            updated_at
        )
        VALUES (?, ?, strftime('%s', 'now'), strftime('%s', 'now'))
        """,
        (
        "api_test_apartment",
        "Apartment for API tests",
        ),
    )

    apartment_id = cursor.lastrowid

    database.commit()

    device_repository = app.extensions[
        "repositories"
    ]["device"]

    device_id = device_repository.create(
        Device(
            apartment_id=apartment_id,
            name="api_test_device",
            device_type=DeviceType.CLIMATE,
            firmware="test",
        )
    )

    database.commit()

    client = app.test_client()

    response = client.post(
        "/api/reading",
        json={
            "device": "api_test_device",
            "temperature": 24.5,
            "humidity": 42.0,
            "battery": 3.8,
        },
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data is not None
    assert data["status"] == "ok"
    assert data["reading_id"] is not None

    reading_repository = app.extensions[
        "repositories"
    ]["reading"]

    reading = reading_repository.get(
        data["reading_id"]
    )

    assert reading is not None

    assert reading.device_id == device_id
    assert reading.temperature == 24.5
    assert reading.humidity == 42.0
    assert reading.soil_moisture is None
    assert reading.battery == 3.8

    print("test_post_reading: OK")

def test_post_climate_device() -> None:
    """
    Проверить приём климатического измерения.

    Климатическое устройство должно передавать:
    temperature + humidity + battery.
    soil_moisture должен отсутствовать.
    """

    app = create_test_app()
    database = app.extensions["database"]

    cursor = database.execute(
        """
        INSERT INTO apartments
        (
            name,
            description,
            created_at,
            updated_at
        )
        VALUES (?, ?, strftime('%s', 'now'), strftime('%s', 'now'))
        """,
        (
            "api_climate_apartment",
            "Climate API test",
        ),
    )

    apartment_id = cursor.lastrowid
    database.commit()

    device_repository = app.extensions[
        "repositories"
    ]["device"]

    device_repository.create(
        Device(
            apartment_id=apartment_id,
            name="api_climate_device",
            device_type=DeviceType.CLIMATE,
            firmware="test",
        )
    )

    database.commit()

    client = app.test_client()

    response = client.post(
        "/api/reading",
        json={
            "device": "api_climate_device",
            "temperature": 24.5,
            "humidity": 42.0,
            "battery": 3.8,
        },
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data is not None
    assert data["status"] == "ok"
    assert data["reading_id"] is not None

    reading_repository = app.extensions[
        "repositories"
    ]["reading"]

    reading = reading_repository.get(
        data["reading_id"]
    )

    assert reading is not None

    assert reading.temperature == 24.5
    assert reading.humidity == 42.0
    assert reading.soil_moisture is None
    assert reading.battery == 3.8

    print("test_post_climate_device: OK")

def test_post_soil_moisture_device() -> None:
    """
    Проверить приём измерения влажности почвы.

    Устройство должно передавать:
    soil_moisture + battery.

    temperature и humidity должны отсутствовать.
    """

    app = create_test_app()
    database = app.extensions["database"]

    cursor = database.execute(
        """
        INSERT INTO apartments
        (
            name,
            description,
            created_at,
            updated_at
        )
        VALUES (?, ?, strftime('%s', 'now'), strftime('%s', 'now'))
        """,
        (
            "api_soil_apartment",
            "Soil moisture API test",
        ),
    )

    apartment_id = cursor.lastrowid
    database.commit()

    device_repository = app.extensions[
        "repositories"
    ]["device"]

    device_repository.create(
        Device(
            apartment_id=apartment_id,
            name="api_soil_device",
            device_type=DeviceType.SOIL_MOISTURE,
            firmware="test",
        )
    )

    database.commit()

    client = app.test_client()

    response = client.post(
        "/api/reading",
        json={
            "device": "api_soil_device",
            "soil_moisture": 57.5,
            "battery": 3.82,
        },
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data is not None
    assert data["status"] == "ok"
    assert data["reading_id"] is not None

    reading_repository = app.extensions[
        "repositories"
    ]["reading"]

    reading = reading_repository.get(
        data["reading_id"]
    )

    assert reading is not None

    assert reading.temperature is None
    assert reading.humidity is None
    assert reading.soil_moisture == 57.5
    assert reading.battery == 3.82

    print("test_post_soil_moisture_device: OK")

def test_post_reading_unknown_device() -> None:
    """
    Неизвестное устройство должно вернуть HTTP 400.
    """

    app = create_test_app()
    client = app.test_client()

    response = client.post(
        "/api/reading",
        json={
            "device": "unknown_device",
            "temperature": 24.5,
            "humidity": 42.0,
            "battery": 3.8,
        },
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data is not None
    assert "error" in data

    print("test_post_reading_unknown_device: OK")


def test_post_reading_without_device() -> None:
    """
    Отсутствие поля device должно вернуть HTTP 400.
    """

    app = create_test_app()
    client = app.test_client()

    response = client.post(
        "/api/reading",
        json={
            "temperature": 24.5,
            "humidity": 42.0,
            "battery": 3.8,
        },
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data is not None
    assert "error" in data

    print("test_post_reading_without_device: OK")


def test_post_reading_invalid_value() -> None:
    """
    Некорректное значение измерения должно вернуть HTTP 400.
    """

    app = create_test_app()
    database = app.extensions["database"]

    cursor = database.execute(
        """
        INSERT INTO apartments
        (
            name,
            description,
            created_at,
            updated_at
        )
        VALUES (?, ?, strftime('%s', 'now'), strftime('%s', 'now'))
        """,
        (
            "api_invalid_value_apartment",
            "Apartment for API tests",
        ),
    )

    apartment_id = cursor.lastrowid

    database.commit()

    device_repository = app.extensions[
        "repositories"
    ]["device"]

    device_repository.create(
        Device(
            apartment_id=apartment_id,
            name="api_invalid_device",
            device_type=DeviceType.CLIMATE,
            firmware="test",
        )
    )

    database.commit()

    client = app.test_client()

    response = client.post(
        "/api/reading",
        json={
            "device": "api_invalid_device",
            "temperature": 999,
            "humidity": 42.0,
            "battery": 3.8,
        },
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data is not None
    assert "error" in data

    print("test_post_reading_invalid_value: OK")

def test_get_readings() -> None:
    """
    Проверить получение истории измерений через HTTP API.
    """

    app = create_test_app()
    database = app.extensions["database"]

    cursor = database.execute(
        """
        INSERT INTO apartments
        (
            name,
            description,
            created_at,
            updated_at
        )
        VALUES (?, ?, strftime('%s', 'now'), strftime('%s', 'now'))
        """,
        (
            "api_history_apartment",
            "Apartment for API tests",
        ),
    )

    apartment_id = cursor.lastrowid
    database.commit()

    device_repository = app.extensions[
        "repositories"
    ]["device"]

    device_repository.create(
        Device(
            apartment_id=apartment_id,
            name="api_history_device",
            device_type=DeviceType.CLIMATE,
            firmware="test",
        )
    )

    database.commit()

    service = app.extensions[
        "services"
    ]["reading"]

    service.receive(
        device_name="api_history_device",
        temperature=24.5,
        humidity=42.0,
        battery=3.8,
    )

    time.sleep(1)

    service.receive(
        device_name="api_history_device",
        temperature=25.5,
        humidity=43.0,
        battery=3.7,
    )

    client = app.test_client()

    response = client.get(
        "/api/readings?device=api_history_device&limit=100"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data is not None
    assert data["device"] == "api_history_device"
    assert data["count"] == 2

    readings = data["readings"]

    assert len(readings) == 2

    assert readings[0]["temperature"] == 25.5
    assert readings[0]["humidity"] == 43.0
    assert readings[0]["battery"] == 3.7

    assert readings[1]["temperature"] == 24.5
    assert readings[1]["humidity"] == 42.0
    assert readings[1]["battery"] == 3.8

    assert readings[0]["soil_moisture"] is None
    assert readings[1]["soil_moisture"] is None

    assert readings[0]["timestamp"] is not None
    assert readings[1]["timestamp"] is not None

    print("test_get_readings: OK")

# ======================================================================
# GET /api/devices
# ======================================================================

def test_get_devices() -> None:
    """
    Проверить получение списка устройств
    в едином JSON-формате.
    """

    app = create_test_app()
    database = app.extensions["database"]

    # --------------------------------------------------------------
    # Apartment
    # --------------------------------------------------------------

    cursor = database.execute(
        """
        INSERT INTO apartments
        (
            name,
            description,
            created_at,
            updated_at
        )
        VALUES (?, ?, strftime('%s', 'now'), strftime('%s', 'now'))
        """,
        (
            "api_devices_apartment",
            "Apartment for devices API test",
        ),
    )

    apartment_id = cursor.lastrowid

    database.commit()

    # --------------------------------------------------------------
    # Device
    # --------------------------------------------------------------

    device_repository = app.extensions[
        "repositories"
    ]["device"]

    device_id = device_repository.create(
        Device(
            apartment_id=apartment_id,
            name="api_devices_device",
            device_type=DeviceType.CLIMATE,
            firmware="test",
            description="Test climate device",
        )
    )

    database.commit()

    # --------------------------------------------------------------
    # Reading
    # --------------------------------------------------------------

    service = app.extensions[
        "services"
    ]["reading"]

    service.receive(
        device_name="api_devices_device",
        temperature=23.5,
        humidity=45.0,
        battery=3.8,
    )

    # --------------------------------------------------------------
    # Request
    # --------------------------------------------------------------

    client = app.test_client()

    response = client.get(
        "/api/devices"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data is not None

    # --------------------------------------------------------------
    # Root structure
    # --------------------------------------------------------------

    assert "count" in data
    assert "devices" in data

    assert isinstance(
        data["count"],
        int,
    )

    assert isinstance(
        data["devices"],
        list,
    )

    assert data["count"] == 1
    assert len(data["devices"]) == 1

    # --------------------------------------------------------------
    # Device structure
    # --------------------------------------------------------------

    device = data["devices"][0]

    assert device["id"] == device_id
    assert device["name"] == "api_devices_device"
    assert device["serial"] is None
    assert device["description"] == "Test climate device"
    assert device["firmware"] == "test"

    assert device["type"] == "climate"

    assert device["last_seen"] is not None

    # --------------------------------------------------------------
    # Latest reading
    # --------------------------------------------------------------

    latest = device["latest"]

    assert latest is not None

    assert latest["device_id"] == device_id
    assert latest["temperature"] == 23.5
    assert latest["humidity"] == 45.0
    assert latest["soil_moisture"] is None
    assert latest["battery"] == 3.8
    assert latest["timestamp"] is not None

    print("test_get_devices: OK")

def test_get_devices_by_type() -> None:
    """
    Проверить типы устройств в GET /api/devices.
    """

    app = create_test_app()
    database = app.extensions["database"]

    # --------------------------------------------------------------
    # Apartment
    # --------------------------------------------------------------

    cursor = database.execute(
        """
        INSERT INTO apartments
        (
            name,
            description,
            created_at,
            updated_at
        )
        VALUES (?, ?, strftime('%s', 'now'), strftime('%s', 'now'))
        """,
        (
            "api_devices_type_apartment",
            "API devices type test",
        ),
    )

    apartment_id = cursor.lastrowid
    database.commit()

    # --------------------------------------------------------------
    # Devices
    # --------------------------------------------------------------

    device_repository = app.extensions[
        "repositories"
    ]["device"]

    climate_id = device_repository.create(
        Device(
            apartment_id=apartment_id,
            name="api_devices_climate",
            device_type=DeviceType.CLIMATE,
            firmware="test",
        )
    )

    soil_id = device_repository.create(
        Device(
            apartment_id=apartment_id,
            name="api_devices_soil",
            device_type=DeviceType.SOIL_MOISTURE,
            firmware="test",
        )
    )

    database.commit()

    # --------------------------------------------------------------
    # Readings
    # --------------------------------------------------------------

    service = app.extensions[
        "services"
    ]["reading"]

    service.receive(
        device_name="api_devices_climate",
        temperature=23.5,
        humidity=45.0,
        battery=3.8,
    )

    service.receive(
        device_name="api_devices_soil",
        soil_moisture=61.5,
        battery=3.82,
    )

    # --------------------------------------------------------------
    # Request
    # --------------------------------------------------------------

    client = app.test_client()

    response = client.get(
        "/api/devices"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data is not None
    assert "devices" in data

    devices = data["devices"]

    # --------------------------------------------------------------
    # Find devices
    # --------------------------------------------------------------

    climate = next(
        device
        for device in devices
        if device["id"] == climate_id
    )

    soil = next(
        device
        for device in devices
        if device["id"] == soil_id
    )

    # --------------------------------------------------------------
    # Climate
    # --------------------------------------------------------------

    assert climate["type"] == "climate"
    assert climate["name"] == "api_devices_climate"

    assert climate["latest"] is not None

    assert climate["latest"]["temperature"] == 23.5
    assert climate["latest"]["humidity"] == 45.0
    assert climate["latest"]["soil_moisture"] is None
    assert climate["latest"]["battery"] == 3.8

    # --------------------------------------------------------------
    # Soil moisture
    # --------------------------------------------------------------

    assert soil["type"] == "soil_moisture"
    assert soil["name"] == "api_devices_soil"

    assert soil["latest"] is not None

    assert soil["latest"]["temperature"] is None
    assert soil["latest"]["humidity"] is None
    assert soil["latest"]["soil_moisture"] == 61.5
    assert soil["latest"]["battery"] == 3.82

    print("test_get_devices_by_type: OK")

def test_get_device_by_id_by_type() -> None:
    """
    Проверить типы устройств в GET /api/devices/<id>.
    """

    app = create_test_app()
    database = app.extensions["database"]

    # --------------------------------------------------------------
    # Apartment
    # --------------------------------------------------------------

    cursor = database.execute(
        """
        INSERT INTO apartments
        (
            name,
            description,
            created_at,
            updated_at
        )
        VALUES (?, ?, strftime('%s', 'now'), strftime('%s', 'now'))
        """,
        (
            "api_single_type_apartment",
            "API single device type test",
        ),
    )

    apartment_id = cursor.lastrowid
    database.commit()

    # --------------------------------------------------------------
    # Climate device
    # --------------------------------------------------------------

    device_repository = app.extensions[
        "repositories"
    ]["device"]

    climate_id = device_repository.create(
        Device(
            apartment_id=apartment_id,
            name="api_single_climate",
            device_type=DeviceType.CLIMATE,
            firmware="test",
        )
    )

    soil_id = device_repository.create(
        Device(
            apartment_id=apartment_id,
            name="api_single_soil",
            device_type=DeviceType.SOIL_MOISTURE,
            firmware="test",
        )
    )

    database.commit()

    # --------------------------------------------------------------
    # Readings
    # --------------------------------------------------------------

    service = app.extensions[
        "services"
    ]["reading"]

    service.receive(
        device_name="api_single_climate",
        temperature=22.5,
        humidity=48.0,
        battery=3.75,
    )

    service.receive(
        device_name="api_single_soil",
        soil_moisture=58.5,
        battery=3.81,
    )

    # --------------------------------------------------------------
    # HTTP client
    # --------------------------------------------------------------

    client = app.test_client()

    # --------------------------------------------------------------
    # Climate
    # --------------------------------------------------------------

    response = client.get(
        f"/api/devices/{climate_id}"
    )

    assert response.status_code == 200

    climate = response.get_json()

    assert climate is not None

    assert climate["id"] == climate_id
    assert climate["name"] == "api_single_climate"
    assert climate["type"] == "climate"

    assert climate["latest"] is not None

    assert climate["latest"]["temperature"] == 22.5
    assert climate["latest"]["humidity"] == 48.0
    assert climate["latest"]["soil_moisture"] is None
    assert climate["latest"]["battery"] == 3.75

    # --------------------------------------------------------------
    # Soil moisture
    # --------------------------------------------------------------

    response = client.get(
        f"/api/devices/{soil_id}"
    )

    assert response.status_code == 200

    soil = response.get_json()

    assert soil is not None

    assert soil["id"] == soil_id
    assert soil["name"] == "api_single_soil"
    assert soil["type"] == "soil_moisture"

    assert soil["latest"] is not None

    assert soil["latest"]["temperature"] is None
    assert soil["latest"]["humidity"] is None
    assert soil["latest"]["soil_moisture"] == 58.5
    assert soil["latest"]["battery"] == 3.81

    print("test_get_device_by_id_by_type: OK")

# ======================================================================
# Main
# ======================================================================

if __name__ == "__main__":
    test_post_reading()
    test_post_reading_unknown_device()
    test_post_reading_without_device()
    test_post_reading_invalid_value()
    test_get_readings()
    test_get_devices()
    test_post_climate_device()
    test_post_soil_moisture_device()
    test_get_devices_by_type()
    test_get_device_by_id_by_type()

    print("ALL API TESTS: OK")