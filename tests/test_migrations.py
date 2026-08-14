def test_migrations_applied(test_db):
    rows = test_db.execute(
        """
        SELECT filename, checksum, applied_at
        FROM migrations
        ORDER BY filename
        """
    ).fetchall()

    assert len(rows) == 2

    assert rows[0]["filename"] == "000_initial.sql"
    assert rows[1]["filename"] == "001_sensor_model.sql"

    assert rows[0]["checksum"]
    assert rows[1]["checksum"]

    assert rows[0]["applied_at"]
    assert rows[1]["applied_at"]


def test_migrations_idempotent(test_db):
    before = test_db.execute(
        """
        SELECT filename, checksum, applied_at
        FROM migrations
        ORDER BY filename
        """
    ).fetchall()

    test_db.initialize()

    after = test_db.execute(
        """
        SELECT filename, checksum, applied_at
        FROM migrations
        ORDER BY filename
        """
    ).fetchall()

    assert len(after) == len(before)

    for before_row, after_row in zip(before, after):
        assert before_row["filename"] == after_row["filename"]
        assert before_row["checksum"] == after_row["checksum"]
        assert before_row["applied_at"] == after_row["applied_at"]
