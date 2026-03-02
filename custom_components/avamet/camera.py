"""Camera platform for the AVAMET integration."""
from __future__ import annotations

import logging

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AvametDataUpdateCoordinator
from .entity import AvametEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the AVAMET camera platform."""
    coordinator: AvametDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Only create a camera if the initial poll found a camera URL
    if coordinator.data.get("camera_url"):
        async_add_entities([AvametCameraEntity(coordinator, entry)])


class AvametCameraEntity(AvametEntity, Camera):
    """Implementation of an AVAMET camera."""

    _attr_name = "Camera"

    def __init__(self, coordinator: AvametDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the camera entity."""
        AvametEntity.__init__(self, coordinator, entry.data["station_id"])
        Camera.__init__(self)
        
        self._attr_unique_id = f"{self.station_id}_camera"

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return bytes of camera image."""
        url = self.coordinator.data.get("camera_url")
        if not url:
            return None
            
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.read()
        except Exception as err:
            _LOGGER.error("Error fetching camera image for station %s: %s", self.station_id, err)
            return None
