"""Sensor platform for the AVAMET integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
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
    """Set up the AVAMET sensor platform."""
    coordinator: AvametDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    # Audit Date
    if getattr(coordinator, "metadata", {}).get("audit_date") is not None:
        entities.append(AvametAuditDateSensor(coordinator, entry))

    if entities:
        async_add_entities(entities)


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

