from pathlib import Path
from tempfile import TemporaryDirectory

from app.core.database import Database


class TestDatabase:
    """
    Временная SQLite-база для тестов.

    После завершения контекстного менеджера
    файл базы и временный каталог удаляются.
    """

    def __init__(self):
        self._temporary_directory = TemporaryDirectory()
        self.path = Path(self._temporary_directory.name) / "test.db"
        self.db = Database(self.path)

    def __enter__(self) -> Database:
        self.db.initialize()
        return self.db

    def __exit__(self, exc_type, exc_value, traceback):
        self.db.close()
        self._temporary_directory.cleanup()
