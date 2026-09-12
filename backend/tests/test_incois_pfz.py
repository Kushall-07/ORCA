"""Official INCOIS PFZ reference: WFS fetch, deterministic spatial matching,
and the map-layer data contract. PFZ is a fishing-potential reference only -
see test_pfz_safety_isolation.py for the mandatory isolation checks."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from app.agents.marine_area import lookup as lookup_area
from app.core.config import Settings
from app.gis.pfz_reference import build_pfz_reference, fetch_matched_lines
from app.models.common import Coordinate
from app.models.pfz import PfzAvailability
from app.services import incois_pfz
from app.services.cache import InMemoryCache, JsonCache

MANGALORE = Coordinate(latitude=12.87, longitude=74.84)
KANYAKUMARI = Coordinate(latitude=8.08, longitude=77.55)


def _line(state_name: str, lon: float, lat: float, julian_day: str = "254") -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "MultiLineString", "coordinates": [[[lon, lat], [lon + 0.05, lat + 0.05]]]},
        "properties": {"State_Name": state_name, "Julian_day": julian_day, "Year": 2026},
    }


def _landing(sector: str, lat: float, lon: float, name: str = "Test LC") -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
            "SECTOR_NAM": sector, "LC_NAME": name, "DIST_NAME": "Test District",
            "LATITUDE": lat, "LONGITUDE": lon, "DIRECTION": "NW", "BEARING": 292,
            "DISTANCE_F": 21, "DISTANCE_T": 26, "DEPTH_FROM": 18, "DEPTH_TO": 23,
            "FORECAST_D": "2026-09-11T18:30:00Z", "VALIDITY_D": "2026-09-12T18:30:00Z",
            "UPDATED_DA": "2026-09-11T06:00:00Z",
        },
    }


_LINES_FC = {
    "type": "FeatureCollection",
    "features": [
        _line("KARNATAKA", 74.84, 12.90),
        _line("KARNATAKA", 74.80, 12.70),
        _line("KERALA", 76.20, 9.90),
        _line("GOA", 73.80, 15.30),
    ],
}
_LANDING_FC = {
    "type": "FeatureCollection",
    "features": [
        _landing("KARNATAKA", 12.88, 74.85, "Mangalore LC"),
        _landing("KARNATAKA", 12.60, 74.70, "Far LC"),
        _landing("KERALA", 9.97, 76.24, "Kochi LC"),
    ],
}


# ---- 9. PFZ geometry parsing / spatial matching -----------------------------
def test_match_nearby_lines_prefers_same_sector() -> None:
    area = lookup_area(MANGALORE)
    matched = incois_pfz.match_nearby_lines(
        _LINES_FC, MANGALORE, state_name=area.state_name,
        max_distance_km=250.0, max_features=40,
    )
    assert len(matched) == 2
    assert all(f["properties"]["State_Name"] == "KARNATAKA" for f in matched)


def test_match_nearby_lines_falls_back_to_distance_without_sector_match() -> None:
    matched = incois_pfz.match_nearby_lines(
        _LINES_FC, MANGALORE, state_name=None, max_distance_km=250.0, max_features=40,
    )
    assert matched  # some nearby lines found by distance alone


def test_match_nearby_lines_caps_feature_count() -> None:
    many = {"type": "FeatureCollection", "features": [_line("KARNATAKA", 74.8 + i * 0.01, 12.8) for i in range(50)]}
    matched = incois_pfz.match_nearby_lines(
        many, MANGALORE, state_name="KARNATAKA", max_distance_km=250.0, max_features=10,
    )
    assert len(matched) == 10


# ---- 10. PFZ spatial matching (landing centres) -----------------------------
def test_nearest_landing_centre_prefers_same_sector() -> None:
    match = incois_pfz.nearest_landing_centre(_LANDING_FC, MANGALORE, state_name="KARNATAKA")
    assert match is not None
    feature, distance_km = match
    assert feature["properties"]["LC_NAME"] == "Mangalore LC"
    assert distance_km < 5.0


def test_nearest_landing_centre_none_for_empty_dataset() -> None:
    empty = {"type": "FeatureCollection", "features": []}
    assert incois_pfz.nearest_landing_centre(empty, MANGALORE, state_name="KARNATAKA") is None


# ---- 11. PFZ unavailable -----------------------------------------------------
async def test_build_pfz_reference_unavailable_on_transport_error(monkeypatch) -> None:
    async def _boom(*a, **k):
        raise incois_pfz.IncoisPfzUnavailable("simulated outage")

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _boom)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _boom)
    # The WFS outage now also tries the official Text Data fallback (see
    # module 13 below) - simulate that channel being down too so this stays a
    # true "both official channels unavailable" case.
    monkeypatch.setattr(incois_pfz, "fetch_pfz_textdata", _boom)
    result = await build_pfz_reference(
        MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache())
    )
    assert result.availability is PfzAvailability.UNAVAILABLE
    assert result.zone_count == 0


async def test_build_pfz_reference_no_location_match_for_open_sea(monkeypatch) -> None:
    async def _lines(*a, **k):
        return _LINES_FC

    async def _landing_fc(*a, **k):
        return _LANDING_FC

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing_fc)
    open_sea = Coordinate(latitude=13.0, longitude=72.0)
    result = await build_pfz_reference(
        open_sea, settings=Settings(), cache=JsonCache(InMemoryCache())
    )
    assert result.availability is PfzAvailability.NO_LOCATION_MATCH


async def test_build_pfz_reference_available_with_matched_geometry(monkeypatch) -> None:
    async def _lines(*a, **k):
        return _LINES_FC

    async def _landing_fc(*a, **k):
        return _LANDING_FC

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing_fc)
    result = await build_pfz_reference(
        MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache())
    )
    assert result.availability is PfzAvailability.AVAILABLE
    assert result.zone_count == 2
    assert result.area_matched == "KARNATAKA"
    assert result.nearest_landing_centre is not None
    assert result.nearest_landing_centre.direction == "NW"
    assert result.nearest_landing_centre.depth_from_m == 18.0


# ---- 12. PFZ rendering data contract -----------------------------------------
async def test_fetch_matched_lines_returns_feature_collection_with_provenance(monkeypatch) -> None:
    async def _lines(*a, **k):
        return _LINES_FC

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    fc = await fetch_matched_lines(MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache()))
    assert fc["type"] == "FeatureCollection"
    assert fc["orca_meta"]["authority"] == "INCOIS"
    assert "not a safety zone" in fc["orca_meta"]["disclaimer"]
    assert all(f["properties"]["State_Name"] == "KARNATAKA" for f in fc["features"])


# ---- schema validation for the WFS client -----------------------------------
async def test_fetch_wfs_geojson_rejects_non_feature_collection() -> None:
    class _FakeResponse:
        status_code = 200

        def json(self):
            return {"not": "geojson"}

    class _FakeClient:
        async def get(self, url, timeout):
            return _FakeResponse()

    with pytest.raises(incois_pfz.SchemaValidationError):
        await incois_pfz._fetch_wfs_geojson(
            base_url="https://example.invalid/geoserver",
            type_name="X:y", timeout_s=5.0, client=_FakeClient(),
        )


# ---- 13. official INCOIS PFZ Text Data fallback (WFS 403 -> Text Data) -----
# "Forecast Date" / "Valid upto" appear once on the sector-select landing page
# (TextDataHome), nested inside an outer layout table exactly like the real
# INCOIS page - this is also a regression test for the HTML table parser
# needing to handle tables nested inside another table's cell.
_TEXTDATA_HOME_HTML = """
<html><body>
<table><tr><td>
  <table><tr><td>&nbsp;</td><td>Forecast Date</td><td>Valid upto</td><td>&nbsp;</td></tr>
  <tr><td>&nbsp;</td><td>12 SEP 2026</td><td>13 SEP 2026</td><td>&nbsp;</td></tr></table>
