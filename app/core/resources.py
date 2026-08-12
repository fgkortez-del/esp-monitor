"""
Работа с ресурсами проекта.

ResourceManager отвечает за:

- поиск ресурсов проекта;
- чтение текстовых и бинарных файлов;
- вычисление контрольных сумм;
- поиск SQL-миграций.

Никакой логики работы с базой данных здесь нет.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.exceptions import ResourceNotFound


class ResourceManager:
    """
    Менеджер ресурсов проекта.
    """

    # ------------------------------------------------------------------
    # Корневые каталоги проекта
    # ------------------------------------------------------------------

    PROJECT_ROOT = Path(__file__).resolve().parents[2]

    RESOURCE_ROOT = PROJECT_ROOT / "app" / "resources"

    SQL_ROOT = RESOURCE_ROOT / "sql"

    MIGRATIONS_ROOT = SQL_ROOT / "migrations"

    # ------------------------------------------------------------------
    # Пути
    # ------------------------------------------------------------------

    @classmethod
    def project_root(cls) -> Path:
        """
        Корень проекта.
        """

        return cls.PROJECT_ROOT

    @classmethod
    def resource_path(cls, *parts: str) -> Path:
        """
        Полный путь внутри app/resources.
        """

        return cls.RESOURCE_ROOT.joinpath(*parts)

    @classmethod
    def sql_path(cls, filename: str) -> Path:
        """
        Полный путь к SQL-файлу.
        """

        return cls.SQL_ROOT / filename

    @classmethod
    def migration_path(cls, filename: str) -> Path:
        """
        Полный путь к SQL-миграции.
        """

        return cls.MIGRATIONS_ROOT / filename

    # ------------------------------------------------------------------
    # Проверка существования
    # ------------------------------------------------------------------

    @staticmethod
    def exists(path: Path) -> bool:
        """
        Проверка существования файла.
        """

        return path.exists()

    # ------------------------------------------------------------------
    # Чтение файлов
    # ------------------------------------------------------------------

    @staticmethod
    def read_text(path: Path) -> str:
        """
        Прочитать текстовый файл.
        """

        if not path.exists():
            raise ResourceNotFound(path)

        return path.read_text(encoding="utf-8")

    @staticmethod
    def read_bytes(path: Path) -> bytes:
        """
        Прочитать бинарный файл.
        """

        if not path.exists():
            raise ResourceNotFound(path)

        return path.read_bytes()

    # ------------------------------------------------------------------
    # SQL
    # ------------------------------------------------------------------

    @classmethod
    def load_sql(cls, filename: str) -> str:
        """
        Загрузить SQL-файл.
        """

        return cls.read_text(cls.sql_path(filename))

    @classmethod
    def load_migration(cls, filename: str) -> str:
        """
        Загрузить SQL-миграцию.
        """

        return cls.read_text(cls.migration_path(filename))

    # ------------------------------------------------------------------
    # Контрольные суммы
    # ------------------------------------------------------------------

    @staticmethod
    def sha256(path: Path) -> str:
        """
        Вычислить SHA-256 файла.
        """

        if not path.exists():
            raise ResourceNotFound(path)

        digest = hashlib.sha256()

        with path.open("rb") as file:

            while chunk := file.read(8192):
                digest.update(chunk)

        return digest.hexdigest()

    @classmethod
    def migration_checksum(cls, filename: str) -> str:
        """
        SHA-256 SQL-миграции.
        """

        return cls.sha256(cls.migration_path(filename))

    # ------------------------------------------------------------------
    # Миграции
    # ------------------------------------------------------------------

    @classmethod
    def migration_files(cls) -> list[tuple[str, Path]]:
        """
        Возвращает список миграций.

        Пример:

        [
            ("000_initial.sql", Path(...)),
            ("001_add_events.sql", Path(...)),
        ]
        """

        if not cls.MIGRATIONS_ROOT.exists():
            return []

        migrations: list[tuple[str, Path]] = []

        for path in sorted(cls.MIGRATIONS_ROOT.glob("*.sql")):
            migrations.append((path.name, path))

        return migrations

    @classmethod
    def list_migrations(cls) -> list[Path]:
        """
        Возвращает только список путей миграций.

        Оставлен для совместимости.
        """

        return [path for _, path in cls.migration_files()]