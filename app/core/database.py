"""
Работа с SQLite.

Database отвечает только за:

- открытие соединения;
- закрытие соединения;
- выполнение SQL-запросов;
- выполнение массовых SQL-запросов;
- получение одной или нескольких строк;
- запуск MigrationManager.

Бизнес-логики и логики миграций здесь нет.
"""

from __future__ import annotations
from app.core.transaction import Transaction
import logging
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from app.core.config import config
from app.core.exceptions.database import (
    DatabaseConnectionError,
    DatabaseQueryError,
)
from app.core.migration_manager import MigrationManager


logger = logging.getLogger(__name__)


class Database:
    """
    Работа с SQLite.
    """

    def __init__(
        self,
        database: Path | None = None,
    ) -> None:
        self.database = database or config.database_file
        self.connection: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    @property
    def connected(self) -> bool:
        """
        Проверить наличие открытого соединения.
        """
        return self.connection is not None

    # ------------------------------------------------------------------

    def connect(self) -> None:
        """
        Открыть соединение с SQLite.

        Повторный вызов безопасен.
        """
        if self.connected:
            return

        logger.info("Opening database: %s", self.database)

        try:
            self.database.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            connection = sqlite3.connect(
                self.database,
                detect_types=sqlite3.PARSE_DECLTYPES,
                check_same_thread=False,
            )

        except (sqlite3.Error, OSError) as exc:
            raise DatabaseConnectionError(
                f"Cannot open database '{self.database}'."
            ) from exc

        connection.row_factory = sqlite3.Row

        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")

        except sqlite3.Error as exc:
            connection.close()

            raise DatabaseConnectionError(
                f"Cannot configure database '{self.database}'."
            ) from exc

        self.connection = connection

        logger.info("Database connected.")

    # ------------------------------------------------------------------

    def close(self) -> None:
        """
        Закрыть соединение с базой данных.
        """
        if not self.connected:
            return

        logger.info("Closing database.")

        try:
            self.connection.close()

        except sqlite3.Error:
            logger.exception(
                "Error while closing database '%s'.",
                self.database,
            )

        finally:
            self.connection = None

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    def commit(self) -> None:
        """
        Зафиксировать текущую транзакцию.
        """
        self.connect()

        try:
            self.connection.commit()

        except sqlite3.Error as exc:
            raise DatabaseQueryError(
                "Cannot commit database transaction."
            ) from exc

    # ------------------------------------------------------------------

    def rollback(self) -> None:
        """
        Откатить текущую транзакцию.
        """
        self.connect()

        try:
            self.connection.rollback()

        except sqlite3.Error as exc:
            raise DatabaseQueryError(
                "Cannot rollback database transaction."
            ) from exc

    # ------------------------------------------------------------------

    def transaction(self) -> Transaction:
        """
        Получить контекстный менеджер транзакции.
        """
        self.connect()

        return Transaction(self.connection)

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """
        Инициализировать базу данных и применить миграции.
        """
        self.connect()

        manager = MigrationManager(self.connection)
        manager.migrate()

        logger.info(
            "Database initialized (%d migrations).",
            len(manager.applied_migrations()),
        )

    # ------------------------------------------------------------------
    # SQL
    # ------------------------------------------------------------------

    def execute(
        self,
        sql: str,
        parameters: Iterable[Any] = (),
    ) -> sqlite3.Cursor:
        """
        Выполнить SQL-запрос.
        """
        self.connect()

        parameters = tuple(parameters)

        try:
            logger.debug(
                "SQL execute: %s | parameters=%r",
                sql.strip(),
                parameters,
            )

            return self.connection.execute(
                sql,
                parameters,
            )

        except sqlite3.Error as exc:
            raise DatabaseQueryError(
                str(exc)
            ) from exc

    # ------------------------------------------------------------------

    def executemany(
        self,
        sql: str,
        parameters: Iterable[Iterable[Any]],
    ) -> sqlite3.Cursor:
        """
        Выполнить SQL-запрос для нескольких наборов параметров.
        """
        self.connect()

        try:
            logger.debug(
                "SQL executemany: %s",
                sql.strip(),
            )

            return self.connection.executemany(
                sql,
                parameters,
            )

        except sqlite3.Error as exc:
            raise DatabaseQueryError(
                str(exc)
            ) from exc

    # ------------------------------------------------------------------

    def query_one(
        self,
        sql: str,
        parameters: Iterable[Any] = (),
    ) -> sqlite3.Row | None:
        """
        Выполнить SELECT и вернуть одну строку.

        Если строк нет, возвращается None.
        """
        return self.execute(
            sql,
            parameters,
        ).fetchone()

    # ------------------------------------------------------------------

    def query_all(
        self,
        sql: str,
        parameters: Iterable[Any] = (),
    ) -> list[sqlite3.Row]:
        """
        Выполнить SELECT и вернуть все строки.
        """
        return self.execute(
            sql,
            parameters,
        ).fetchall()