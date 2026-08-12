"""
Сервис измерений ESP Monitor.

ReadingService отвечает за бизнес-правила приёма измерений:

- проверяет существование устройства;
- проверяет соответствие типа устройства данным;
- создаёт объект Reading;
- сохраняет измерение;
- обновляет last_seen устройства;
- поддерживает устройства без батареи;
- поддерживает климатические датчики;
- поддерживает датчики влажности почвы.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.enums import DeviceType
from app.core.models import Reading
from app.repositories.device_repository import DeviceRepository
from app.repositories.event_repository import EventRepository
from app.repositories.reading_repository import ReadingRepository


class ReadingService:
    """
    Бизнес-логика приёма и сохранения измерений.
    """

    def __init__(
        self,
        *,
        database,
        device_repository: DeviceRepository,
        reading_repository: ReadingRepository,
        event_repository: EventRepository,
    ) -> None:

        self.database = database

        self.device_repository = device_repository
        self.reading_repository = reading_repository
        self.event_repository = event_repository

    # ==================================================================
    # Receive
    # ==================================================================

    def receive(
        self,
        *,
        device_name: str,
        temperature: float | None = None,
        humidity: float | None = None,
        soil_moisture: float | None = None,
        battery: float | None = None,
    ) -> Reading:
        """
        Принять и сохранить одно измерение.

        device_name:
            Имя устройства, переданное ESP/ATtiny85.

        temperature:
            Температура в °C.

        humidity:
            Влажность воздуха в %.

        soil_moisture:
            Влажность почвы в %.

        battery:
            Напряжение батареи в В.

        Возвращает сохранённый объект Reading.
        """

        # --------------------------------------------------------------
        # Device
        # --------------------------------------------------------------

        device = self.device_repository.get_by_name(
            device_name
        )

        if device is None:

            raise ValueError(
                f"Device '{device_name}' not found."
            )

        # --------------------------------------------------------------
        # Normalize values
        # --------------------------------------------------------------

        temperature = self._normalize_float(
            temperature,
            "temperature",
        )

        humidity = self._normalize_float(
            humidity,
            "humidity",
        )

        soil_moisture = self._normalize_float(
            soil_moisture,
            "soil_moisture",
        )

        battery = self._normalize_float(
            battery,
            "battery",
        )

        # --------------------------------------------------------------
        # Validate device type
        # --------------------------------------------------------------

        self._validate_device_type(
            device_type=device.device_type,
            temperature=temperature,
            humidity=humidity,
            soil_moisture=soil_moisture,
        )

        # --------------------------------------------------------------
        # Validate values
        # --------------------------------------------------------------

        self._validate_values(
            temperature=temperature,
            humidity=humidity,
            soil_moisture=soil_moisture,
            battery=battery,
        )

        # --------------------------------------------------------------
        # Timestamp
        # --------------------------------------------------------------

        timestamp = datetime.now(UTC)

        # --------------------------------------------------------------
        # Reading
        # --------------------------------------------------------------

        reading = Reading(
            device_id=device.id,
            timestamp=timestamp,
            temperature=temperature,
            humidity=humidity,
            soil_moisture=soil_moisture,
            battery=battery,
        )

        # --------------------------------------------------------------
        # Save
        # --------------------------------------------------------------

        with self.database.transaction():

            reading.id = self.reading_repository.create(
                reading
            )

            self.device_repository.update_last_seen(
                device.id
            )

        return reading

    # ==================================================================
    # Device type validation
    # ==================================================================

    @staticmethod
    def _validate_device_type(
        *,
        device_type: DeviceType,
        temperature: float | None,
        humidity: float | None,
        soil_moisture: float | None,
    ) -> None:
        """
        Проверить соответствие данных типу устройства.
        """

        if device_type == DeviceType.CLIMATE:

            if (
                temperature is None
                and humidity is None
            ):
                raise ValueError(
                    "Climate device must provide "
                    "temperature or humidity."
                )

            if soil_moisture is not None:

                raise ValueError(
                    "Climate device cannot send "
                    "soil_moisture."
                )

            return

        if device_type == DeviceType.SOIL_MOISTURE:

            if soil_moisture is None:

                raise ValueError(
                    "Soil moisture device must provide "
                    "soil_moisture."
                )

            if (
                temperature is not None
                or humidity is not None
            ):

                raise ValueError(
                    "Soil moisture device cannot send "
                    "temperature or humidity."
                )

            return

        raise ValueError(
            f"Unsupported device type: {device_type}"
        )

    # ==================================================================
    # Value validation
    # ==================================================================

    @staticmethod
    def _validate_values(
        *,
        temperature: float | None,
        humidity: float | None,
        soil_moisture: float | None,
        battery: float | None,
    ) -> None:
        """
        Проверить диапазоны измерений.

        Основная защита также существует на уровне SQLite,
        но сервис должен отбрасывать некорректные данные
        до обращения к базе.
        """

        if temperature is not None:

            if not -80 <= temperature <= 150:

                raise ValueError(
                    "Temperature must be between "
                    "-80 and 150 °C."
                )

        if humidity is not None:

            if not 0 <= humidity <= 100:

                raise ValueError(
                    "Humidity must be between "
                    "0 and 100 %."
                )

        if soil_moisture is not None:

            if not 0 <= soil_moisture <= 100:

                raise ValueError(
                    "Soil moisture must be between "
                    "0 and 100 %."
                )

        if battery is not None:

            if not 0 <= battery <= 6:

                raise ValueError(
                    "Battery voltage must be between "
                    "0 and 6 V."
                )

    # ==================================================================
    # Normalization
    # ==================================================================

    @staticmethod
    def _normalize_float(
        value,
        field_name: str,
    ) -> float | None:
        """
        Привести значение к float.

        None остаётся None.

        Строковые значения вроде "3.85"
        также принимаются.

        Некорректные значения отклоняются.
        """

        if value is None:

            return None

        try:

            result = float(value)

        except (TypeError, ValueError) as exc:

            raise ValueError(
                f"Field '{field_name}' must be a number."
            ) from exc

        return result