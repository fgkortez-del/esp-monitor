"""
Репозиторий устройств.

Отвечает исключительно за работу с таблицей devices.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.enums import DeviceType
from app.core.models import Device
from app.repositories.base_repository import BaseRepository


class DeviceRepository(BaseRepository):
    """
    Репозиторий устройств.
    """

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    @classmethod
    def _to_model(
        cls,
        row,
    ) -> Device | None:
        """
        Преобразовать sqlite3.Row в Device.
        """

        if row is None:
            return None

        return Device(
            id=row["id"],
            apartment_id=row["apartment_id"],
            name=row["name"],
            serial=row["serial"],
            device_type=DeviceType(row["device_type"]),
            plant_name=row["plant_name"],
            description=row["description"],
            firmware=row["firmware"],
            created_at=cls.to_datetime(row["created_at"]),
            updated_at=cls.to_datetime(row["updated_at"]),
            last_seen=cls.to_datetime(row["last_seen"]),
        )

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create(
        self,
        device: Device,
    ) -> int:
        """
        Создать устройство.

        Возвращает ID новой записи.

        Commit здесь специально не выполняется.
        Управление транзакцией находится выше —
        на уровне Service.
        """

        now = self.to_timestamp(
            datetime.now(UTC)
        )

        cursor = self.database.execute(
            """
            INSERT INTO devices
            (
                apartment_id,
                name,
                serial,
                device_type,
                plant_name,
                description,
                firmware,
                created_at,
                updated_at,
                last_seen
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                device.apartment_id,
                device.name,
                device.serial,
                device.device_type.value,
                device.plant_name,
                device.description,
                device.firmware,
                now,
                now,
                self.to_timestamp(device.last_seen),
            ),
        )

        return cursor.lastrowid

    # ------------------------------------------------------------------
    # Get
    # ------------------------------------------------------------------

    def get(
        self,
        device_id: int,
    ) -> Device | None:
        """
        Получить устройство по ID.
        """

        row = self.database.query_one(
            """
            SELECT *
            FROM devices
            WHERE id = ?
            """,
            (device_id,),
        )

        return self._to_model(row)

    # ------------------------------------------------------------------
    # Get by name
    # ------------------------------------------------------------------

    def get_by_name(
        self,
        name: str,
    ) -> Device | None:
        """
        Получить устройство по имени.
        """

        row = self.database.query_one(
            """
            SELECT *
            FROM devices
            WHERE name = ?
            """,
            (name,),
        )

        return self._to_model(row)

    # ------------------------------------------------------------------
    # Get by serial
    # ------------------------------------------------------------------

    def get_by_serial(
        self,
        serial: str,
    ) -> Device | None:
        """
        Получить устройство по серийному номеру.
        """

        row = self.database.query_one(
            """
            SELECT *
            FROM devices
            WHERE serial = ?
            """,
            (serial,),
        )

        return self._to_model(row)

    # ------------------------------------------------------------------
    # Get all
    # ------------------------------------------------------------------

    def get_all(
        self,
    ) -> list[Device]:
        """
        Получить список всех устройств.
        """

        rows = self.database.query_all(
            """
            SELECT *
            FROM devices
            ORDER BY name
            """
        )

        return [
            self._to_model(row)
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Get by apartment
    # ------------------------------------------------------------------

    def get_for_apartment(
        self,
        apartment_id: int,
    ) -> list[Device]:
        """
        Получить все устройства квартиры.
        """

        rows = self.database.query_all(
            """
            SELECT *
            FROM devices
            WHERE apartment_id = ?
            ORDER BY name
            """,
            (apartment_id,),
        )

        return [
            self._to_model(row)
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(
        self,
        device: Device,
    ) -> None:
        """
        Обновить устройство.

        Commit здесь специально не выполняется.
        """

        self.database.execute(
            """
            UPDATE devices
            SET
                apartment_id = ?,
                name = ?,
                serial = ?,
                device_type = ?,
                plant_name = ?,
                description = ?,
                firmware = ?,
                last_seen = ?
            WHERE id = ?
            """,
            (
                device.apartment_id,
                device.name,
                device.serial,
                device.device_type.value,
                device.plant_name,
                device.description,
                device.firmware,
                self.to_timestamp(device.last_seen),
                device.id,
            ),
        )

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete(
        self,
        device_id: int,
    ) -> None:
        """
        Удалить устройство.

        Commit здесь специально не выполняется.
        """

        self.database.execute(
            """
            DELETE FROM devices
            WHERE id = ?
            """,
            (device_id,),
        )

    # ------------------------------------------------------------------
    # Exists
    # ------------------------------------------------------------------

    def exists(
        self,
        name: str,
    ) -> bool:
        """
        Проверить существование устройства.
        """

        return self.get_by_name(name) is not None

    # ------------------------------------------------------------------
    # Count
    # ------------------------------------------------------------------

    def count(self) -> int:
        """
        Количество устройств.
        """

        row = self.database.query_one(
            """
            SELECT COUNT(*) AS count
            FROM devices
            """
        )

        return row["count"]

    # ------------------------------------------------------------------
    # Last seen
    # ------------------------------------------------------------------

    def update_last_seen(
        self,
        device_id: int,
    ) -> None:
        """
        Обновить время последнего подключения.

        Commit здесь специально не выполняется.
        """

        self.database.execute(
            """
            UPDATE devices
            SET last_seen = strftime('%s', 'now')
            WHERE id = ?
            """,
            (device_id,),
        )