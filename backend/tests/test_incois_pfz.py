"""Official INCOIS PFZ reference: WFS fetch, deterministic spatial matching,
and the map-layer data contract. PFZ is a fishing-potential reference only -
see test_pfz_safety_isolation.py for the mandatory isolation checks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.agents.marine_area import lookup as lookup_area
from app.core.config import Settings
from app.gis import pfz_reference
from app.gis.pfz_reference import build_pfz_reference, build_pfz_zone_ranking, fetch_matched_lines
from app.models.common import Coordinate
from app.models.geo import Geofence, GeofenceSeverity, GeofenceType
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


# ---- 11b. WFS landing-centre static dates must never read as a live forecast -
# The official WFS landing-centres layer (~1223 nodes) bakes the SAME single
# FORECAST_D/VALIDITY_D timestamp into every node from whenever that layer was
# last rebuilt (verified live: identical across the whole dataset) - showing
# it as "valid until <that date>" to a query made long after would misleadingly
# read as a current forecast. Only the Text Data channel re-scrapes these two
# fields fresh every day, so they must only be surfaced when THAT is the
# source. The stable geographic profile (distance/direction/bearing/depth) is
# never time-sensitive and must still come through either way.
async def test_build_pfz_reference_wfs_landing_centre_static_dates_not_surfaced(
    monkeypatch,
) -> None:
    async def _lines(*a, **k):
        return _LINES_FC

    async def _landing_fc(*a, **k):
        return _LANDING_FC

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing_fc)
    result = await build_pfz_reference(
        MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache())
    )
    lc = result.nearest_landing_centre
    assert lc is not None
    # The raw fixture DOES carry FORECAST_D/VALIDITY_D (see _landing above) -
    # they must still be dropped because this result came from the WFS.
    assert lc.forecast_date is None
    assert lc.valid_until is None
    # Genuinely stable geographic fields are unaffected.
    assert lc.direction == "NW"
    assert lc.depth_from_m == 18.0
    assert lc.updated_at == "2026-09-11T06:00:00Z"


async def test_build_pfz_reference_textdata_landing_centre_dates_are_surfaced(
    monkeypatch,
) -> None:
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

    result = await build_pfz_reference(
        MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache())
    )
    lc = result.nearest_landing_centre
    assert lc is not None
    # Text Data is re-scraped fresh every query, so these ARE trustworthy here.
    assert lc.forecast_date == "12 SEP 2026"
    assert lc.valid_until == "13 SEP 2026"


# ---- 12. PFZ rendering data contract -----------------------------------------
async def test_fetch_matched_lines_returns_feature_collection_with_provenance(monkeypatch) -> None:
    async def _lines(*a, **k):
        return _LINES_FC

    async def _landing_fc(*a, **k):
        return _LANDING_FC

    # _fetch_pfz_feature_collections fetches lines AND landing centres together
    # (shared fallback decision) even though fetch_matched_lines only uses the
    # lines - both external boundaries must be mocked or the landing-centre
    # call falls through to the live INCOIS WFS/Text Data channels.
    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing_fc)
    fc = await fetch_matched_lines(MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache()))
    assert fc["type"] == "FeatureCollection"
    assert fc["orca_meta"]["authority"] == "INCOIS"
    assert "not a safety zone" in fc["orca_meta"]["disclaimer"]
    assert all(f["properties"]["State_Name"] == "KARNATAKA" for f in fc["features"])


# ---- 12b. map layer falls back to the landing centre when no line matched --
# A day with no PFZ LINE advisory for the query's sector (e.g. today's
# satellite pass skipped it - the real Karnataka/Mangalore case that exposed
# this) must not make GET /gis/layers/pfz render nothing while the chat
# answer (build_pfz_reference) reports a landing centre reference as
# available - see fetch_matched_lines's own comment. Two real official Point
# features, both clearly tagged, never a fabricated line/polygon: the landing
# centre itself, and (since the fixture's BEARING/DISTANCE_F/DISTANCE_T are
# usable) the point that landing centre's own published distance/bearing
# describes.
async def test_fetch_matched_lines_falls_back_to_landing_centre_when_no_lines_matched(
    monkeypatch,
) -> None:
    no_karnataka_lines_fc = {
        "type": "FeatureCollection",
        "features": [_line("KERALA", 76.20, 9.90), _line("GOA", 73.80, 15.30)],
    }

    async def _lines(*a, **k):
        return no_karnataka_lines_fc

    async def _landing_fc(*a, **k):
        return _LANDING_FC

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing_fc)
    fc = await fetch_matched_lines(MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache()))
    assert len(fc["features"]) == 2
    landing_feature, projected_feature = fc["features"]
    assert landing_feature["properties"]["orca_feature_kind"] == "LANDING_CENTRE"
    assert landing_feature["properties"]["LC_NAME"] == "Mangalore LC"
    assert landing_feature["geometry"]["type"] == "Point"
    assert landing_feature["properties"]["orca_distance_km"] is not None
    assert projected_feature["properties"]["orca_feature_kind"] == "PROJECTED_ADVISORY_POINT"
    assert projected_feature["geometry"]["type"] == "Point"
    assert "Mangalore LC" in projected_feature["properties"]["derived_from"]
    # The projected point must not be the same coordinate as the landing
    # centre - it moved along the published bearing/distance.
    assert projected_feature["geometry"]["coordinates"] != landing_feature["geometry"]["coordinates"]


async def test_fetch_matched_lines_no_lines_and_no_landing_centre_is_empty(
    monkeypatch,
) -> None:
    async def _lines(*a, **k):
        return {"type": "FeatureCollection", "features": [_line("KERALA", 76.20, 9.90)]}

    async def _landing_fc(*a, **k):
        return {"type": "FeatureCollection", "features": [_landing("KERALA", 9.97, 76.24, "Kochi LC")]}

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing_fc)
    fc = await fetch_matched_lines(
        Coordinate(latitude=13.0, longitude=72.0),  # open sea, far from Kerala
        settings=Settings(), cache=JsonCache(InMemoryCache()),
    )
    assert fc["features"] == []


# ---- WFS endpoint URL (root-cause regression) --------------------------------
# The live INCOIS WebGIS's own js/featureinfo.js never calls the GLOBAL
# /geoserver/ows endpoint (verified live: it returns HTTP 403 independent of
# ORCA) - it calls the PER-WORKSPACE path (e.g. /geoserver/PFZ_Automation/ows),
# which is public and returns real data. An earlier version of this module
# built the global URL instead, so every WFS fetch failed and fell through to
# the Text Data fallback even though the WFS was actually reachable.
async def test_fetch_wfs_geojson_uses_per_workspace_ows_path_not_global() -> None:
    captured_urls: list[str] = []

    class _FakeResponse:
        status_code = 200

        def json(self):
            return {"type": "FeatureCollection", "features": []}

    class _FakeClient:
        async def get(self, url, timeout):
            captured_urls.append(url)
            return _FakeResponse()

    await incois_pfz._fetch_wfs_geojson(
        base_url="https://www.incois.gov.in/geoserver",
        type_name="PFZ_Automation:pfzlines", timeout_s=5.0, client=_FakeClient(),
    )
    assert captured_urls == [
        "https://www.incois.gov.in/geoserver/PFZ_Automation/ows"
        "?service=WFS&version=1.1.0&request=GetFeature"
        "&typeName=PFZ_Automation:pfzlines&outputFormat=application/json"
    ]
    assert "/geoserver/ows?" not in captured_urls[0]


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


# ---- 14b. last-known-good: a stale but real snapshot when BOTH channels ---
# fail on a LATER query, after an EARLIER query already succeeded for the
# same sector (see app.gis.pfz_reference._fetch_pfz_feature_collections).
# Never a third source, never fabricated - the exact same WFS/Text Data
# payload that was already served live once, just replayed with its real
# original fetch time and labelled stale.
async def test_build_pfz_reference_uses_last_known_good_when_both_channels_fail(
    monkeypatch,
) -> None:
    # Prime the last-known-good snapshot directly (bypassing the ordinary
    # day-bucketed hot cache, which would otherwise mask "both channels down"
    # on a same-day retry with its own already-cached success).
    cache = JsonCache(InMemoryCache())
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    await pfz_reference._save_last_good(
        cache, "KARNATAKA", _LINES_FC, _LANDING_FC, pfz_reference._WFS_SOURCE_URL,
        settings=Settings(), fetched_at=yesterday,
    )

    async def _wfs_403(*a, **k):
        raise incois_pfz.IncoisPfzUnavailable("INCOIS PFZ WFS HTTP 403")

    async def _textdata_fails(*, state_name, settings, client=None):
        raise incois_pfz.PfzTextDataUnavailable("Text Data also unreachable")

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _wfs_403)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _wfs_403)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_textdata", _textdata_fails)

    result = await build_pfz_reference(MANGALORE, settings=Settings(), cache=cache)
    assert result.availability is PfzAvailability.AVAILABLE
    assert result.zone_count == 2
    assert result.area_matched == "KARNATAKA"
    assert result.is_stale is True
    assert result.data_retrieved_at == yesterday
    assert result.data_retrieved_at < result.retrieved_at


async def test_build_pfz_zone_ranking_uses_last_known_good_when_both_channels_fail(
    monkeypatch,
) -> None:
    cache = JsonCache(InMemoryCache())
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    await pfz_reference._save_last_good(
        cache, "KARNATAKA", _LINES_FC, _LANDING_FC, pfz_reference._WFS_SOURCE_URL,
        settings=Settings(), fetched_at=yesterday,
    )

    async def _boom(*a, **k):
        raise incois_pfz.IncoisPfzUnavailable("simulated outage")

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _boom)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _boom)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_textdata", _boom)

    result = await build_pfz_zone_ranking(MANGALORE, settings=Settings(), cache=cache)
    assert result.availability is PfzAvailability.AVAILABLE
    assert len(result.zones) == 2
    assert result.is_stale is True
    assert result.data_retrieved_at == yesterday


async def test_build_pfz_reference_no_last_known_good_stays_honestly_unavailable(
    monkeypatch,
) -> None:
    """No sector has ever succeeded before (fresh cache) - both live channels
    failing must stay a true UNAVAILABLE, never silently invent a snapshot."""
    async def _boom(*a, **k):
        raise incois_pfz.IncoisPfzUnavailable("simulated outage")

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _boom)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _boom)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_textdata", _boom)

    result = await build_pfz_reference(
        MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache())
    )
    assert result.availability is PfzAvailability.UNAVAILABLE
    assert result.is_stale is False


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


# ---- 15. ranked individual PFZ zones (additive to build_pfz_reference) ----
def test_rank_matched_lines_sorts_by_real_distance() -> None:
    """match_nearby_lines' same-sector branch is dataset order, not distance
    order - rank_matched_lines must re-sort by real nearest-point distance
    regardless, so "PFZ zone 1" is genuinely the closest one."""
    area = lookup_area(MANGALORE)
    ranked = incois_pfz.rank_matched_lines(
        _LINES_FC, MANGALORE, state_name=area.state_name,
        max_distance_km=250.0, max_features=40,
    )
    assert len(ranked) == 2
    distances = [d for _f, d, _lat, _lon in ranked]
    assert distances == sorted(distances)


async def test_build_pfz_zone_ranking_available_with_ranked_zones(monkeypatch) -> None:
    async def _lines(*a, **k):
        return _LINES_FC

    async def _landing_fc(*a, **k):
        return _LANDING_FC

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing_fc)
    result = await build_pfz_zone_ranking(
        MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache())
    )
    assert result.availability is PfzAvailability.AVAILABLE
    assert result.area_matched == "KARNATAKA"
    assert [z.rank for z in result.zones] == [1, 2]
    assert result.zones[0].distance_km <= result.zones[1].distance_km
    assert len({z.id for z in result.zones}) == len(result.zones)  # ids unique
    assert all(z.restricted is False for z in result.zones)


async def test_build_pfz_zone_ranking_flags_restricted_zone_from_hard_geofence(
    monkeypatch,
) -> None:
    """restricted / nearest_hard_geofence_m reuse the SAME check_geofences the
    route planner and Safety Guard use - display only, never fed back into
    either (safety-isolation preserved)."""
    async def _lines(*a, **k):
        return _LINES_FC

    async def _landing_fc(*a, **k):
        return _LANDING_FC

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing_fc)

    # Covers only the first Karnataka line's geometry (lon 74.83-74.90, lat
    # 12.88-12.97), not the second (lat 12.70-12.75).
    hard_fence = Geofence(
        id="test-hard-1", name="Test hard restriction",
        geofence_type=GeofenceType.RESTRICTED, severity=GeofenceSeverity.HARD,
        geometry_wkt="POLYGON((74.83 12.88, 74.83 12.97, 74.90 12.97, 74.90 12.88, 74.83 12.88))",
    )
    result = await build_pfz_zone_ranking(
        MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache()),
        hard_geofences=(hard_fence,),
    )
    assert result.availability is PfzAvailability.AVAILABLE
    restricted_flags = {z.rank: z.restricted for z in result.zones}
    assert any(restricted_flags.values())
    assert not all(restricted_flags.values())


async def test_build_pfz_zone_ranking_unavailable_on_transport_error(monkeypatch) -> None:
    async def _boom(*a, **k):
        raise incois_pfz.IncoisPfzUnavailable("simulated outage")

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _boom)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _boom)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_textdata", _boom)
    result = await build_pfz_zone_ranking(
        MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache())
    )
    assert result.availability is PfzAvailability.UNAVAILABLE
    assert result.zones == ()


# ---- projected advisory point (no line advisory, but a WFS landing centre's
# own published distance/bearing describes a real advised point) -----------
# The WFS landing-centres layer's LATITUDE/LONGITUDE is the coastal landing
# centre itself, not the advised fishing area - DISTANCE_F/DISTANCE_T (nm)
# and BEARING separately describe how far/which way the actual advisory zone
# is from there. When no PFZ line advisory matched at all, ORCA computes that
# described point with plain WGS84 geodesic trigonometry on those official
# published numbers - never an estimate, never derived from SST/CHL, and
# clearly labelled everywhere as computed (geometry_source /
# PROJECTED_ADVISORY_POINT), never conflated with a real matched line.
async def test_destination_point_geodesic_matches_known_offset() -> None:
    from app.gis.operations import destination_point_geodesic, geodesic_distance_m

    lat, lon = 12.85, 74.84
    proj_lat, proj_lon = destination_point_geodesic(lat, lon, bearing_deg=0.0, distance_m=1852.0)
    # Due north by exactly 1 nm: latitude increases, longitude essentially
    # unchanged, and the round-trip distance matches what was requested.
    assert proj_lat > lat
    assert abs(proj_lon - lon) < 1e-6
    assert geodesic_distance_m(lat, lon, proj_lat, proj_lon) == pytest.approx(1852.0, rel=1e-3)


async def test_build_pfz_reference_sets_projected_zone_when_no_lines_matched(monkeypatch) -> None:
    no_karnataka_lines_fc = {
        "type": "FeatureCollection",
        "features": [_line("KERALA", 76.20, 9.90)],
    }

    async def _lines(*a, **k):
        return no_karnataka_lines_fc

    async def _landing_fc(*a, **k):
        return _LANDING_FC

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing_fc)
    result = await build_pfz_reference(
        MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache())
    )
    assert result.zone_count == 0  # never inflated by the projected point
    assert result.projected_zone is not None
    assert result.projected_zone.geometry_source == "PROJECTED_FROM_LANDING_CENTRE"
    assert "Mangalore LC" in result.projected_zone.derived_from
    assert result.projected_zone.latitude != result.nearest_landing_centre.latitude


async def test_build_pfz_reference_no_projected_zone_when_lines_matched(monkeypatch) -> None:
    async def _lines(*a, **k):
        return _LINES_FC

    async def _landing_fc(*a, **k):
        return _LANDING_FC

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing_fc)
    result = await build_pfz_reference(
        MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache())
    )
    assert result.zone_count > 0
    assert result.projected_zone is None


async def test_build_pfz_zone_ranking_falls_back_to_projected_point(monkeypatch) -> None:
    # _LANDING_FC has TWO KARNATAKA-sector landing centres ("Mangalore LC",
    # "Far LC") within the default 250km match radius, plus one KERALA-sector
    # one ("Kochi LC") excluded by the same-sector-first rule. The fallback
    # must surface BOTH real KARNATAKA references, not collapse to only the
    # single nearest one (the exact regression this test used to encode -
    # see rank_landing_centres and build_pfz_zone_ranking's fallback).
    no_karnataka_lines_fc = {
        "type": "FeatureCollection",
        "features": [_line("KERALA", 76.20, 9.90)],
    }

    async def _lines(*a, **k):
        return no_karnataka_lines_fc

    async def _landing_fc(*a, **k):
        return _LANDING_FC

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing_fc)
    result = await build_pfz_zone_ranking(
        MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache())
    )
    assert result.availability is PfzAvailability.AVAILABLE
    assert len(result.zones) == 2
    names = {z.derived_from for z in result.zones}
    assert any("Mangalore LC" in n for n in names)
    assert any("Far LC" in n for n in names)
    assert all(z.geometry_source == "PROJECTED_FROM_LANDING_CENTRE" for z in result.zones)
    # Ranked 1..N, nearest-first, by the PROJECTED point's own distance.
    assert [z.rank for z in result.zones] == [1, 2]
    assert result.zones[0].distance_km <= result.zones[1].distance_km
    ids = [z.id for z in result.zones]
    assert len(ids) == len(set(ids))  # stable, unique per-zone identity


async def test_build_pfz_zone_ranking_projected_fallback_single_reference(monkeypatch) -> None:
    """Exactly one landing centre in range must still work (not just >=2)."""
    kochi_only_fc = {
        "type": "FeatureCollection",
        "features": [_landing("KERALA", 9.97, 76.24, "Kochi LC")],
    }
    no_lines_fc = {"type": "FeatureCollection", "features": []}

    async def _lines(*a, **k):
        return no_lines_fc

    async def _landing_fc(*a, **k):
        return kochi_only_fc

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing_fc)
    result = await build_pfz_zone_ranking(
        Coordinate(latitude=9.93, longitude=76.26),
        settings=Settings(), cache=JsonCache(InMemoryCache()),
    )
    assert result.availability is PfzAvailability.AVAILABLE
    assert len(result.zones) == 1
    assert result.zones[0].rank == 1
    assert "Kochi LC" in result.zones[0].derived_from


async def test_build_pfz_zone_ranking_projected_fallback_caps_at_max_ranked_zones(
    monkeypatch,
) -> None:
    """15 real landing centres in range must cap at 10 (_MAX_RANKED_ZONES),
    never fabricate more and never silently drop to fewer than the cap."""
    many_landing_fc = {
        "type": "FeatureCollection",
        "features": [
            _landing("KARNATAKA", 12.80 + i * 0.02, 74.80 + i * 0.02, f"LC {i}")
            for i in range(15)
        ],
    }
    no_lines_fc = {"type": "FeatureCollection", "features": []}

    async def _lines(*a, **k):
        return no_lines_fc

    async def _landing_fc(*a, **k):
        return many_landing_fc

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing_fc)
    result = await build_pfz_zone_ranking(
        MANGALORE, settings=Settings(), cache=JsonCache(InMemoryCache())
    )
    assert result.availability is PfzAvailability.AVAILABLE
    assert len(result.zones) == 10
    assert [z.rank for z in result.zones] == list(range(1, 11))
    distances = [z.distance_km for z in result.zones]
    assert distances == sorted(distances)
    ids = [z.id for z in result.zones]
    assert len(ids) == len(set(ids))
