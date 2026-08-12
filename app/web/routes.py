"""
HTTP-маршруты ESP Monitor.
"""

from __future__ import annotations

from http import HTTPStatus

from flask import (
    Blueprint,
    Flask,
    current_app,
    jsonify,
    render_template,
    request,
)

from app.services.reading_service import ReadingService


# ======================================================================
# Blueprint
# ======================================================================

api = Blueprint(
    "api",
    __name__,
)


# ======================================================================
# Helpers
# ======================================================================

def reading_service() -> ReadingService:
    """
    Вернуть ReadingService.
    """

    return current_app.extensions["services"]["reading"]


def device_repository():
    """
    Вернуть DeviceRepository.
    """

    return current_app.extensions["repositories"]["device"]


def reading_repository():
    """
    Вернуть ReadingRepository.
    """

    return current_app.extensions["repositories"]["reading"]


def reading_to_dict(reading) -> dict:
    """
    Преобразовать Reading в JSON-совместимый словарь.
    """

    timestamp = None

    if reading.timestamp is not None:
        timestamp = reading.timestamp.isoformat()

    return {
        "id": reading.id,
        "device_id": reading.device_id,
        "timestamp": timestamp,
        "temperature": reading.temperature,
        "humidity": reading.humidity,
        "soil_moisture": reading.soil_moisture,
        "battery": reading.battery,
    }


# ======================================================================
# Registration
# ======================================================================

def register_routes(app: Flask) -> None:
    """
    Зарегистрировать все маршруты приложения.
    """

    app.register_blueprint(api)


# ======================================================================
# Root
# ======================================================================

@api.get("/")
def index():
    """
    Главная страница ESP Monitor.
    """

    return render_template(
        "index.html"
    )


# ======================================================================
# Health
# ======================================================================

@api.get("/health")
def health():
    """
    Проверка работоспособности сервера.
    """

    database = current_app.extensions["database"]

    try:
        database.connect()

        database.execute("SELECT 1")

        database_ok = True

    except Exception:
        database_ok = False

    status = (
        HTTPStatus.OK
        if database_ok
        else HTTPStatus.SERVICE_UNAVAILABLE
    )

    return (
        jsonify(
            {
                "status": (
                    "ok"
                    if database_ok
                    else "error"
                ),
                "database": database_ok,
            }
        ),
        status,
    )


# ======================================================================
# Version
# ======================================================================

@api.get("/api/version")
def version():
    """
    Версия приложения.
    """

    return jsonify(
        {
            "name": "ESP Monitor",
            "version": "1.0.0",
        }
    )


# ======================================================================
# Devices
# ======================================================================

@api.get("/api/devices")
def get_devices():
    """
    Получить список всех зарегистрированных устройств.

    Для каждого устройства возвращается:
        - id
        - name
        - serial
        - description
        - firmware
        - last_seen
        - последнее измерение
    """

    devices = device_repository().get_all()

    result = []

    for device in devices:

        latest = reading_repository().get_latest(
            device.id
        )

        last_seen = None

        if device.last_seen is not None:
            last_seen = device.last_seen.isoformat()

        result.append(
            {
                "id": device.id,
                "name": device.name,
                "type": device.device_type.value,
                "serial": device.serial,
                "description": device.description,
                "firmware": device.firmware,
                "last_seen": last_seen,
                "latest": (
                    reading_to_dict(latest)
                    if latest is not None
                    else None
                ),
            }
        )

    return jsonify(
        {
            "count": len(result),
            "devices": result,
        }
    )


# ======================================================================
# Single device
# ======================================================================

@api.get("/api/devices/<int:device_id>")
def get_device(device_id: int):
    """
    Получить информацию об одном устройстве.
    """

    device = device_repository().get(
        device_id
    )

    if device is None:
        return (
            jsonify(
                {
                    "error": "Device not found."
                }
            ),
            HTTPStatus.NOT_FOUND,
        )

    latest = reading_repository().get_latest(
        device.id
    )

    last_seen = None

    if device.last_seen is not None:
        last_seen = device.last_seen.isoformat()

    return jsonify(
        {
            "id": device.id,
            "name": device.name,
            "serial": device.serial,
            "description": device.description,
            "firmware": device.firmware,
            "type": device.device_type.value,
            "last_seen": last_seen,
            "latest": (
                reading_to_dict(latest)
                if latest is not None
                else None
            ),
        }
    )


