from tests.test_helpers import DatabaseTestContext


with DatabaseTestContext() as db:
    rows = db.execute(
        """
        SELECT filename, checksum, applied_at
        FROM migrations
        ORDER BY filename
        """
    ).fetchall()

    assert len(rows) == 2, (
        f"Expected 2 migrations, got {len(rows)}"
    )

    assert rows[0]["filename"] == "000_initial.sql"
    assert rows[1]["filename"] == "001_sensor_model.sql"

    assert rows[0]["checksum"]
    assert rows[1]["checksum"]

    assert rows[0]["applied_at"]
    assert rows[1]["applied_at"]

    print("test_migrations_applied: OK")

    # Повторный запуск миграций не должен ничего менять.
    db.initialize()

    rows_after = db.execute(
        """
        SELECT filename, checksum, applied_at
        FROM migrations
        ORDER BY filename
        """
    ).fetchall()

    assert len(rows_after) == 2
    assert rows_after[0]["filename"] == "000_initial.sql"
    assert rows_after[1]["filename"] == "001_sensor_model.sql"

    print("test_migrations_idempotent: OK")

print("ALL MIGRATION TESTS: OK")
