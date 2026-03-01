"""API Client for fetching weather data from AVAMET."""
import logging
import re
from typing import Any, Dict
from datetime import datetime

import aiohttp
from homeassistant.helpers.sun import get_astral_location
from astral import LocationInfo
from astral.sun import sun

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://www.avamet.org"
DATA_URL = f"{BASE_URL}/mxo_i.php?id={{station_id}}"
METADATA_URL = f"{BASE_URL}/mx-fitxa.php?id={{station_id}}"

# Regex patterns for parsing AVAMET HTML
PATTERN_NAME = re.compile(r"<div id=\"estacio\"[^>]*>\s*(.*?)\s*<br><span class=\"subnom\">\s*(.*?)\s*</span>", re.DOTALL)
PATTERN_COORDS = re.compile(r"(\d+)&deg;\s*(\d+)'\s*([\d\.]+)&quot;\s*([NS])\s*,\s*(\d+)&deg;\s*(\d+)'\s*([\d\.]+)&quot;\s*([EW])")
PATTERN_TEMP = re.compile(r"<div id=\"temp_mit\">([\d,-]+)&deg;</div>")
PATTERN_HUMIDITY = re.compile(r"<div id=\"hrel\">.*?<br/>([\d\.]+)<span class='unit'>%</span>", re.DOTALL)
PATTERN_PRESSURE = re.compile(r"<div id=\"pres\">.*?<br/>([\d\.]+)<span class='unit'>hPa</span>", re.DOTALL)
PATTERN_WIND_SPEED = re.compile(r"<div id=\"vent\">.*风.*?<br/>([\d\.]+)<span class='unit'>km/h</span>", re.DOTALL | re.IGNORECASE)
PATTERN_WIND_SPEED_ALT = re.compile(r"<div id=\"vent\">.*?<br/>([\d\.]+)<span class='unit'>km/h</span>", re.DOTALL)
PATTERN_RAIN_HUI = re.compile(r"<div id=\"prec\">[^<]*?hui[^<]*?<br/>([\d,-]+)<span class='unit'>mm</span>", re.DOTALL | re.IGNORECASE)
PATTERN_CAMERA = re.compile(r"<img class=\"webcamD\" src=\"(.*?)\"")

# Metadata extraction patterns
PATTERN_MODEL = re.compile(r"<td class=\"fitxaVar\">Model(?:o?)</td><td class=\"fitxaValN\">(.*?)<img", re.DOTALL | re.IGNORECASE)
PATTERN_AUDIT_DATE = re.compile(r"<td class=\"fitxaVar\">Revisi(?:.*?) de (?:dades|datos)</td><td class=\"fitxaVal\">(.*?)</td>", re.DOTALL | re.IGNORECASE)
PATTERN_SEGELL_TH = re.compile(r"<td class=\"fitxaVar\">(?:Segell|Sello) TERMO HIGROM.*?TRIC(?:O?)</td><td class=\"fitxaVal\"(?:.*?)><img src=\"(.*?)\"", re.DOTALL | re.IGNORECASE)
PATTERN_SEGELL_PL = re.compile(r"<td class=\"fitxaVar\">(?:Segell|Sello) PLUVIOM.*?TRIC(?:O?)</td><td class=\"fitxaVal\"(?:.*?)><img src=\"(.*?)\"", re.DOTALL | re.IGNORECASE)
PATTERN_SEGELL_WIND = re.compile(r"<td class=\"fitxaVar\">(?:Segell|Sello) E.*?LIC(?:O?)</td><td class=\"fitxaVal\"(?:.*?)><img src=\"(.*?)\"", re.DOTALL | re.IGNORECASE)

