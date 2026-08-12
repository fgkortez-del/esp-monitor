"""
Тесты репозиториев ESP Monitor.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

from app.core.database import Database
from app.core.enums import DeviceType, EventLevel
from app.core.models import Device, Event, Reading
from app.repositories.device_repository import DeviceRepository
from app.repositories.event_repository import EventRepository
from app.repositories.reading_repository import ReadingRepository


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
# Helpers
# ======================================================================


def create_device(
    repository: DeviceRepository,
    *,
    name: str,
    device_type: DeviceType = DeviceType.CLIMATE,
    apartment_id: int = 1,
    serial: str | None = None,
    plant_name: str | None = None,
) -> int:
    """
    Создать тестовое устройство.
    """

    return repository.create(
        Device(
            apartment_id=apartment_id,
            name=name,
            serial=serial,
            device_type=device_type,
            plant_name=plant_name,
            description="test device",
            firmware="test",
        )
    )

def create_apartment(
    db: Database,
    *,
    apartment_id: int,
    name: str,
) -> None:
    """
    Создать тестовую квартиру.
    """

    now = int(datetime.now(UTC).timestamp())

    db.execute(
        """
        INSERT INTO apartments
        (
            id,
            name,
            description,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            apartment_id,
            name,
            "test apartment",
            now,
            now,
        ),
    )

    db.commit()

# ======================================================================
# DeviceRepository
# ======================================================================


def test_device_create() -> None:
    db = create_test_database()
    repository = DeviceRepository(db)

    device_id = create_device(
        repository,
        name="device_1",
    )

    db.commit()

    device = repository.get(device_id)

    assert device is not None
    assert device.id == device_id
    assert device.apartment_id == 1
    assert device.name == "device_1"
    assert device.device_type == DeviceType.CLIMATE
    assert device.firmware == "test"

    assert device.created_at is not None
    assert device.updated_at is not None

    print("test_device_create: OK")


def test_device_get_missing() -> None:
    db = create_test_database()
    repository = DeviceRepository(db)

    assert repository.get(999999) is None

    print("test_device_get_missing: OK")


def test_device_get_by_name() -> None:
    db = create_test_database()
    repository = DeviceRepository(db)

    device_id = create_device(
        repository,
        name="named_device",
    )

    db.commit()

    device = repository.get_by_name("named_device")

    assert device is not None
    assert device.id == device_id
    assert device.name == "named_device"

    assert repository.get_by_name("missing") is None

    print("test_device_get_by_name: OK")


def test_device_get_by_serial() -> None:
    db = create_test_database()
    repository = DeviceRepository(db)

    device_id = create_device(
        repository,
        name="serial_device",
        serial="ABC-123",
    )

    db.commit()

    device = repository.get_by_serial("ABC-123")

    assert device is not None
    assert device.id == device_id
    assert device.serial == "ABC-123"

    assert repository.get_by_serial("UNKNOWN") is None

    print("test_device_get_by_serial: OK")


def test_device_get_all() -> None:
    db = create_test_database()
    repository = DeviceRepository(db)

    create_device(repository, name="device_b")
    create_device(repository, name="device_a")
    create_device(repository, name="device_c")

    db.commit()

    devices = repository.get_all()

    assert len(devices) == 3

    assert [device.name for device in devices] == [
        "device_a",
        "device_b",
        "device_c",
    ]

    print("test_device_get_all: OK")

def test_device_get_for_apartment() -> None:
    db = create_test_database()
    repository = DeviceRepository(db)

    # Квартира №1 уже создаётся Database.initialize()
    create_apartment(
        db,
        apartment_id=2,
        name="Квартира №2",
    )

    create_device(
        repository,
        name="flat1_device",
        apartment_id=1,
    )

    create_device(
        repository,
        name="flat2_device",
        apartment_id=2,
    )

    db.commit()

    apartment_1 = repository.get_for_apartment(1)
    apartment_2 = repository.get_for_apartment(2)

    assert len(apartment_1) == 1
    assert apartment_1[0].name == "flat1_device"

    assert len(apartment_2) == 1
    assert apartment_2[0].name == "flat2_device"

    print("test_device_get_for_apartment: OK")


def test_device_exists() -> None:
    db = create_test_database()
    repository = DeviceRepository(db)

    create_device(
        repository,
        name="existing",
    )

    db.commit()

    assert repository.exists("existing") is True
    assert repository.exists("missing") is False

    print("test_device_exists: OK")


def test_device_count() -> None:
    db = create_test_database()
    repository = DeviceRepository(db)

    assert repository.count() == 0

    create_device(repository, name="device_1")
    create_device(repository, name="device_2")

    db.commit()

    assert repository.count() == 2

    print("test_device_count: OK")


