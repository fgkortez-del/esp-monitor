"""
Базовый класс репозиториев.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.database import Database


class BaseRepository:
    """
    Базовый класс всех репозиториев.
    """

    def __init__(
        self,
        database: Database,
    ) -> None:

        self.database = database

    # ------------------------------------------------------------------
    # Timestamp conversion
    # ------------------------------------------------------------------

    @staticmethod
    def to_datetime(
        value: int | None,
    ) -> datetime | None:
        """
        Unix Timestamp -> UTC-aware datetime.
        """

        if value is None:
            return None

        return datetime.fromtimestamp(
            value,
            tz=UTC,
        )

    # ------------------------------------------------------------------

    @staticmethod
    def to_timestamp(
        value: datetime | None,
    ) -> int | None:
        """
        datetime -> Unix Timestamp.

        Требует timezone-aware datetime.
        """

        if value is None:
            return None

        if value.tzinfo is None:

            raise ValueError(
                "Datetime must be timezone-aware."
            )

        return int(value.timestamp())