def dms_to_decimal(degrees: int, minutes: int, seconds: float, direction: str) -> float:
    """Convert DMS to Decimal Degrees format."""
    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if direction in ['S', 'W']:
        decimal *= -1
    return decimal

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
            async with self.session.get(url, cookies={"idioma": "_va"}) as response:
                response.raise_for_status()
                html = await response.text()
                return self._parse_html(html)
        except Exception as err:
            _LOGGER.error("Error fetching data from AVAMET for station %s: %s", self.station_id, err)
            raise

    async def async_get_metadata(self) -> Dict[str, Any]:
        """Fetch and parse device metadata from AVAMET."""
        url = METADATA_URL.format(station_id=self.station_id)
        
        try:
            async with self.session.get(url, cookies={"idioma": "_va"}) as response:
                response.raise_for_status()
                html = await response.text()
                return self._parse_metadata_html(html)
        except Exception as err:
            _LOGGER.error("Error fetching metadata from AVAMET for station %s: %s", self.station_id, err)
            return {"model": None, "audit_date": None, "check_temp_hum": None, "check_rain": None, "check_wind": None}

    def _parse_metadata_html(self, html: str) -> Dict[str, Any]:
        """Parse the HTML content of the mx-fitxa page into a dictionary."""
        data: Dict[str, Any] = {
            "model": None,
            "audit_date": None,
            "check_temp_hum": None,
            "check_rain": None,
            "check_wind": None,
        }

        match_model = PATTERN_MODEL.search(html)
        if match_model:
            data["model"] = match_model.group(1).strip()

        match_audit_date = PATTERN_AUDIT_DATE.search(html)
        if match_audit_date:
            date_str = match_audit_date.group(1).strip()
            if date_str:
                data["audit_date"] = date_str

        # For checks, "check-cercle.png" means audited/passed. "check-no-cercle.png" means not audited.
        def _parse_check(pattern_result):
            if pattern_result:
                src = pattern_result.group(1).strip()
                return "check-cercle.png" in src
            return False

        data["check_temp_hum"] = _parse_check(PATTERN_SEGELL_TH.search(html))
        data["check_rain"] = _parse_check(PATTERN_SEGELL_PL.search(html))
        data["check_wind"] = _parse_check(PATTERN_SEGELL_WIND.search(html))

        return data

    def _parse_html(self, html: str) -> Dict[str, Any]:
        """Parse the HTML content into a dictionary."""
        data: Dict[str, Any] = {
            "name": None,
            "latitude": None,
            "longitude": None,
            "temperature": None,
            "humidity": None,
            "pressure": None,
            "wind_speed": None,
            "rain_today": None,
            "condition": None,
            "camera_url": None,
        }

        # Match name
        match_name = PATTERN_NAME.search(html)
        if match_name:
            # We want to replace HTML escape character &agrave; -> à, etc. if required,
            # but HA might handle this or we can clean it minimally. Right now
            # let's just extract the raw text and replace typical newlines/spaces
            main_name = match_name.group(1).strip()
            sub_name = match_name.group(2).strip()
            data["name"] = f"{main_name} - {sub_name}"

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

        # Match rain today (pluja hui)
        match_rain = PATTERN_RAIN_HUI.search(html)
        if match_rain:
            val = match_rain.group(1).replace(",", ".")
            try:
                data["rain_today"] = float(val)
            except ValueError:
                pass

        # Quick HTML entity unescaping for the name so it looks natural
        if data["name"]:
            import html as html_parser
            data["name"] = html_parser.unescape(data["name"])

        # Determine conditions via Coordinates and Astral
        match_coords = PATTERN_COORDS.search(html)
        if match_coords:
            try:
                lat_d = int(match_coords.group(1))
                lat_m = int(match_coords.group(2))
                lat_s = float(match_coords.group(3))
                lat_dir = match_coords.group(4)
                
                lon_d = int(match_coords.group(5))
                lon_m = int(match_coords.group(6))
                lon_s = float(match_coords.group(7))
                lon_dir = match_coords.group(8)
                
                lat_decimal = dms_to_decimal(lat_d, lat_m, lat_s, lat_dir)
                lon_decimal = dms_to_decimal(lon_d, lon_m, lon_s, lon_dir)
                
                data["latitude"] = lat_decimal
                data["longitude"] = lon_decimal
                
                # Check day/night using Astral
                from astral import LocationInfo
                from astral.sun import sun
                from datetime import datetime, timezone
                import pytz # Standard dependency used by astral if necessary, or simple UTC comparison

                loc = LocationInfo(timezone="UTC", latitude=lat_decimal, longitude=lon_decimal)
                s = sun(loc.observer, date=datetime.now())
                
                now = datetime.now(timezone.utc)
                is_day = s["sunrise"] < now < s["sunset"]

                # Extremely basic heuristical estimation
                rain = data.get("rain_today", 0) or 0
                if rain > 0:
                    data["condition"] = "rainy"
                elif not is_day:
                    data["condition"] = "clear-night"
                else:
                    data["condition"] = "sunny"
            except Exception as e:
                _LOGGER.debug(f"Failed to extrapolate conditions: {e}")

        return data