def test_device_update() -> None:
    db = create_test_database()
    repository = DeviceRepository(db)

    device_id = create_device(
        repository,
        name="before",
        serial="OLD",
    )

    db.commit()

    device = repository.get(device_id)

    assert device is not None

    device.name = "after"
    device.serial = "NEW"
    device.plant_name = "Rose"
    device.description = "updated"
    device.firmware = "2.0"

    repository.update(device)
    db.commit()

    updated = repository.get(device_id)

    assert updated is not None
    assert updated.name == "after"
    assert updated.serial == "NEW"
    assert updated.plant_name == "Rose"
    assert updated.description == "updated"
    assert updated.firmware == "2.0"

    print("test_device_update: OK")


def test_device_update_last_seen() -> None:
    db = create_test_database()
    repository = DeviceRepository(db)

    device_id = create_device(
        repository,
        name="last_seen_device",
    )

    db.commit()

    before = repository.get(device_id)

    assert before is not None
    assert before.last_seen is None

    repository.update_last_seen(device_id)
    db.commit()

    after = repository.get(device_id)

    assert after is not None
    assert after.last_seen is not None
    assert after.last_seen.tzinfo == UTC

    print("test_device_update_last_seen: OK")


def test_device_delete() -> None:
    db = create_test_database()
    repository = DeviceRepository(db)

    device_id = create_device(
        repository,
        name="delete_me",
    )

    db.commit()

    assert repository.get(device_id) is not None

    repository.delete(device_id)
    db.commit()

    assert repository.get(device_id) is None
    assert repository.count() == 0

    print("test_device_delete: OK")


def test_device_type_soil_moisture() -> None:
    db = create_test_database()
    repository = DeviceRepository(db)

    device_id = create_device(
        repository,
        name="soil_device",
        device_type=DeviceType.SOIL_MOISTURE,
    )

    db.commit()

    device = repository.get(device_id)

    assert device is not None
    assert device.device_type == DeviceType.SOIL_MOISTURE

    print("test_device_type_soil_moisture: OK")


# ======================================================================
# EventRepository
# ======================================================================


def test_event_create() -> None:
    db = create_test_database()

    device_repository = DeviceRepository(db)
    event_repository = EventRepository(db)

    device_id = create_device(
        device_repository,
        name="event_device",
    )

    timestamp = datetime.now(UTC)

    event_id = event_repository.create(
        Event(
            device_id=device_id,
            timestamp=timestamp,
            level=EventLevel.WARNING,
            message="Test warning",
        )
    )

    db.commit()

    event = event_repository.get(event_id)

    assert event is not None
    assert event.id == event_id
    assert event.device_id == device_id
    assert event.level == EventLevel.WARNING
    assert event.message == "Test warning"
    assert event.timestamp is not None
    assert event.timestamp.tzinfo == UTC

    print("test_event_create: OK")


def test_event_get_missing() -> None:
    db = create_test_database()
    repository = EventRepository(db)

    assert repository.get(999999) is None

    print("test_event_get_missing: OK")


def test_event_get_latest() -> None:
    db = create_test_database()

    device_repository = DeviceRepository(db)
    repository = EventRepository(db)

    device_id = create_device(
        device_repository,
        name="latest_event_device",
    )

    now = datetime.now(UTC)

    repository.create(
        Event(
            device_id=device_id,
            timestamp=now - timedelta(minutes=10),
            level=EventLevel.INFO,
            message="old",
        )
    )

    repository.create(
        Event(
            device_id=device_id,
            timestamp=now - timedelta(minutes=5),
            level=EventLevel.WARNING,
            message="middle",
        )
    )

    repository.create(
        Event(
            device_id=device_id,
            timestamp=now,
            level=EventLevel.ERROR,
            message="new",
        )
    )

    db.commit()

    events = repository.get_latest(2)

    assert len(events) == 2
    assert events[0].message == "new"
    assert events[1].message == "middle"

    print("test_event_get_latest: OK")


def test_event_get_for_device() -> None:
    db = create_test_database()

    device_repository = DeviceRepository(db)
    repository = EventRepository(db)

    device_1 = create_device(
        device_repository,
        name="event_device_1",
    )

    device_2 = create_device(
        device_repository,
        name="event_device_2",
    )

    now = datetime.now(UTC)

    repository.create(
        Event(
            device_id=device_1,
            timestamp=now - timedelta(minutes=2),
            level=EventLevel.INFO,
            message="device 1",
        )
    )

    repository.create(
        Event(
            device_id=device_2,
            timestamp=now - timedelta(minutes=1),
            level=EventLevel.ERROR,
            message="device 2",
        )
    )

    db.commit()

    events = repository.get_for_device(device_1)

    assert len(events) == 1
    assert events[0].device_id == device_1
    assert events[0].message == "device 1"

    print("test_event_get_for_device: OK")


