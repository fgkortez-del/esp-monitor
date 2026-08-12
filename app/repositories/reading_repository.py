"""
Репозиторий измерений.

Отвечает исключительно за работу с таблицей readings.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.models import Reading
from app.repositories.base_repository import BaseRepository


class ReadingRepository(BaseRepository):
    """
    Репозиторий измерений.
    """

    # ==================================================================
    # Model conversion
    # ==================================================================

    @classmethod
    def _to_model(
        cls,
        row,
    ) -> Reading | None:
        """
        Преобразовать sqlite3.Row в Reading.
        """

        if row is None:
            return None

        return Reading(
            id=row["id"],
            device_id=row["device_id"],
            timestamp=cls.to_datetime(row["timestamp"]),
            temperature=row["temperature"],
            humidity=row["humidity"],
            soil_moisture=row["soil_moisture"],
            battery=row["battery"],
        )

    # ==================================================================
    # Create
    # ==================================================================

    def create(
        self,
        reading: Reading,
    ) -> int:
        """
        Сохранить одно измерение.

        Возвращает ID созданной записи.
        """

        cursor = self.database.execute(
            """
            INSERT INTO readings
            (
                device_id,
                timestamp,
                temperature,
                humidity,
                soil_moisture,
                battery
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                reading.device_id,
                self.to_timestamp(reading.timestamp),
                reading.temperature,
                reading.humidity,
                reading.soil_moisture,
                reading.battery,
            ),
        )

        return cursor.lastrowid

    # ==================================================================
    # Create many
    # ==================================================================

    def create_many(
        self,
        readings: list[Reading],
    ) -> None:
        """
        Массовое сохранение измерений.
        """

        self.database.executemany(
            """
            INSERT INTO readings
            (
                device_id,
                timestamp,
                temperature,
                humidity,
                soil_moisture,
                battery
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    reading.device_id,
                    self.to_timestamp(reading.timestamp),
                    reading.temperature,
                    reading.humidity,
                    reading.soil_moisture,
                    reading.battery,
                )
                for reading in readings
            ],
        )

    # ==================================================================
    # Get by ID
    # ==================================================================

    def get(
        self,
        reading_id: int,
    ) -> Reading | None:
        """
        Получить измерение по ID.
        """

        row = self.database.query_one(
            """
            SELECT *
            FROM readings
            WHERE id = ?
            """,
            (reading_id,),
        )

        return self._to_model(row)

    # ==================================================================
    # Latest
    # ==================================================================

    def get_latest(
        self,
        device_id: int,
    ) -> Reading | None:
        """
        Получить последнее измерение устройства.
        """

        row = self.database.query_one(
            """
            SELECT *
            FROM readings
            WHERE device_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (device_id,),
        )

        return self._to_model(row)

    # ==================================================================
    # Device history
    # ==================================================================

    def get_for_device(
        self,
        device_id: int,
        limit: int = 100,
    ) -> list[Reading]:
        """
        Получить последние измерения устройства.
        """

        rows = self.database.query_all(
            """
            SELECT *
            FROM readings
            WHERE device_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (
                device_id,
                limit,
            ),
        )

        return [
            self._to_model(row)
            for row in rows
        ]

    # ==================================================================
    # Period
    # ==================================================================

    def get_between(
        self,
        device_id: int,
        start: datetime,
        end: datetime,
    ) -> list[Reading]:
        """
        Получить измерения устройства за указанный период.
        """

        rows = self.database.query_all(
            """
            SELECT *
            FROM readings
            WHERE device_id = ?
              AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC
            """,
            (
                device_id,
                self.to_timestamp(start),
                self.to_timestamp(end),
            ),
        )

        return [
            self._to_model(row)
            for row in rows
        ]

    # ==================================================================
    # Last N hours
    # ==================================================================

    def get_last_hours(
        self,
        device_id: int,
        hours: int,
    ) -> list[Reading]:
        """
        Получить измерения за последние N часов.
        """

        end = datetime.now(UTC)
        start = end - timedelta(hours=hours)

        return self.get_between(
            device_id=device_id,
            start=start,
            end=end,
        )

    # ==================================================================
    # Last 24 hours
    # ==================================================================

    def get_last_24_hours(
        self,
        device_id: int,
    ) -> list[Reading]:
        """
        Получить измерения за последние 24 часа.
        """

        return self.get_last_hours(
            device_id=device_id,
            hours=24,
        )

    # ==================================================================
    # Last 7 days
    # ==================================================================

    def get_last_7_days(
        self,
        device_id: int,
    ) -> list[Reading]:
        """
        Получить измерения за последние 7 дней.
        """

        end = datetime.now(UTC)
        start = end - timedelta(days=7)

        return self.get_between(
            device_id=device_id,
            start=start,
            end=end,
        )

    # ==================================================================
    # Last 30 days
    # ==================================================================

    def get_last_30_days(
        self,
        device_id: int,
    ) -> list[Reading]:
        """
        Получить измерения за последние 30 дней.

        Особенно актуально для датчиков влажности почвы.
        """

        end = datetime.now(UTC)
        start = end - timedelta(days=30)

        return self.get_between(
            device_id=device_id,
            start=start,
            end=end,
        )

    # ==================================================================
    # Delete old
    # ==================================================================

    def delete_before(
        self,
        timestamp: datetime,
    ) -> None:
        """
        Удалить измерения старше указанной даты.
        """

        self.database.execute(
            """
            DELETE
            FROM readings
            WHERE timestamp < ?
            """,
            (
                self.to_timestamp(timestamp),
            ),
        )

    # ==================================================================
    # Count
    # ==================================================================

    def count(
        self,
    ) -> int:
        """
        Общее количество измерений.
        """

        row = self.database.query_one(
            """
            SELECT COUNT(*) AS count
            FROM readings
            """
        )

        return row["count"]

    # ==================================================================
    # Count for device
    # ==================================================================

    def count_for_device(
        self,
        device_id: int,
    ) -> int:
        """
        Количество измерений устройства.
        """

        row = self.database.query_one(
            """
            SELECT COUNT(*) AS count
            FROM readings
            WHERE device_id = ?
            """,
            (device_id,),
        )

        return row["count"]

    # ==================================================================
    # Count for period
    # ==================================================================

    def count_between(
        self,
        device_id: int,
        start: datetime,
        end: datetime,
    ) -> int:
        """
        Количество измерений устройства за период.
        """

        row = self.database.query_one(
            """
            SELECT COUNT(*) AS count
            FROM readings
            WHERE device_id = ?
              AND timestamp BETWEEN ? AND ?
            """,
            (
                device_id,
                self.to_timestamp(start),
                self.to_timestamp(end),
            ),
        )

        return row["count"]