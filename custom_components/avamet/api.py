"""API Client for fetching weather data from AVAMET."""
import logging
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone

import aiohttp
from astral import LocationInfo
from astral.sun import sun

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://www.avamet.org"
DATA_URL = f"{BASE_URL}/mxo_i.php?id={{station_id}}"
METADATA_URL = f"{BASE_URL}/mx-fitxa.php?id={{station_id}}"

# Applied only to the already-extracted coordinate string, not the full HTML
PATTERN_COORDS = re.compile(
    r'(\d+)°\s*(\d+)\'\s*([\d.]+)"\s*([NS]),\s*(\d+)°\s*(\d+)\'\s*([\d.]+)"\s*([EW])'
)

# Metadata extraction patterns (applied to the metadata page, not the data page)
PATTERN_MODEL = re.compile(r"<td class=\"fitxaVar\">Model(?:o?)</td><td class=\"fitxaValN\">(.*?)<img", re.DOTALL | re.IGNORECASE)
PATTERN_AUDIT_DATE = re.compile(r"<td class=\"fitxaVar\">Revisi(?:.*?) de (?:dades|datos)</td><td class=\"fitxaVal\">(.*?)</td>", re.DOTALL | re.IGNORECASE)
PATTERN_SEGELL_TH = re.compile(r"<td class=\"fitxaVar\">(?:Segell|Sello) TERMO HIGROM.*?TRIC(?:O?)</td><td class=\"fitxaVal\"(?:.*?)><img src=\"(.*?)\"", re.DOTALL | re.IGNORECASE)
PATTERN_SEGELL_PL = re.compile(r"<td class=\"fitxaVar\">(?:Segell|Sello) PLUVIOM.*?TRIC(?:O?)</td><td class=\"fitxaVal\"(?:.*?)><img src=\"(.*?)\"", re.DOTALL | re.IGNORECASE)
PATTERN_SEGELL_WIND = re.compile(r"<td class=\"fitxaVar\">(?:Segell|Sello) E.*?LIC(?:O?)</td><td class=\"fitxaVal\"(?:.*?)><img src=\"(.*?)\"", re.DOTALL | re.IGNORECASE)


class _ElementParser(HTMLParser):
    """Collect elements by ID from potentially malformed HTML.

    Segments within each element are split on <br> tags, mirroring the site's
    label / value layout (e.g. <span class="dess">Label</span><br/>VALUE<span class="unit">UNIT</span>).
    Elements with the same ID (duplicate IDs) are stored in document order so
    callers can pick the first, second, etc. occurrence.
    """

    _VOID = frozenset(['br', 'hr', 'img', 'input', 'link', 'meta',
                       'area', 'base', 'col', 'embed', 'param', 'source', 'track', 'wbr'])

    def __init__(self, target_ids: List[str]) -> None:
        super().__init__(convert_charrefs=True)
        self._targets = frozenset(target_ids)
        # All collected elements in document order.
        # Each entry: {'id': str, 'segments': [[str, ...], ...], 'images': [{attr: val}]}
        self.elements: List[Dict] = []
        self._current: Optional[Dict] = None
        self._depth: int = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs_dict = dict(attrs)
        if self._current is not None:
            if tag == 'br':
                self._current['segments'].append([])
            if tag == 'img':
                self._current['images'].append(attrs_dict)
            if tag not in self._VOID:
                self._depth += 1
        elif attrs_dict.get('id') in self._targets:
            self._current = {'id': attrs_dict['id'], 'segments': [[]], 'images': []}
            self._depth = 0

    def handle_endtag(self, tag: str) -> None:
        if self._current is None or tag in self._VOID:
            return
        if self._depth == 0:
            self.elements.append(self._current)
            self._current = None
        else:
            self._depth -= 1

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            stripped = data.strip()
            if stripped:
                self._current['segments'][-1].append(stripped)


def _seg(element: Dict, seg: int, idx: int = 0) -> Optional[str]:
    """Return one text item from a parsed element's segment list."""
    try:
        return element['segments'][seg][idx]
    except (IndexError, TypeError):
        return None


