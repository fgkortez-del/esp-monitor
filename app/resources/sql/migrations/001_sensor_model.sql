PRAGMA foreign_keys = OFF;


-- =====================================================================
-- 1. Apartments
-- =====================================================================

CREATE TABLE IF NOT EXISTS apartments
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    name TEXT NOT NULL UNIQUE,

    description TEXT,

    created_at INTEGER NOT NULL,

    updated_at INTEGER NOT NULL
);


-- =====================================================================
-- 2. Квартира по умолчанию
-- =====================================================================

INSERT OR IGNORE INTO apartments
(
    id,
    name,
    description,
    created_at,
    updated_at
)
VALUES
(
    1,
    'Квартира №1',
    'Квартира по умолчанию',
    strftime('%s', 'now'),
    strftime('%s', 'now')
);


-- =====================================================================
-- 3. Новая таблица devices
-- =====================================================================

CREATE TABLE devices_new
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    apartment_id INTEGER NOT NULL,

    name TEXT NOT NULL UNIQUE,

    serial TEXT,

    device_type TEXT NOT NULL DEFAULT 'climate',

    plant_name TEXT,

    description TEXT,

    firmware TEXT,

    created_at INTEGER NOT NULL,

    updated_at INTEGER NOT NULL,

    last_seen INTEGER,

    FOREIGN KEY (apartment_id)
        REFERENCES apartments(id)
        ON DELETE CASCADE,

    CHECK
    (
        device_type IN
        (
            'climate',
            'soil_moisture'
        )
    )
);


-- =====================================================================
-- 4. Перенос существующих устройств
-- =====================================================================

INSERT INTO devices_new
(
    id,
    apartment_id,
    name,
    serial,
    device_type,
    plant_name,
    description,
    firmware,
    created_at,
    updated_at,
    last_seen
)
SELECT
    id,
    1,
    name,
    serial,
    'climate',
    NULL,
    description,
    firmware,
    created_at,
    updated_at,
    last_seen
FROM devices;


-- =====================================================================
-- 5. Замена devices
-- =====================================================================

DROP TABLE devices;

ALTER TABLE devices_new
RENAME TO devices;


-- =====================================================================
-- 6. Новая таблица readings
-- =====================================================================

CREATE TABLE readings_new
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    device_id INTEGER NOT NULL,

    timestamp INTEGER NOT NULL,

    temperature REAL,

    humidity REAL,

    soil_moisture REAL,

    battery REAL,

    FOREIGN KEY (device_id)
        REFERENCES devices(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CHECK
    (
        temperature IS NULL
        OR temperature BETWEEN -80 AND 150
    ),

    CHECK
    (
        humidity IS NULL
        OR humidity BETWEEN 0 AND 100
    ),

    CHECK
    (
        soil_moisture IS NULL
        OR soil_moisture BETWEEN 0 AND 100
    ),

    CHECK
    (
        battery IS NULL
        OR battery BETWEEN 0 AND 6
    ),

    UNIQUE(device_id, timestamp)
);


-- =====================================================================
-- 7. Перенос существующих readings
-- =====================================================================

INSERT INTO readings_new
(
    id,
    device_id,
    timestamp,
    temperature,
    humidity,
    soil_moisture,
    battery
)
SELECT
    id,
    device_id,
    timestamp,
    temperature,
    humidity,
    NULL,
    battery
FROM readings;


-- =====================================================================
-- 8. Замена readings
-- =====================================================================

DROP TABLE readings;

ALTER TABLE readings_new
RENAME TO readings;


-- =====================================================================
-- 9. Новая таблица events
-- =====================================================================

CREATE TABLE events_new
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    device_id INTEGER,

    timestamp INTEGER NOT NULL,

    level TEXT NOT NULL,

    message TEXT NOT NULL,

    FOREIGN KEY (device_id)
        REFERENCES devices(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CHECK
    (
        level IN
        (
            'debug',
            'info',
            'warning',
            'error',
            'critical'
        )
    )
);


-- =====================================================================
-- 10. Перенос существующих событий
-- =====================================================================

INSERT INTO events_new
(
    id,
    device_id,
    timestamp,
    level,
    message
)
SELECT
    id,
    device_id,
    created_at,
    lower(level),
    message
FROM events;


-- =====================================================================
-- 11. Замена events
-- =====================================================================

DROP TABLE events;

ALTER TABLE events_new
RENAME TO events;


-- =====================================================================
-- 12. Schema info
-- =====================================================================

CREATE TABLE IF NOT EXISTS schema_info
(
    version INTEGER PRIMARY KEY,

    applied_at INTEGER NOT NULL
);


INSERT OR REPLACE INTO schema_info
(
    version,
    applied_at
)
VALUES
(
    1,
    strftime('%s', 'now')
);


-- =====================================================================
-- 13. Индексы devices
-- =====================================================================

CREATE INDEX IF NOT EXISTS idx_devices_apartment
ON devices(apartment_id);


CREATE INDEX IF NOT EXISTS idx_devices_type
ON devices(device_type);


CREATE INDEX IF NOT EXISTS idx_devices_name
ON devices(name);


CREATE INDEX IF NOT EXISTS idx_devices_serial
ON devices(serial);


-- =====================================================================
-- 14. Индексы readings
-- =====================================================================

CREATE INDEX IF NOT EXISTS idx_readings_device_timestamp
ON readings(device_id, timestamp);


-- =====================================================================
-- 15. Индексы events
-- =====================================================================

CREATE INDEX IF NOT EXISTS idx_events_device_timestamp
ON events(device_id, timestamp);


-- =====================================================================
-- 16. Trigger updated_at
-- =====================================================================

CREATE TRIGGER IF NOT EXISTS trg_devices_updated_at
AFTER UPDATE
ON devices
FOR EACH ROW
BEGIN

    UPDATE devices
    SET updated_at = strftime('%s', 'now')
    WHERE id = NEW.id;

END;


PRAGMA foreign_keys = ON;