"""
Репозиторий системных событий.

Отвечает исключительно за работу с таблицей events.
"""

from __future__ import annotations

from datetime import datetime

from app.core.enums import EventLevel
from app.core.models import Event
from app.repositories.base_repository import BaseRepository


class EventRepository(BaseRepository):
    """
    Репозиторий системных событий.
    """

    # ------------------------------------------------------------------

    @classmethod
    def _to_model(
        cls,
        row,
    ) -> Event | None:
        """
        Преобразовать sqlite3.Row в Event.
        """

        if row is None:
            return None

        return Event(
            id=row["id"],
            device_id=row["device_id"],
            timestamp=cls.to_datetime(row["timestamp"]),
            level=EventLevel(row["level"]),
            message=row["message"],
        )

    # ------------------------------------------------------------------

    def create(
        self,
        event: Event,
    ) -> int:
        """
        Добавить событие.

        Возвращает ID новой записи.
        """

        cursor = self.database.execute(
            """
            INSERT INTO events
            (
                device_id,
                timestamp,
                level,
                message
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                event.device_id,
                self.to_timestamp(event.timestamp),
                event.level.value,
                event.message,
            ),
        )

        return cursor.lastrowid

    # ------------------------------------------------------------------

    def get(
        self,
        event_id: int,
    ) -> Event | None:
        """
        Получить событие по ID.
        """

        row = self.database.query_one(
            """
            SELECT *
            FROM events
            WHERE id = ?
            """,
            (event_id,),
        )

        return self._to_model(row)

    # ------------------------------------------------------------------

    def get_latest(
        self,
        limit: int = 100,
    ) -> list[Event]:
        """
        Получить последние события.
        """

        rows = self.database.query_all(
            """
            SELECT *
            FROM events
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )

        return [
            self._to_model(row)
            for row in rows
        ]

    # ------------------------------------------------------------------

    def get_for_device(
        self,
        device_id: int,
        limit: int = 100,
    ) -> list[Event]:
        """
        Получить последние события конкретного устройства.
        """

        rows = self.database.query_all(
            """
            SELECT *
            FROM events
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

    # ------------------------------------------------------------------

    def get_between(
        self,
        start: datetime,
        end: datetime,
    ) -> list[Event]:
        """
        Получить события за указанный период.
        """

        rows = self.database.query_all(
            """
            SELECT *
            FROM events
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp
            """,
            (
                self.to_timestamp(start),
                self.to_timestamp(end),
            ),
        )

        return [
            self._to_model(row)
            for row in rows
        ]

    # ------------------------------------------------------------------

    def get_between_for_device(
        self,
        device_id: int,
        start: datetime,
        end: datetime,
    ) -> list[Event]:
        """
        Получить события конкретного устройства
        за указанный период.
        """

        rows = self.database.query_all(
            """
            SELECT *
            FROM events
            WHERE device_id = ?
              AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp
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

    # ------------------------------------------------------------------

    def delete_before(
        self,
        timestamp: datetime,
    ) -> None:
        """
        Удалить события старше указанной даты.
        """

        self.database.execute(
            """
            DELETE
            FROM events
            WHERE timestamp < ?
            """,
            (
                self.to_timestamp(timestamp),
            ),
        )

    # ------------------------------------------------------------------

    def count(
        self,
    ) -> int:
        """
        Общее количество событий.
        """

        row = self.database.query_one(
            """
            SELECT COUNT(*) AS count
            FROM events
            """
        )

        return row["count"]

    # ------------------------------------------------------------------

    def count_for_device(
        self,
        device_id: int,
    ) -> int:
        """
        Количество событий конкретного устройства.
        """

        row = self.database.query_one(
            """
            SELECT COUNT(*) AS count
            FROM events
            WHERE device_id = ?
            """,
            (device_id,),
        )

        return row["count"]