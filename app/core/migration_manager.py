"""
Управление SQL-миграциями.

MigrationManager отвечает за:

- создание служебной таблицы migrations;
- поиск SQL-файлов миграций;
- применение новых миграций;
- проверку контрольных сумм;
- регистрацию выполненных миграций.

Менеджер ничего не знает о классе Database.
Ему требуется только открытое sqlite3.Connection.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.constants import MIGRATIONS_TABLE
from app.core.exceptions import (
    MigrationChecksumError,
    MigrationError,
    MigrationFileError,
)
from app.core.resources import ResourceManager

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class AppliedMigration:
    """
    Информация о применённой миграции.
    """

    filename: str
    checksum: str
    applied_at: str


class MigrationManager:
    """
    Менеджер SQL-миграций.
    """

    def __init__(self, connection: sqlite3.Connection):

        self.connection = connection

    # ---------------------------------------------------------

    def migrate(self) -> None:
        """
        Проверить и применить все отсутствующие миграции.
        """

        logger.info("Checking database migrations...")

        self._ensure_table()

        applied = self._load_applied()

        for filename, path in ResourceManager.migration_files():

            checksum = ResourceManager.sha256(path)

            migration = applied.get(filename)

            if migration is not None:

                if migration.checksum != checksum:

                    raise MigrationChecksumError(
                        f"Migration '{filename}' has been modified."
                    )

                continue

            logger.info("Applying migration %s", filename)

            sql = ResourceManager.read_text(path)

            self._apply(
                filename=filename,
                sql=sql,
                checksum=checksum,
            )

        logger.info("Migration check finished.")

    # ---------------------------------------------------------

    def validate(self) -> None:
        """
        Проверить контрольные суммы уже применённых миграций.
        """

        applied = self._load_applied()

        for filename, migration in applied.items():

            path = ResourceManager.migration_path(filename)

            if not path.exists():

                raise MigrationFileError(
                    f"Migration file '{filename}' not found."
                )

            checksum = ResourceManager.sha256(path)

            if checksum != migration.checksum:

                raise MigrationChecksumError(
                    f"Checksum mismatch for '{filename}'."
                )

    # ---------------------------------------------------------

    def _load_applied(self) -> dict[str, AppliedMigration]:
        """
        Загрузить список применённых миграций.
        """

        cursor = self.connection.execute(
            f"""
            SELECT
                filename,
                checksum,
                applied_at
            FROM {MIGRATIONS_TABLE}
            ORDER BY filename
            """
        )

        migrations: dict[str, AppliedMigration] = {}

        for row in cursor.fetchall():

            migrations[row["filename"]] = AppliedMigration(
                filename=row["filename"],
                checksum=row["checksum"],
                applied_at=row["applied_at"],
            )

        return migrations
        # ---------------------------------------------------------

    def _apply(
        self,
        *,
        filename: str,
        sql: str,
        checksum: str,
    ) -> None:
        """
        Применить одну SQL-миграцию.
        """

        timestamp = datetime.now(UTC).isoformat(timespec="seconds")

        try:

            with self.connection:

                self.connection.executescript(sql)

                self._register(
                    filename=filename,
                    checksum=checksum,
                    applied_at=timestamp,
                )



        except sqlite3.Error as exc:


            raise MigrationError(
                f"Unable to apply migration '{filename}'."
            ) from exc

    # ---------------------------------------------------------

    def _register(
        self,
        *,
        filename: str,
        checksum: str,
        applied_at: str,
    ) -> None:
        """
        Зарегистрировать применённую миграцию.
        """

        self.connection.execute(
            f"""
            INSERT INTO {MIGRATIONS_TABLE}
            (
                filename,
                checksum,
                applied_at
            )
            VALUES
            (
                ?,
                ?,
                ?
            )
            """,
            (
                filename,
                checksum,
                applied_at,
            ),
        )

    # ---------------------------------------------------------

    def applied_migrations(self) -> list[AppliedMigration]:
        """
        Вернуть список применённых миграций.
        """

        migrations = self._load_applied()

        return sorted(
            migrations.values(),
            key=lambda migration: migration.filename,
        )

    # ---------------------------------------------------------

    def has_migration(
        self,
        filename: str,
    ) -> bool:
        """
        Проверить, применена ли миграция.
        """

        cursor = self.connection.execute(
            f"""
            SELECT 1
            FROM {MIGRATIONS_TABLE}
            WHERE filename = ?
            """,
            (filename,),
        )

        return cursor.fetchone() is not None

        # ---------------------------------------------------------

    def _ensure_table(self) -> None:
        """
        Создать служебную таблицу миграций.
        """

        self.connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE}
            (
                filename TEXT PRIMARY KEY,
                checksum TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
            """
        )


    # ---------------------------------------------------------

    def current_version(self) -> str | None:
        """
        Вернуть имя последней применённой миграции.
        """

        cursor = self.connection.execute(
            f"""
            SELECT filename
            FROM {MIGRATIONS_TABLE}
            ORDER BY filename DESC
            LIMIT 1
            """
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return row["filename"]

    # ---------------------------------------------------------

    def pending_migrations(self) -> list[str]:
        """
        Вернуть список ещё не применённых миграций.
        """

        applied = self._load_applied()

        pending: list[str] = []

        for filename, _ in ResourceManager.migration_files():

            if filename not in applied:
                pending.append(filename)

        return pending

    # ---------------------------------------------------------

    def migration_count(self) -> int:
        """
        Количество применённых миграций.
        """

        cursor = self.connection.execute(
            f"""
            SELECT COUNT(*)
            FROM {MIGRATIONS_TABLE}
            """
        )

        row = cursor.fetchone()

        return int(row[0])

    # ---------------------------------------------------------

    def is_database_initialized(self) -> bool:
        """
        Проверить, была ли база данных инициализирована.
        """

        return self.migration_count() > 0
        # ---------------------------------------------------------

    def __len__(self) -> int:
        """
        Количество применённых миграций.
        """

        return self.migration_count()

    # ---------------------------------------------------------

    def __contains__(self, filename: str) -> bool:
        """
        Проверка наличия миграции.

        Пример:
            if "001_add_events.sql" in manager:
                ...
        """

        return self.has_migration(filename)

    # ---------------------------------------------------------

    def __repr__(self) -> str:

        return (
            f"{self.__class__.__name__}("
            f"migrations={self.migration_count()})"
        )