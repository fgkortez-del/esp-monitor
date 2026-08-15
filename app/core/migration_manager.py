"""
Управление SQL-миграциями SQLite.

MigrationManager отвечает за:

- создание служебной таблицы migrations;
- поиск файлов миграций;
- проверку checksum уже применённых миграций;
- последовательное применение новых миграций;
- регистрацию успешно применённых миграций.

MigrationManager работает непосредственно с sqlite3.Connection
и ничего не знает о классе Database.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.core.constants import MIGRATIONS_TABLE
from app.core.exceptions import (
    MigrationChecksumError,
    MigrationError,
    MigrationFileError,
)
from app.core.resources import ResourceManager


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AppliedMigration:
    """
    Информация о применённой миграции.
    """

    filename: str
    checksum: str
    applied_at: int


class MigrationManager:
    """
    Управление SQL-миграциями.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    # ==================================================================
    # Public API
    # ==================================================================

    def migrate(self) -> None:
        """
        Проверить и применить все неприменённые миграции.

        Миграции применяются строго в порядке имени файла.

        Если миграция уже применена, её checksum проверяется.

        Если файл миграции был изменён после применения,
        выбрасывается MigrationChecksumError.

        Каждая новая миграция применяется атомарно.
        """

        logger.info("Checking database migrations...")

        self._ensure_table()

        applied = self._load_applied()

        for filename, path in ResourceManager.migration_files():
            checksum = ResourceManager.sha256(path)

            previous = applied.get(filename)

            if previous is not None:
                self._validate_checksum(
                    filename=filename,
                    actual_checksum=checksum,
                    expected_checksum=previous.checksum,
                )

                logger.debug(
                    "Migration already applied: %s",
                    filename,
                )

                continue

            self._apply(
                filename=filename,
                path=path,
                checksum=checksum,
            )

        logger.info("Database migrations are up to date.")

    # ------------------------------------------------------------------

    def validate(self) -> None:
        """
        Проверить все уже применённые миграции.

        Проверяются:

        - существование файла;
        - соответствие checksum.

        Новые миграции здесь НЕ применяются.
        """

        self._ensure_table()

        applied = self._load_applied()

        for filename, migration in applied.items():
            path = ResourceManager.migration_path(filename)

            if not path.exists():
                raise MigrationFileError(
                    f"Migration file '{filename}' not found."
                )

            checksum = ResourceManager.sha256(path)

            self._validate_checksum(
                filename=filename,
                actual_checksum=checksum,
                expected_checksum=migration.checksum,
            )

    # ------------------------------------------------------------------

    def applied_migrations(self) -> list[AppliedMigration]:
        """
        Вернуть список применённых миграций.
        """

        self._ensure_table()

        return list(self._load_applied().values())

    # ==================================================================
    # Migration application
    # ==================================================================

    def _apply(
        self,
        *,
        filename: str,
        path: Path,
        checksum: str,
    ) -> None:
        """
        Применить одну миграцию атомарно.

        SQL миграции и запись в migrations выполняются
        в одной транзакции.
        """

        logger.info("Applying migration: %s", filename)

        try:
            sql = ResourceManager.read_text(path)

        except (OSError, UnicodeError) as exc:
            raise MigrationFileError(
                f"Cannot read migration file '{filename}'."
            ) from exc

        try:
            self.connection.execute("BEGIN")

            self._execute_script(sql)

            self.connection.execute(
                f"""
                INSERT INTO {MIGRATIONS_TABLE}
                (
                    filename,
                    checksum
                )
                VALUES (?, ?)
                """,
                (
                    filename,
                    checksum,
                ),
            )

            self.connection.commit()

        except sqlite3.Error as exc:
            self.connection.rollback()

            logger.exception(
                "Migration failed: %s",
                filename,
            )

            raise MigrationError(
                f"Unable to apply migration '{filename}'."
            ) from exc

        logger.info("Migration applied: %s", filename)

    # ------------------------------------------------------------------

    def _execute_script(self, sql: str) -> None:
        """
        Выполнить SQL-скрипт внутри текущей транзакции.

        В отличие от sqlite3.executescript(), здесь не происходит
        автоматического COMMIT.

        Поддерживается:

        - обычный SQL;
        - комментарии;
        - строки;
        - CREATE TRIGGER ... BEGIN ... END;
        """

        statements = self._split_sql(sql)

        for statement in statements:
            logger.debug(
                "Executing migration SQL: %s",
                statement.strip(),
            )

            self.connection.execute(statement)

    # ==================================================================
    # Migration state
    # ==================================================================

    def _load_applied(self) -> dict[str, AppliedMigration]:
        """
        Загрузить применённые миграции.
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

        return {
            row["filename"]: AppliedMigration(
                filename=row["filename"],
                checksum=row["checksum"],
                applied_at=row["applied_at"],
            )
            for row in cursor.fetchall()
        }

    # ------------------------------------------------------------------

    def _ensure_table(self) -> None:
        """
        Создать служебную таблицу migrations.

        applied_at хранится как Unix Timestamp UTC,
        в соответствии с 000_initial.sql.
        """

        self.connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE}
            (
                filename TEXT PRIMARY KEY,
                checksum TEXT NOT NULL,
                applied_at INTEGER NOT NULL
                    DEFAULT (strftime('%s', 'now'))
            )
            """
        )

        self.connection.commit()

    # ==================================================================
    # Validation
    # ==================================================================

    @staticmethod
    def _validate_checksum(
        *,
        filename: str,
        actual_checksum: str,
        expected_checksum: str,
    ) -> None:
        """
        Проверить checksum миграции.
        """

        if actual_checksum != expected_checksum:
            raise MigrationChecksumError(
                f"Migration '{filename}' has been modified."
            )

    # ==================================================================
    # SQL parser
    # ==================================================================

    @staticmethod
    def _split_sql(sql: str) -> list[str]:
        """
        Разделить SQL-файл на отдельные SQL statements.

        В отличие от простого split(';'), этот парсер понимает:

        - строковые литералы '...';
        - экранированные строки '';
        - двойные кавычки "...";
        - комментарии -- ...;
        - комментарии /* ... */;
        - CREATE TRIGGER ... BEGIN ... END;

        Последнее особенно важно для наших миграций.

        Пример:

            CREATE TRIGGER ...
            BEGIN
                UPDATE devices;
            END;

        воспринимается как ОДИН SQL statement.
        """

        statements: list[str] = []
        current: list[str] = []

        in_single_quote = False
        in_double_quote = False
        in_line_comment = False
        in_block_comment = False

        # Количество вложенных BEGIN внутри trigger.
        #
        # Для наших миграций практически всегда будет:
        #
        # BEGIN
        #     ...
        # END;
        #
        # Но поддержим и вложенные BEGIN ... END.
        begin_depth = 0

        # Находим, является ли текущий statement CREATE TRIGGER.
        current_is_trigger = False

        i = 0

        while i < len(sql):
            char = sql[i]
            next_char = sql[i + 1] if i + 1 < len(sql) else ""

            # ----------------------------------------------------------
            # Line comment
            # ----------------------------------------------------------

            if in_line_comment:
                if char == "\n":
                    in_line_comment = False
                    current.append("\n")

                i += 1
                continue

            # ----------------------------------------------------------
            # Block comment
            # ----------------------------------------------------------

            if in_block_comment:
                if char == "*" and next_char == "/":
                    in_block_comment = False
                    i += 2
                    continue

                i += 1
                continue

            # ----------------------------------------------------------
            # Single quoted string
            # ----------------------------------------------------------

            if in_single_quote:
                current.append(char)

                if char == "'":
                    if next_char == "'":
                        current.append(next_char)
                        i += 2
                        continue

                    in_single_quote = False

                i += 1
                continue

            # ----------------------------------------------------------
            # Double quoted identifier
            # ----------------------------------------------------------

            if in_double_quote:
                current.append(char)

                if char == '"':
                    if next_char == '"':
                        current.append(next_char)
                        i += 2
                        continue

                    in_double_quote = False

                i += 1
                continue

            # ----------------------------------------------------------
            # Start comments
            # ----------------------------------------------------------

            if char == "-" and next_char == "-":
                in_line_comment = True
                i += 2
                continue

            if char == "/" and next_char == "*":
                in_block_comment = True
                i += 2
                continue

            # ----------------------------------------------------------
            # Start quotes
            # ----------------------------------------------------------

            if char == "'":
                in_single_quote = True
                current.append(char)
                i += 1
                continue

            if char == '"':
                in_double_quote = True
                current.append(char)
                i += 1
                continue

            # ----------------------------------------------------------
            # Detect CREATE TRIGGER
            # ----------------------------------------------------------

            if not current_is_trigger:
                partial = "".join(current).upper()

                if (
                    "CREATE TRIGGER" in partial
                    or "CREATE TEMP TRIGGER" in partial
                    or "CREATE TEMPORARY TRIGGER" in partial
                ):
                    current_is_trigger = True

            # ----------------------------------------------------------
            # BEGIN inside trigger
            # ----------------------------------------------------------

            if current_is_trigger:
                upper_remaining = sql[i:].upper()

                if (
                    upper_remaining.startswith("BEGIN")
                    and (
                        i == 0
                        or not sql[i - 1].isalnum()
                    )
                    and (
                        i + 5 >= len(sql)
                        or not sql[i + 5].isalnum()
                    )
                ):
                    begin_depth += 1

                    current.extend(sql[i:i + 5])
                    i += 5
                    continue

            # ----------------------------------------------------------
            # END inside trigger
            # ----------------------------------------------------------

            if current_is_trigger:
                upper_remaining = sql[i:].upper()

                if (
                    upper_remaining.startswith("END")
                    and (
                        i == 0
                        or not sql[i - 1].isalnum()
                    )
                    and (
                        i + 3 >= len(sql)
                        or not sql[i + 3].isalnum()
                    )
                ):
                    if begin_depth > 0:
                        begin_depth -= 1

                    current.extend(sql[i:i + 3])
                    i += 3
                    continue

            # ----------------------------------------------------------
            # Statement separator
            # ----------------------------------------------------------

            if char == ";":
                # Для обычного SQL ';' заканчивает statement.
                #
                # Для trigger:
                #
                # BEGIN
                #     UPDATE ...;
                # END;
                #
                # первый ';' НЕ заканчивает statement.
                if current_is_trigger and begin_depth > 0:
                    current.append(char)
                    i += 1
                    continue

                statement = "".join(current).strip()

                if statement:
                    statements.append(statement)

                current.clear()

                current_is_trigger = False
                begin_depth = 0

                i += 1
                continue

            current.append(char)
            i += 1

        # --------------------------------------------------------------
        # Последний statement
        # --------------------------------------------------------------

        statement = "".join(current).strip()

        if statement:
            statements.append(statement)

        return statements