from tests.test_helpers import TestDatabase


with TestDatabase() as db:
    print("Test database:", db.database)
    print("Connected:", db.connected)

print("Database OK")
