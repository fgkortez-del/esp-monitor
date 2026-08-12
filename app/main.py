"""
Точка входа приложения.

Здесь создаётся Flask-приложение,
инициализируются база данных,
репозитории,
сервисы
и HTTP-маршруты.
"""

from __future__ import annotations

from flask import Flask

from app.core.database import Database

from app.repositories.device_repository import DeviceRepository
from app.repositories.reading_repository import ReadingRepository
from app.repositories.event_repository import EventRepository

from app.services.reading_service import ReadingService

from app.web.routes import register_routes


# ======================================================================
# Application Factory
# ======================================================================

def create_app(
    database: Database | None = None,
) -> Flask:
    """
    Создать Flask-приложение.
    """

    app = Flask(
        __name__,
        template_folder="web/templates",
        static_folder="web/static",
    )

    # -------------------------------------------------------------
    # Database
    # -------------------------------------------------------------

    database = database or Database()

    database.initialize()

    # -------------------------------------------------------------
    # Repositories
    # -------------------------------------------------------------

    device_repository = DeviceRepository(
        database,
    )

    reading_repository = ReadingRepository(
        database,
    )

    event_repository = EventRepository(
        database,
    )

    # -------------------------------------------------------------
    # Services
    # -------------------------------------------------------------

    reading_service = ReadingService(
        database=database,
        device_repository=device_repository,
        reading_repository=reading_repository,
        event_repository=event_repository,
    )

    # -------------------------------------------------------------
    # Dependency container
    # -------------------------------------------------------------

    app.extensions["database"] = database

    app.extensions["repositories"] = {
        "device": device_repository,
        "reading": reading_repository,
        "event": event_repository,
    }

    app.extensions["services"] = {
        "reading": reading_service,
    }

    # -------------------------------------------------------------
    # Routes
    # -------------------------------------------------------------

    register_routes(app)

    return app