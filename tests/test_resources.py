from app.core.resources import ResourceManager


migration_files = ResourceManager.migration_files()

assert len(migration_files) == 2, (
    f"Expected 2 migration files, got {len(migration_files)}"
)

filenames = [filename for filename, _ in migration_files]

assert filenames == [
    "000_initial.sql",
    "001_sensor_model.sql",
]

print("test_migration_files: OK")


for filename, path in migration_files:
    assert path.exists(), (
        f"Migration file does not exist: {path}"
    )

    sql = ResourceManager.read_text(path)

    assert sql.strip(), (
        f"Migration '{filename}' is empty."
    )

    checksum = ResourceManager.sha256(path)

    assert len(checksum) == 64, (
        f"Invalid SHA-256 checksum for '{filename}'."
    )

    print(f"test_resource_{filename}: OK")


for filename in filenames:
    path = ResourceManager.migration_path(filename)

    assert path.exists(), (
        f"ResourceManager.migration_path() failed for '{filename}'."
    )

print("test_migration_path: OK")
print("ALL RESOURCE TESTS: OK")
