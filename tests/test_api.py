"""Tests for the AVAMET API client.

Offline tests parse the saved HTML snapshots under research/ and assert exact
values known at capture time.  Live tests (opt-in via ``-m live``) make real
HTTP requests and only check that the response is structurally valid.
"""
import pytest
import aiohttp
from pathlib import Path

from api import AvametApiClient  # resolved via conftest sys.path

RESEARCH = Path(__file__).parent.parent / "research"
LIVE_STATION = "c27m009e03"


def _client() -> AvametApiClient:
    """Return a bare AvametApiClient instance suitable for calling pure parsing methods."""
    return AvametApiClient.__new__(AvametApiClient)


# ── Offline parsing: mxo_i.html ───────────────────────────────────────────


class TestParseHtml:
    @pytest.fixture(scope="class")
    def data(self):
        return _client()._parse_html(
            (RESEARCH / "mxo_i.html").read_text(encoding="utf-8")
        )

    def test_name(self, data):
        assert data["name"] == "Bocairent - Càmping Mariola"

    def test_temperature(self, data):
        assert data["temperature"] == pytest.approx(14.8)

    def test_humidity(self, data):
        assert data["humidity"] == pytest.approx(81.0)

    def test_pressure(self, data):
        assert data["pressure"] == pytest.approx(1015.0)

    def test_wind_speed(self, data):
        assert data["wind_speed"] == pytest.approx(0.0)

    def test_rain_today(self, data):
        assert data["rain_today"] == pytest.approx(0.0)

    def test_latitude(self, data):
        assert data["latitude"] == pytest.approx(38.7529, abs=1e-3)

    def test_longitude(self, data):
        assert data["longitude"] == pytest.approx(-0.5507, abs=1e-3)

    def test_camera_url(self, data):
        assert data["camera_url"] is not None
        assert data["camera_url"].startswith("https://")

    def test_condition(self, data):
        # Value depends on current time-of-day at test runtime; just validate the domain.
        assert data["condition"] in {"sunny", "clear-night", "rainy", None}


# ── Offline parsing: mx-fitxa.html ────────────────────────────────────────


class TestParseMetadataHtml:
    @pytest.fixture(scope="class")
    def data(self):
        return _client()._parse_metadata_html(
            (RESEARCH / "mx-fitxa.html").read_text(encoding="utf-8")
        )

    def test_model(self, data):
        assert data["model"] == "Davis Vantage Pro2"

    def test_audit_date(self, data):
        assert data["audit_date"] == "31-10-2017"

    def test_check_temp_hum(self, data):
        assert data["check_temp_hum"] is True

    def test_check_rain(self, data):
        assert data["check_rain"] is True

    def test_check_wind(self, data):
        assert data["check_wind"] is False


# ── Live network tests (opt-in: pytest -m live) ───────────────────────────


@pytest.mark.live
async def test_live_fetch_data():
    async with aiohttp.ClientSession() as session:
        client = AvametApiClient(LIVE_STATION, session)
        data = await client.async_get_data()

    assert isinstance(data, dict)
    assert isinstance(data.get("name"), str) and data["name"], "name must be a non-empty string"
    for field in ("temperature", "humidity", "pressure", "wind_speed", "rain_today"):
        val = data.get(field)
        assert val is None or isinstance(val, float), (
            f"{field!r} expected float or None, got {val!r}"
        )
    camera = data.get("camera_url")
    assert camera is None or camera.startswith("https://"), (
        f"camera_url expected https:// URL or None, got {camera!r}"
    )


@pytest.mark.live
async def test_live_fetch_metadata():
    async with aiohttp.ClientSession() as session:
        client = AvametApiClient(LIVE_STATION, session)
        meta = await client.async_get_metadata()

    assert isinstance(meta, dict)
    assert {"model", "audit_date", "check_temp_hum", "check_rain", "check_wind"} <= meta.keys()