# ======================================================================
# Reading API
# ======================================================================

@api.post("/api/reading")
def create_reading():
    """
    Получить измерение от ESP.
    """

    payload = request.get_json(
        silent=True
    )

    if payload is None:
        return (
            jsonify(
                {
                    "error": (
                        "Request body must contain JSON."
                    )
                }
            ),
            HTTPStatus.BAD_REQUEST,
        )

    device_name = payload.get(
        "device"
    )

    if not device_name:
        return (
            jsonify(
                {
                    "error": (
                        "Field 'device' is required."
                    )
                }
            ),
            HTTPStatus.BAD_REQUEST,
        )

    try:

        reading = reading_service().receive(
            device_name=device_name,
            temperature=payload.get(
                "temperature"
            ),
            humidity=payload.get(
                "humidity"
            ),
            soil_moisture=payload.get(
              "soil_moisture"
            ),
            battery=payload.get(
                "battery"
            ),
        )

    except ValueError as exc:

        return (
            jsonify(
                {
                    "error": str(exc),
                }
            ),
            HTTPStatus.BAD_REQUEST,
        )

    except Exception:

        current_app.logger.exception(
            "Cannot save reading."
        )

        return (
            jsonify(
                {
                    "error": (
                        "Internal server error."
                    ),
                }
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    return (
        jsonify(
            {
                "status": "ok",
                "reading_id": reading.id,
            }
        ),
        HTTPStatus.CREATED,
    )


# ======================================================================
# Readings history
# ======================================================================

@api.get("/api/readings")
def get_readings():
    """
    Получить историю измерений устройства.

    Пример:

        /api/readings?device=flat_a&limit=100
    """

    device_name = request.args.get(
        "device"
    )

    if not device_name:
        return (
            jsonify(
                {
                    "error": (
                        "Query parameter "
                        "'device' is required."
                    )
                }
            ),
            HTTPStatus.BAD_REQUEST,
        )

    try:
        limit = int(
            request.args.get(
                "limit",
                100,
            )
        )

    except ValueError:

        return (
            jsonify(
                {
                    "error": (
                        "Parameter 'limit' "
                        "must be an integer."
                    )
                }
            ),
            HTTPStatus.BAD_REQUEST,
        )

    limit = max(
        1,
        min(limit, 5000),
    )

    device = device_repository().get_by_name(
        device_name
    )

    if device is None:
        return (
            jsonify(
                {
                    "error": "Device not found.",
                    "device": device_name,
                }
            ),
            HTTPStatus.NOT_FOUND,
        )

    readings = reading_repository().get_for_device(
        device.id,
        limit=limit,
    )

    return jsonify(
        {
            "device": device.name,
            "count": len(readings),
            "readings": [
                reading_to_dict(reading)
                for reading in readings
            ],
        }
    )


# ======================================================================
# Latest reading
# ======================================================================

@api.get("/api/readings/latest")
def get_latest_reading():
    """
    Получить последнее измерение устройства.

    Пример:

        /api/readings/latest?device=flat_a
    """

    device_name = request.args.get(
        "device"
    )

    if not device_name:
        return (
            jsonify(
                {
                    "error": (
                        "Query parameter "
                        "'device' is required."
                    )
                }
            ),
            HTTPStatus.BAD_REQUEST,
        )

    device = device_repository().get_by_name(
        device_name
    )

    if device is None:
        return (
            jsonify(
                {
                    "error": "Device not found.",
                    "device": device_name,
                }
            ),
            HTTPStatus.NOT_FOUND,
        )

    reading = reading_repository().get_latest(
        device.id
    )

    return jsonify(
        {
            "device": device.name,
            "reading": (
                reading_to_dict(reading)
                if reading is not None
                else None
            ),
        }
    )