"""API Client for fetching weather data from AVAMET."""
import logging
import re
from typing import Any, Dict

import aiohttp

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://www.avamet.org"
DATA_URL = f"{BASE_URL}/mxo_i.php?id={{station_id}}"

# Regex patterns for parsing AVAMET HTML
PATTERN_TEMP = re.compile(r"<div id=\"temp_mit\">([\d,-]+)&deg;</div>")
PATTERN_HUMIDITY = re.compile(r"<div id=\"hrel\">.*?<br/>([\d\.]+)<span class='unit'>%</span>", re.DOTALL)
PATTERN_PRESSURE = re.compile(r"<div id=\"pres\">.*?<br/>([\d\.]+)<span class='unit'>hPa</span>", re.DOTALL)
PATTERN_WIND_SPEED = re.compile(r"<div id=\"vent\">.*风.*?<br/>([\d\.]+)<span class='unit'>km/h</span>", re.DOTALL | re.IGNORECASE)
PATTERN_WIND_SPEED_ALT = re.compile(r"<div id=\"vent\">.*?<br/>([\d\.]+)<span class='unit'>km/h</span>", re.DOTALL)
PATTERN_CAMERA = re.compile(r"<img class=\"webcamD\" src=\"(.*?)\"")

class AvametApiClient:
    """API Client to interact with AVAMET real-time pages."""

    def __init__(self, station_id: str, session: aiohttp.ClientSession) -> None:
        """Initialize."""
        self.station_id = station_id
        self.session = session

    async def async_get_data(self) -> Dict[str, Any]:
        """Fetch and parse data from AVAMET."""
        url = DATA_URL.format(station_id=self.station_id)
        
        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                html = await response.text()
                return self._parse_html(html)
        except Exception as err:
            _LOGGER.error("Error fetching data from AVAMET for station %s: %s", self.station_id, err)
            raise

    def _parse_html(self, html: str) -> Dict[str, Any]:
        """Parse the HTML content into a dictionary."""
        data: Dict[str, Any] = {
            "temperature": None,
            "humidity": None,
            "pressure": None,
            "wind_speed": None,
            "camera_url": None,
        }

        # Match temperature
        match_temp = PATTERN_TEMP.search(html)
        if match_temp:
            val = match_temp.group(1).replace(",", ".")
            try:
                data["temperature"] = float(val)
            except ValueError:
                pass

        # Match humidity
        match_hum = PATTERN_HUMIDITY.search(html)
        if match_hum:
            val = match_hum.group(1)
            try:
                data["humidity"] = float(val)
            except ValueError:
                pass

        # Match pressure
        match_pres = PATTERN_PRESSURE.search(html)
        if match_pres:
            # Pressure format might have thousand separators like 1.026
            val = match_pres.group(1).replace(".", "") 
            try:
                data["pressure"] = float(val)
            except ValueError:
                pass

        # Match wind speed
        match_wind = PATTERN_WIND_SPEED_ALT.search(html)
        if match_wind:
            val = match_wind.group(1).replace(",", ".")
            try:
                data["wind_speed"] = float(val)
            except ValueError:
                pass

        # Match camera URL
        match_cam = PATTERN_CAMERA.search(html)
        if match_cam:
            cam_url = match_cam.group(1)
            if cam_url.startswith("http"):
                data["camera_url"] = cam_url
            else:
                data["camera_url"] = f"{BASE_URL}/{cam_url}"

        return data
