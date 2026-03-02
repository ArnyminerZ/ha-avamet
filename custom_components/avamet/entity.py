"""Base entity for the AVAMET integration."""
from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AvametDataUpdateCoordinator


class AvametEntity(CoordinatorEntity[AvametDataUpdateCoordinator]):
    """Base class for AVAMET entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AvametDataUpdateCoordinator, station_id: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.station_id = station_id
        
        station_name = self.coordinator.data.get("name")
        display_name = station_name if station_name else f"AVAMET Station {self.station_id}"
        model = getattr(self.coordinator, "metadata", {}).get("model") or "Station"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.station_id)},
            "name": display_name,
            "manufacturer": "AVAMET",
            "model": model,
        }
