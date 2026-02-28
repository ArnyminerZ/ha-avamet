"""Weather platform for the AVAMET integration."""
from __future__ import annotations

import logging

from homeassistant.components.weather import (
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfPressure, UnitOfSpeed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AvametDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the AVAMET weather platform."""
    coordinator: AvametDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([AvametWeatherEntity(coordinator, entry)])


class AvametWeatherEntity(CoordinatorEntity[AvametDataUpdateCoordinator], WeatherEntity):
    """Implementation of an AVAMET weather entity."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: AvametDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the weather entity."""
        super().__init__(coordinator)
        self.station_id = entry.data["station_id"]
        
        # Determine the unit configurations based on the website
        self._attr_native_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_native_pressure_unit = UnitOfPressure.HPA
        self._attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
        
        self._attr_unique_id = f"{self.station_id}_weather"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.station_id)},
            "name": f"AVAMET Station {self.station_id}",
            "manufacturer": "AVAMET",
            "model": "Station",
        }

    @property
    def condition(self) -> str | None:
        """Return the current condition."""
        # AVAMET MXO current status pages don't provide a direct string condition,
        # but we could guess sunny or cloudy. For now, since it wasn't requested,
        # we can just return None.
        return None

    @property
    def native_temperature(self) -> float | None:
        """Return the temperature."""
        return self.coordinator.data.get("temperature")

    @property
    def native_pressure(self) -> float | None:
        """Return the pressure."""
        return self.coordinator.data.get("pressure")

    @property
    def humidity(self) -> float | None:
        """Return the humidity."""
        return self.coordinator.data.get("humidity")

    @property
    def native_wind_speed(self) -> float | None:
        """Return the wind speed."""
        return self.coordinator.data.get("wind_speed")