</td></tr></table>
</body></html>
"""

_TEXTDATA_SELECT_HTML = "<html><body>sector selected into session</body></html>"

_TEXTDATA_FORECAST_HTML = """
<table border="1px" class="center">
<tr><th>From the coast of</th><th>Direction</th><th>Bearing (deg)</th>
<th>Distance (nmi)<br>From-To</th><th>Depth (mtr)<br>From-To</th>
<th>Latitude (dd)</th><th>Longitude (dd)</th><th></th></tr>
<tr><td>Mangalore</td><td>SW</td><td>256</td><td>17.82-20.52</td>
<td>56-61</td><td>12.9 N</td><td>74.75 E</td></tr>
</table>
"""


class _FakeTextDataClient:
    """Fakes the 3-request TextDataHome -> TextData?secid=.. ->
    formattedForecast.action flow without any network access."""

    def __init__(self, *, select_status: int = 200, forecast_status: int = 200) -> None:
        self.select_status = select_status
        self.forecast_status = forecast_status
        self.calls: list[str] = []

    async def get(self, url, params=None):
        self.calls.append(url)

        class _Resp:
            def __init__(self, status_code: int, text: str) -> None:
                self.status_code = status_code
                self.text = text

        if "TextDataHome" in url:
            return _Resp(200, _TEXTDATA_HOME_HTML)
        if url.endswith("/TextData"):
            return _Resp(self.select_status, _TEXTDATA_SELECT_HTML)
        if "formattedForecast" in url:
            return _Resp(self.forecast_status, _TEXTDATA_FORECAST_HTML)
        raise AssertionError(f"unexpected URL in fake Text Data client: {url}")


async def test_fetch_pfz_textdata_parses_official_forecast_table() -> None:
    client = _FakeTextDataClient()
    result = await incois_pfz.fetch_pfz_textdata(
        state_name="KARNATAKA", settings=Settings(), client=client
    )
    assert result["forecast_date"] == "12 SEP 2026"
    assert result["valid_until"] == "13 SEP 2026"
    assert len(result["points"]) == 1
    point = result["points"][0]
    assert point["from_coast"] == "Mangalore"
    assert point["direction"] == "SW"
    assert point["bearing_deg"] == 256.0
    assert point["distance_from_nm"] == 17.82
    assert point["distance_to_nm"] == 20.52
    assert point["depth_from_m"] == 56.0
    assert point["depth_to_m"] == 61.0
    assert point["latitude"] == pytest.approx(12.9)
    assert point["longitude"] == pytest.approx(74.75)
    # session established before the sector is selected, sector selected
    # before the formatted forecast is requested (order matters - the site's
    # own session-scoped sector selection depends on it).
    assert "TextDataHome" in client.calls[0]
    assert client.calls[1].endswith("/TextData")
    assert "formattedForecast" in client.calls[2]


async def test_fetch_pfz_textdata_unknown_sector_raises() -> None:
    with pytest.raises(incois_pfz.PfzTextDataUnavailable):
        await incois_pfz.fetch_pfz_textdata(
            state_name="NOT A REAL SECTOR", settings=Settings(), client=_FakeTextDataClient()
        )


async def test_fetch_pfz_textdata_http_failure_raises_unavailable() -> None:
    with pytest.raises(incois_pfz.PfzTextDataUnavailable):
        await incois_pfz.fetch_pfz_textdata(
            state_name="KARNATAKA", settings=Settings(),
            client=_FakeTextDataClient(forecast_status=500),
        )


def test_parse_decimal_degree_handles_hemispheres() -> None:
    assert incois_pfz._parse_decimal_degree("12.9 N") == pytest.approx(12.9)
    assert incois_pfz._parse_decimal_degree("74.75 E") == pytest.approx(74.75)
    assert incois_pfz._parse_decimal_degree("12.9 S") == pytest.approx(-12.9)
    assert incois_pfz._parse_decimal_degree("74.75 W") == pytest.approx(-74.75)


def test_parse_forecast_dates_handles_nested_layout_table() -> None:
    """The real INCOIS page nests the Forecast Date / Valid upto table inside
    an outer page-layout table - the parser must not lose it."""
    forecast_date, valid_until = incois_pfz._parse_forecast_dates(_TEXTDATA_HOME_HTML)
    assert forecast_date == "12 SEP 2026"
    assert valid_until == "13 SEP 2026"


def test_parse_decimal_degree_rejects_garbage() -> None:
    with pytest.raises(incois_pfz.SchemaValidationError):
        incois_pfz._parse_decimal_degree("not a coordinate")


def test_textdata_to_feature_collections_produces_point_geometry_only() -> None:
    """No fabricated line/polygon geometry: the Text Data fallback only ever
    carries the real official point the INCOIS forecast table gives us."""
    textdata = {
        "points": [
            {
                "from_coast": "Mangalore", "direction": "SW", "bearing_deg": 256.0,
                "distance_from_nm": 17.82, "distance_to_nm": 20.52,
                "depth_from_m": 56.0, "depth_to_m": 61.0,
                "latitude": 12.9, "longitude": 74.75,
            }
        ],
        "forecast_date": "12 SEP 2026",
        "valid_until": "13 SEP 2026",
    }
    lines_fc, landing_fc = incois_pfz.textdata_to_feature_collections(
        textdata, state_name="KARNATAKA"
    )
    for fc in (lines_fc, landing_fc):
        assert fc["type"] == "FeatureCollection"
        for feature in fc["features"]:
            assert feature["geometry"]["type"] == "Point"
    assert lines_fc["features"][0]["properties"]["State_Name"] == "KARNATAKA"
    landing_props = landing_fc["features"][0]["properties"]
    assert landing_props["LC_NAME"] == "Mangalore"
    assert landing_props["DISTANCE_F"] == 17.82
    assert landing_props["FORECAST_D"] == "12 SEP 2026"


# ---- 14. build_pfz_reference / fetch_matched_lines fall back to Text Data --
async def test_build_pfz_reference_falls_back_to_textdata_on_wfs_403(monkeypatch) -> None:
    async def _wfs_403(*a, **k):
        raise incois_pfz.IncoisPfzUnavailable("INCOIS PFZ WFS HTTP 403")

    async def _textdata(*, state_name, settings, client=None):
        assert state_name == "KARNATAKA"
        return {
            "points": [
                {
                    "from_coast": "Mangalore LC", "direction": "SW", "bearing_deg": 256.0,
                    "distance_from_nm": 17.82, "distance_to_nm": 20.52,
                    "depth_from_m": 56.0, "depth_to_m": 61.0,
                    "latitude": 12.88, "longitude": 74.85,
                }
            ],
            "forecast_date": "12 SEP 2026",
            "valid_until": "13 SEP 2026",
        }

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _wfs_403)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _wfs_403)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_textdata", _textdata)

    result = await build_pfz_reference(
        MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache())
    )
    assert result.availability is PfzAvailability.AVAILABLE
    assert result.area_matched == "KARNATAKA"
    assert result.zone_count == 1
    assert result.nearest_landing_centre is not None
    assert result.nearest_landing_centre.name == "Mangalore LC"
    assert "TextDataHome" in result.source_url


async def test_build_pfz_reference_unavailable_when_both_channels_fail(monkeypatch) -> None:
    async def _wfs_403(*a, **k):
        raise incois_pfz.IncoisPfzUnavailable("INCOIS PFZ WFS HTTP 403")

    async def _textdata_fails(*, state_name, settings, client=None):
        raise incois_pfz.PfzTextDataUnavailable("Text Data also unreachable")

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _wfs_403)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _wfs_403)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_textdata", _textdata_fails)

    result = await build_pfz_reference(
        MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache())
    )
    assert result.availability is PfzAvailability.UNAVAILABLE
    assert result.zone_count == 0


async def test_build_pfz_reference_unavailable_when_wfs_fails_outside_known_sector(
    monkeypatch,
) -> None:
    """No sector -> no Text Data secid to try; must stay honestly unavailable,
    never guess a sector for open-sea / out-of-bounds coordinates."""
    async def _wfs_403(*a, **k):
        raise incois_pfz.IncoisPfzUnavailable("INCOIS PFZ WFS HTTP 403")

    def _boom_if_called(*a, **k):
        raise AssertionError("Text Data must not be attempted without a matched sector")

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _wfs_403)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _wfs_403)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_textdata", _boom_if_called)

    far_out_at_sea = Coordinate(latitude=5.0, longitude=70.0)
    result = await build_pfz_reference(
        far_out_at_sea, settings=Settings(), cache=JsonCache(InMemoryCache())
    )
    assert result.availability is PfzAvailability.UNAVAILABLE


async def test_fetch_matched_lines_falls_back_to_textdata_on_wfs_403(monkeypatch) -> None:
    async def _wfs_403(*a, **k):
        raise incois_pfz.IncoisPfzUnavailable("INCOIS PFZ WFS HTTP 403")

    async def _textdata(*, state_name, settings, client=None):
        return {
            "points": [
                {
                    "from_coast": "Mangalore LC", "direction": "SW", "bearing_deg": 256.0,
                    "distance_from_nm": 17.82, "distance_to_nm": 20.52,
                    "depth_from_m": 56.0, "depth_to_m": 61.0,
                    "latitude": 12.88, "longitude": 74.85,
                }
            ],
            "forecast_date": "12 SEP 2026",
            "valid_until": "13 SEP 2026",
        }

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _wfs_403)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _wfs_403)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_textdata", _textdata)

    fc = await fetch_matched_lines(MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache()))
    assert fc["features"]
    assert all(f["geometry"]["type"] == "Point" for f in fc["features"])
    assert "Text Data" in fc["orca_meta"]["source"]
