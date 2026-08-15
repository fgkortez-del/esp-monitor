def test_database_initialization(test_db):
    assert test_db.connected
    assert test_db.database.exists()
