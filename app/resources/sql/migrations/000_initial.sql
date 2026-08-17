PRAGMA foreign_keys = ON;

-- ==========================================================
-- ESP Monitor
-- Migration: 000_initial.sql
--
-- Первоначальная структура базы данных.
--
-- Все временные метки хранятся как Unix Timestamp (UTC).
-- ==========================================================



-- ==========================================================
-- Таблица применённых миграций
-- ==========================================================

CREATE TABLE IF NOT EXISTS migrations
(
    -- Имя файла миграции
    filename TEXT PRIMARY KEY,

    -- SHA-256 контрольная сумма файла
    checksum TEXT NOT NULL,

    -- Время применения миграции
    applied_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);



-- ==========================================================
-- Таблица устройств
-- ==========================================================

CREATE TABLE IF NOT EXISTS devices
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Имя устройства
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,

    -- Серийный номер
    serial TEXT UNIQUE,

    -- Описание
    description TEXT,

    -- Версия прошивки
    firmware TEXT,

    -- Последнее успешное подключение
    last_seen INTEGER,

    -- Дата регистрации
    created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),

    -- Последнее изменение записи
    updated_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);



-- ==========================================================
-- Таблица измерений
-- ==========================================================

CREATE TABLE IF NOT EXISTS readings
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Устройство
    device_id INTEGER NOT NULL,

    -- Время измерения
    timestamp INTEGER NOT NULL,

    -- Температура (°C)
    temperature REAL
        CHECK (
            temperature IS NULL OR
            temperature BETWEEN -80 AND 150
        ),

    -- Влажность (%)
    humidity REAL
        CHECK (
            humidity IS NULL OR
            humidity BETWEEN 0 AND 100
        ),

    -- Напряжение батареи (В)
    battery REAL
        CHECK (
            battery IS NULL OR
            battery BETWEEN 0 AND 6
        ),

    -- Уровень сигнала Wi-Fi (dBm)
    wifi_rssi INTEGER
        CHECK (
            wifi_rssi IS NULL OR
            wifi_rssi BETWEEN -120 AND 0
        ),

    -- Напряжение питания устройства
    supply_voltage REAL
        CHECK (
            supply_voltage IS NULL OR
            supply_voltage BETWEEN 0 AND 24
        ),

    FOREIGN KEY(device_id)
        REFERENCES devices(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    -- Запрещаем дублировать измерение
    UNIQUE(device_id, timestamp)
);



-- ==========================================================
-- Журнал событий
-- ==========================================================

CREATE TABLE IF NOT EXISTS events
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    device_id INTEGER,

    level TEXT NOT NULL
        CHECK (
            level IN (
                'DEBUG',
                'INFO',
                'WARNING',
                'ERROR',
                'CRITICAL'
            )
        ),

    message TEXT NOT NULL,

    created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),

    FOREIGN KEY(device_id)
        REFERENCES devices(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);



-- ==========================================================
-- Индексы
-- ==========================================================

-- Поиск устройства по имени
CREATE INDEX IF NOT EXISTS idx_devices_name
    ON devices(name);

-- Поиск устройства по серийному номеру
CREATE INDEX IF NOT EXISTS idx_devices_serial
    ON devices(serial);

-- История измерений устройства
CREATE INDEX IF NOT EXISTS idx_readings_device_timestamp
    ON readings(device_id, timestamp);

-- Журнал событий устройства
CREATE INDEX IF NOT EXISTS idx_events_device
    ON events(device_id);

-- Поиск событий по времени
CREATE INDEX IF NOT EXISTS idx_events_created
    ON events(created_at);



-- ==========================================================
-- Триггер автоматического обновления updated_at
-- ==========================================================

CREATE TRIGGER IF NOT EXISTS trg_devices_updated_at
AFTER UPDATE
ON devices
FOR EACH ROW
BEGIN
    UPDATE devices
       SET updated_at = strftime('%s', 'now')
     WHERE id = NEW.id;
END;