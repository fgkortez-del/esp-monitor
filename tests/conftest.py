from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from app.core.database import Database


@pytest.fixture
def test_db():
    """
    Временная SQLite-база для одного теста.

    После завершения теста база и временный каталог удаляются.
    """
    with TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "test.db"

        db = Database(database_path)
        db.initialize()

        try:
            yield db
        finally:
            db.close()
