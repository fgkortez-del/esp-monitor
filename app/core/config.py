"""
Конфигурация проекта ESP Monitor.

Все настройки приложения находятся только здесь.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Config:
    """
    Конфигурация приложения.
    """

    # Пути
    base_dir: Path
    app_dir: Path
    data_dir: Path
    logs_dir: Path
    backups_dir: Path

    # База данных
    database_file: Path
    schema_version: int

    # Flask
    host: str
    port: int
    debug: bool

    # История
    retention_hours: int

    # Логирование
    log_file: Path
    log_level: str


# -----------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

config = Config(
    base_dir=BASE_DIR,
    app_dir=BASE_DIR / "app",
    data_dir=BASE_DIR / "data",
    logs_dir=BASE_DIR / "logs",
    backups_dir=BASE_DIR / "backups",

    database_file=BASE_DIR / "data" / "data.db",
    schema_version=1,

    host="0.0.0.0",
    port=8080,
    debug=False,

    retention_hours=72,

    log_file=BASE_DIR / "logs" / "app.log",
    log_level="INFO",
)