def _parse_eur_float(s: Optional[str]) -> Optional[float]:
    """Convert a European-format number string (. thousands, , decimal) to float."""
    if s is None:
        return None
    try:
        return float(s.replace('.', '').replace(',', '.'))
    except ValueError:
        return None

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
                data = self._parse_html(html)
                
                # Fetch forecast if coordinates are available
                if data.get("latitude") is not None and data.get("longitude") is not None:
                    try:
                        forecast_url = f"https://api.meteopt.com/gfs/json?lat={data['latitude']}&lon={data['longitude']}&lang=es"
                        async with self.session.get(forecast_url) as forecast_response:
                            if forecast_response.status == 200:
                                forecast_json = await forecast_response.json(content_type=None)
                                data.update(self._parse_forecast(forecast_json))
                    except Exception as e:
                        _LOGGER.debug(f"Failed to fetch forecast: {e}")

                return data
        except Exception as err:
            _LOGGER.error("Error fetching data from AVAMET for station %s: %s", self.station_id, err)
            raise

    def _parse_forecast(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse forecast JSON data."""
        try:
            run_str = str(json_data.get("run", ""))
            if not run_str:
                return {}
                
            run_date = datetime.strptime(run_str, "%Y%m%d%H").replace(tzinfo=timezone.utc)
            
            steps = json_data.get("steps", {}).get("values", [])
            data_block = json_data.get("data", {})
            
            tmp2m = data_block.get("tmp2m", {}).get("values", [])
            apcp = data_block.get("apcp", {}).get("values", [])
            wind = data_block.get("wind10m", {}).get("values", [])
            wind_dir = data_block.get("wind10mdir", {}).get("values", [])
            tcdc = data_block.get("tcdc", {}).get("values", [])
            
            forecasts = []
            for i, step in enumerate(steps):
                fcst_time = run_date + timedelta(hours=step)
                
                cloud = tcdc[i] if i < len(tcdc) else 0
                rain = apcp[i] if i < len(apcp) else 0
                
                # Basic condition estimation
                condition = "sunny"
                if rain > 0:
                    condition = "rainy"
                elif cloud > 80:
                    condition = "cloudy"
                elif cloud > 30:
                    condition = "partlycloudy"
                    
                forecast = {
                    "datetime": fcst_time.isoformat(),
                    "native_temperature": tmp2m[i] if i < len(tmp2m) else None,
                    "native_precipitation": rain,
                    "native_wind_speed": wind[i] if i < len(wind) else None,
                    "wind_bearing": wind_dir[i] if i < len(wind_dir) else None,
                    "condition": condition,
                    "cloud_coverage": cloud,
                }
                forecasts.append(forecast)
                
            return {
                "forecast": forecasts,
                "forecast_model": json_data.get("model", "Unknown")
            }
        except Exception as e:
            _LOGGER.debug(f"Error parsing forecast data: {e}")
            return {}

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

        parser = _ElementParser(['estacio', 'temp_mit', 'hrel', 'pres', 'vent', 'prec', 'webcam'])
        parser.feed(html)

        def first(eid: str) -> Optional[Dict]:
            return next((el for el in parser.elements if el['id'] == eid), None)

        def all_by_id(eid: str) -> List[Dict]:
            return [el for el in parser.elements if el['id'] == eid]

        # Station name and coordinates
        estacio = first('estacio')
        if estacio:
            main_name = ''.join(estacio['segments'][0]).strip() if estacio['segments'] else ''
            sub_name = ''.join(estacio['segments'][1]).strip() if len(estacio['segments']) > 1 else ''
            data['name'] = f"{main_name} - {sub_name}" if sub_name else main_name

            coord_str = ''.join(estacio['segments'][2]).strip() if len(estacio['segments']) > 2 else ''
            match_coords = PATTERN_COORDS.search(coord_str)
            if match_coords:
                try:
                    lat_decimal = dms_to_decimal(
                        int(match_coords.group(1)), int(match_coords.group(2)),
                        float(match_coords.group(3)), match_coords.group(4),
                    )
                    lon_decimal = dms_to_decimal(
                        int(match_coords.group(5)), int(match_coords.group(6)),
                        float(match_coords.group(7)), match_coords.group(8),
                    )
                    data['latitude'] = lat_decimal
                    data['longitude'] = lon_decimal
                except Exception as e:
                    _LOGGER.debug("Failed to parse coordinates: %s", e)

        # Temperature: <div id="temp_mit">14,8°</div>
        temp_elem = first('temp_mit')
        if temp_elem:
            val = _parse_eur_float((_seg(temp_elem, 0) or '').rstrip('°') or None)
            if val is not None:
                data['temperature'] = val

        # Humidity: label in seg[0], value in seg[1][0]
        hrel_elem = first('hrel')
        if hrel_elem:
            val = _parse_eur_float(_seg(hrel_elem, 1))
            if val is not None:
                data['humidity'] = val

        # Pressure: label in seg[0], value in seg[1][0] (European thousands separator)
        pres_elem = first('pres')
        if pres_elem:
            val = _parse_eur_float(_seg(pres_elem, 1))
            if val is not None:
                data['pressure'] = val

        # Wind speed: first <div id="vent"> is current wind; second is max wind
        vent_elems = all_by_id('vent')
        if vent_elems:
            val = _parse_eur_float(_seg(vent_elems[0], 1))
            if val is not None:
                data['wind_speed'] = val

        # Rain today: first <div id="prec"> is today; second is monthly; third is annual
        prec_elems = all_by_id('prec')
        if prec_elems:
            val = _parse_eur_float(_seg(prec_elems[0], 1))
            if val is not None:
                data['rain_today'] = val

        # Camera URL: first webcamD image inside <div id="webcam">
        webcam_elem = first('webcam')
        if webcam_elem:
            for img in webcam_elem['images']:
                if 'webcamD' in img.get('class', '').split():
                    src = img.get('src', '')
                    if src:
                        data['camera_url'] = src if src.startswith('http') else f"{BASE_URL}/{src}"
                    break

        # Determine day/night condition using Astral
        if data['latitude'] is not None and data['longitude'] is not None:
            try:
                loc = LocationInfo(timezone="UTC", latitude=data['latitude'], longitude=data['longitude'])
                s = sun(loc.observer, date=datetime.now())
                now = datetime.now(timezone.utc)
                is_day = s['sunrise'] < now < s['sunset']
                rain = data.get('rain_today', 0) or 0
                if rain > 0:
                    data['condition'] = 'rainy'
                elif not is_day:
                    data['condition'] = 'clear-night'
                else:
                    data['condition'] = 'sunny'
            except Exception as e:
                _LOGGER.debug("Failed to extrapolate conditions: %s", e)

        return data