def test_event_get_between() -> None:
    db = create_test_database()

    device_repository = DeviceRepository(db)
    repository = EventRepository(db)

    device_id = create_device(
        device_repository,
        name="between_device",
    )

    now = datetime.now(UTC)

    repository.create(
        Event(
            device_id=device_id,
            timestamp=now - timedelta(hours=3),
            level=EventLevel.INFO,
            message="old",
        )
    )

    repository.create(
        Event(
            device_id=device_id,
            timestamp=now - timedelta(hours=1),
            level=EventLevel.WARNING,
            message="inside",
        )
    )

    repository.create(
        Event(
            device_id=device_id,
            timestamp=now + timedelta(hours=1),
            level=EventLevel.ERROR,
            message="future",
        )
    )

    db.commit()

    events = repository.get_between(
        start=now - timedelta(hours=2),
        end=now,
    )

    assert len(events) == 1
    assert events[0].message == "inside"

    print("test_event_get_between: OK")


def test_event_get_between_for_device() -> None:
    db = create_test_database()

    device_repository = DeviceRepository(db)
    repository = EventRepository(db)

    device_1 = create_device(
        device_repository,
        name="between_device_1",
    )

    device_2 = create_device(
        device_repository,
        name="between_device_2",
    )

    now = datetime.now(UTC)

    repository.create(
        Event(
            device_id=device_1,
            timestamp=now - timedelta(hours=1),
            level=EventLevel.WARNING,
            message="device 1",
        )
    )

    repository.create(
        Event(
            device_id=device_2,
            timestamp=now - timedelta(hours=1),
            level=EventLevel.ERROR,
            message="device 2",
        )
    )

    db.commit()

    events = repository.get_between_for_device(
        device_id=device_1,
        start=now - timedelta(hours=2),
        end=now,
    )

    assert len(events) == 1
    assert events[0].device_id == device_1
    assert events[0].message == "device 1"

    print("test_event_get_between_for_device: OK")


def test_event_delete_before() -> None:
    db = create_test_database()

    device_repository = DeviceRepository(db)
    repository = EventRepository(db)

    device_id = create_device(
        device_repository,
        name="delete_events_device",
    )

    now = datetime.now(UTC)

    repository.create(
        Event(
            device_id=device_id,
            timestamp=now - timedelta(days=2),
            level=EventLevel.INFO,
            message="old",
        )
    )

    repository.create(
        Event(
            device_id=device_id,
            timestamp=now - timedelta(hours=1),
            level=EventLevel.INFO,
            message="new",
        )
    )

    db.commit()

    assert repository.count() == 2

    repository.delete_before(
        now - timedelta(days=1)
    )

    db.commit()

    assert repository.count() == 1

    events = repository.get_latest()

    assert len(events) == 1
    assert events[0].message == "new"

    print("test_event_delete_before: OK")


def test_event_count() -> None:
    db = create_test_database()

    device_repository = DeviceRepository(db)
    repository = EventRepository(db)

    device_id = create_device(
        device_repository,
        name="count_events_device",
    )

    now = datetime.now(UTC)

    repository.create(
        Event(
            device_id=device_id,
            timestamp=now,
            level=EventLevel.INFO,
            message="one",
        )
    )

    repository.create(
        Event(
            device_id=device_id,
            timestamp=now + timedelta(seconds=1),
            level=EventLevel.WARNING,
            message="two",
        )
    )

    db.commit()

    assert repository.count() == 2

    print("test_event_count: OK")


def test_event_count_for_device() -> None:
    db = create_test_database()

    device_repository = DeviceRepository(db)
    repository = EventRepository(db)

    device_1 = create_device(
        device_repository,
        name="count_device_1",
    )

    device_2 = create_device(
        device_repository,
        name="count_device_2",
    )

    now = datetime.now(UTC)

    repository.create(
        Event(
            device_id=device_1,
            timestamp=now,
            level=EventLevel.INFO,
            message="one",
        )
    )

    repository.create(
        Event(
            device_id=device_1,
            timestamp=now + timedelta(seconds=1),
            level=EventLevel.WARNING,
            message="two",
        )
    )

    repository.create(
        Event(
            device_id=device_2,
            timestamp=now + timedelta(seconds=2),
            level=EventLevel.ERROR,
            message="three",
        )
    )

    db.commit()

    assert repository.count_for_device(device_1) == 2
    assert repository.count_for_device(device_2) == 1

    print("test_event_count_for_device: OK")


# ======================================================================
# Main
# ======================================================================


def main() -> None:
    """
    Запустить все repository tests.
    """

    # DeviceRepository
    test_device_create()
    test_device_get_missing()
    test_device_get_by_name()
    test_device_get_by_serial()
    test_device_get_all()
    test_device_get_for_apartment()
    test_device_exists()
    test_device_count()
    test_device_update()
    test_device_update_last_seen()
    test_device_delete()
    test_device_type_soil_moisture()

    # EventRepository
    test_event_create()
    test_event_get_missing()
    test_event_get_latest()
    test_event_get_for_device()
    test_event_get_between()
    test_event_get_between_for_device()
    test_event_delete_before()
    test_event_count()
    test_event_count_for_device()

    print("ALL REPOSITORY TESTS: OK")


if __name__ == "__main__":
    main()