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

from .const import DOMAIN
from .coordinator import AvametDataUpdateCoordinator
from .entity import AvametEntity

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


class AvametAuditCheckBinarySensor(AvametEntity, BinarySensorEntity):
    """AVAMET Audit Check Binary Sensor."""
    
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, coordinator: AvametDataUpdateCoordinator, entry: ConfigEntry, metadata_key: str, icon: str, translation_key: str) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry.data["station_id"])
        self.metadata_key = metadata_key
        
        self._attr_translation_key = translation_key
        self._attr_icon = icon
        self._attr_unique_id = f"{self.station_id}_{metadata_key}"

    @property
    def is_on(self) -> bool:
        """Return true if the sensor is on."""
        # Metadata parsing is only done on load and stays in coordinator.metadata
        return getattr(self.coordinator, "metadata", {}).get(self.metadata_key, False)
