"""Sensor platform for the AVAMET integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfPrecipitationDepth,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AvametDataUpdateCoordinator
from .entity import AvametEntity

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    SensorEntityDescription(
        key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    SensorEntityDescription(
        key="pressure",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.HPA,
    ),
    SensorEntityDescription(
        key="wind_speed",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
    ),
    SensorEntityDescription(
        key="rain_today",
        translation_key="rain_today",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
    ),
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the AVAMET sensor platform."""
    coordinator: AvametDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    # Audit Date
    if getattr(coordinator, "metadata", {}).get("audit_date") is not None:
        entities.append(AvametAuditDateSensor(coordinator, entry))

    # Weather Parameters Sensors
    for description in SENSOR_TYPES:
        if coordinator.data.get(description.key) is not None:
            entities.append(AvametSensor(coordinator, entry, description))

    if entities:
        async_add_entities(entities)


class AvametSensor(AvametEntity, SensorEntity):
    """Implementation of an AVAMET sensor."""

    def __init__(
        self,
        coordinator: AvametDataUpdateCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry.data["station_id"])
        self.entity_description = description
        
        self._attr_unique_id = f"{self.station_id}_{description.key}"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self.coordinator.data.get(self.entity_description.key)


class AvametMetadataSensor(AvametEntity, SensorEntity):
    """Base class for AVAMET metadata sensors."""
    
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, coordinator: AvametDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry.data["station_id"])

class AvametAuditDateSensor(AvametMetadataSensor):
    """AVAMET Audit Date Sensor."""
    
    _attr_translation_key = "audit_date"
    _attr_icon = "mdi:calendar-check"
    
    def __init__(self, coordinator: AvametDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.station_id}_audit_date"

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        # Metadata parsing is only done on load and stays in coordinator.metadata
        return getattr(self.coordinator, "metadata", {}).get("audit_date")

