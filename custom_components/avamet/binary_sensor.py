"""Binary sensor platform for the AVAMET integration."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
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
    """Set up the AVAMET binary sensor platform."""
    coordinator: AvametDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    # We always will create these binary sensors if metadata dictionary is present
    if hasattr(coordinator, "metadata"):
        entities.append(AvametAuditCheckBinarySensor(coordinator, entry, "check_temp_hum", "mdi:thermometer-check", "audit_temp_hum"))
        entities.append(AvametAuditCheckBinarySensor(coordinator, entry, "check_rain", "mdi:weather-pouring", "audit_rain"))
        entities.append(AvametAuditCheckBinarySensor(coordinator, entry, "check_wind", "mdi:weather-windy", "audit_wind"))

    if entities:
        async_add_entities(entities)


class AvametAuditCheckBinarySensor(CoordinatorEntity[AvametDataUpdateCoordinator], BinarySensorEntity):
    """AVAMET Audit Check Binary Sensor."""
    
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, coordinator: AvametDataUpdateCoordinator, entry: ConfigEntry, metadata_key: str, icon: str, translation_key: str) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.station_id = entry.data["station_id"]
        self.metadata_key = metadata_key
        
        self._attr_translation_key = translation_key
        self._attr_icon = icon
        self._attr_unique_id = f"{self.station_id}_{metadata_key}"
        
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
    def is_on(self) -> bool:
        """Return true if the sensor is on."""
        # Metadata parsing is only done on load and stays in coordinator.metadata
        return getattr(self.coordinator, "metadata", {}).get(self.metadata_key, False)
