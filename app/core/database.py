"""
Работа с SQLite.

Database отвечает только за:

- открытие соединения;
- выполнение SQL;
- выполнение транзакций;
- запуск MigrationManager.

Никакой бизнес-логики здесь нет.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Iterable
from contextlib import suppress

from app.core.config import config
from app.core.exceptions.database import (
    DatabaseConnectionError,
    DatabaseQueryError,
)
from app.core.migration_manager import MigrationManager

logger = logging.getLogger(__name__)

class DatabaseTransaction:
    """
    Контекстный менеджер транзакции SQLite.
    """

    def __init__(self, database: "Database") -> None:

        self.database = database

    # ------------------------------------------------------------------

    def __enter__(self) -> "Database":

        self.database.begin()

        return self.database

    # ------------------------------------------------------------------

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> bool:

        if exc_type is None:
            self.database.commit()
        else:
            self.database.rollback()

        return False

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

    # ---------------------------------------------------------

    @property
    def connected(self) -> bool:
        """
        Проверить наличие открытого соединения.
        """

        return self.connection is not None

    # ---------------------------------------------------------

    def connect(self) -> None:
        """
        Открыть соединение с SQLite.
        """

        if self.connected:
            return

        logger.info("Opening database: %s", self.database)

        try:

            self.connection = sqlite3.connect(
                self.database,
                detect_types=sqlite3.PARSE_DECLTYPES,
                check_same_thread=False,
            )

        except sqlite3.Error as exc:

            raise DatabaseConnectionError(
                f"Cannot open database '{self.database}'."
            ) from exc

        self.connection.row_factory = sqlite3.Row

        self.connection.execute(
            "PRAGMA foreign_keys = ON"
        )
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA synchronous = NORMAL")

        logger.info("Database connected.")

    # ------------------------------------------------------------------

    def begin(self) -> None:
        """
        Начать транзакцию.
        """

        self.connect()

        self.connection.execute("BEGIN")

    # ------------------------------------------------------------------

    def commit(self) -> None:
        """
        Зафиксировать транзакцию.
        """

        if self.connection is None:
            return

        self.connection.commit()

    # ------------------------------------------------------------------

    def rollback(self) -> None:
        """
        Откатить транзакцию.
        """

        if self.connection is None:
            return

        with suppress(Exception):
            self.connection.rollback()

    # ---------------------------------------------------------

    def initialize(self) -> None:
        """
        Инициализация базы данных.
        """

        self.connect()

        manager = MigrationManager(self.connection)

        manager.migrate()

        logger.info(
            "Database initialized (%d migrations).",
            len(manager),
        )

    # ---------------------------------------------------------

    def close(self) -> None:
        """
        Закрыть соединение с базой данных.
        """

        if not self.connected:
            return

        logger.info("Closing database.")

        with suppress(Exception):
            self.connection.close()

        self.connection = None

    # ---------------------------------------------------------

    def execute(
        self,
        sql: str,
        parameters: Iterable[Any] = (),
    ) -> sqlite3.Cursor:
        """
        Выполнить SQL-запрос.
        """

        cursor = self._execute(
            sql,
            parameters,
        )

        return cursor

    # ---------------------------------------------------------

    def executemany(
        self,
        sql: str,
        parameters: Iterable[Iterable[Any]],
    ) -> sqlite3.Cursor:
        """
        Выполнить массовый SQL-запрос.
        """

        self.connect()

        try:

            cursor = self.connection.executemany(
                sql,
                parameters,
            )

            return cursor

        except sqlite3.Error as exc:

            raise DatabaseQueryError(
                str(exc)
            ) from exc

    # ---------------------------------------------------------

    def execute_script(
        self,
        sql: str,
    ) -> None:
        """
        Выполнить SQL-скрипт.
        """

        self.connect()

        try:
            logger.debug(
                "Executing SQL script."
            )
            self.connection.executescript(sql)

        except sqlite3.Error as exc:

            raise DatabaseQueryError(
                str(exc)
            ) from exc

    # ---------------------------------------------------------

    def _execute(
        self,
        sql: str,
        parameters: Iterable[Any] = (),
    ) -> sqlite3.Cursor:
        """
        Внутреннее выполнение SQL-запроса.
        Все SQL проходят через этот метод.
        """

        self.connect()

        logger.debug(
            "SQL: %s | params=%s",
            sql.strip(),
            tuple(parameters),
        )

        try:

            return self.connection.execute(
                sql,
                tuple(parameters),
            )

        except sqlite3.Error as exc:

            logger.exception(
                "SQL execution failed: %s",
                sql.strip(),
            )

            raise DatabaseQueryError(
                str(exc)
            ) from exc

    # ---------------------------------------------------------

    def query_one(
        self,
        sql: str,
        parameters: Iterable[Any] = (),
    ) -> sqlite3.Row | None:
        """
        Вернуть одну запись.
        """

        cursor = self._execute(
            sql,
            parameters,
        )

        return cursor.fetchone()

    # ---------------------------------------------------------

    def query_all(
        self,
        sql: str,
        parameters: Iterable[Any] = (),
    ) -> list[sqlite3.Row]:
        """
        Вернуть список записей.
        """

        cursor = self._execute(
            sql,
            parameters,
        )

        return cursor.fetchall()

    # ---------------------------------------------------------

    def cursor(self) -> sqlite3.Cursor:
        """
        Получить курсор SQLite.
        """

        self.connect()

        return self.connection.cursor()

    # ------------------------------------------------------------------

    def transaction(self) -> DatabaseTransaction:
        """
        Вернуть контекстный менеджер транзакции.
        """

        return DatabaseTransaction(self)

    # ---------------------------------------------------------

    def __enter__(self) -> "Database":

        self.connect()

        return self

    # ---------------------------------------------------------

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:

        self.close()

    # ---------------------------------------------------------

    def __repr__(self) -> str:

        return (
            f"{self.__class__.__name__}("
            f"database='{self.database}')"
        )