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
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AvametDataUpdateCoordinator

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


class AvametSensor(CoordinatorEntity[AvametDataUpdateCoordinator], SensorEntity):
    """Implementation of an AVAMET sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AvametDataUpdateCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self.station_id = entry.data["station_id"]
        
        self._attr_unique_id = f"{self.station_id}_{description.key}"
        
        station_name = self.coordinator.data.get("name")
        display_name = station_name if station_name else f"AVAMET Station {self.station_id}"
        model = getattr(self.coordinator, "metadata", {}).get("model") or "Station"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.station_id)},
            "name": display_name,
            "manufacturer": "AVAMET",
            "model": model,
        }

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self.coordinator.data.get(self.entity_description.key)


class AvametMetadataSensor(CoordinatorEntity[AvametDataUpdateCoordinator], SensorEntity):
    """Base class for AVAMET metadata sensors."""
    
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, coordinator: AvametDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.station_id = entry.data["station_id"]
        
        station_name = self.coordinator.data.get("name")
        display_name = station_name if station_name else f"AVAMET Station {self.station_id}"
        model = getattr(self.coordinator, "metadata", {}).get("model") or "Station"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.station_id)},
            "name": display_name,
            "manufacturer": "AVAMET",
            "model": model,
        }

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

