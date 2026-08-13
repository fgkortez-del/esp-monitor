from tests.test_helpers import DatabaseTestContext


with DatabaseTestContext() as db:
    print("Test database:", db.database)
    print("Connected:", db.connected)

print("Database OK")
