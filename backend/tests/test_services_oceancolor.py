"""Phase 9 Step 2 - satellite ocean-colour (chlorophyll-a) client.

Every external call is mocked with respx. Nothing hits the network.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx

from app.core.config import Settings
from app.services import oceancolor as oc

NOAA_INFO = "https://coastwatch.noaa.gov/erddap/info/noaacwNPPVIIRSchlaDaily/index.json"
NOAA_DATA = "https://coastwatch.noaa.gov/erddap/griddap/noaacwNPPVIIRSchlaDaily.json"
INCOIS_INFO = "https://erddap.incois.gov.in/erddap/info/incoisChl/index.json"
INCOIS_DATA = "https://erddap.incois.gov.in/erddap/griddap/incoisChl.json"

LAT, LON = 12.87, 74.84
WHEN = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)


def _settings(**over) -> Settings:
    base = dict(oceancolor_enabled=True)
    base.update(over)
    return Settings(**base)


def _info(axes=("time", "altitude", "latitude", "longitude"), variable="chlor_a") -> dict:
    rows = [["dimension", a, "", "double", "nValues=10"] for a in axes]
    rows.append(["variable", variable, "", "float", ""])
    return {
        "table": {
            "columnNames": ["Row Type", "Variable Name", "Attribute Name", "Data Type", "Value"],
            "rows": rows,
        }
    }


def _table(rows, *, variable="chlor_a", with_altitude=True) -> dict:
    cols = ["time"]
    if with_altitude:
        cols.append("altitude")
    cols += ["latitude", "longitude", variable]
    return {"table": {"columnNames": cols, "columnUnits": ["UTC"] * len(cols), "rows": rows}}


def _row(days_before_when: float, value, *, lat=LAT + 0.01, lon=LON + 0.01, alt=True) -> list:
    t = (WHEN - timedelta(days=days_before_when)).strftime("%Y-%m-%dT12:00:00Z")
    base = [t]
    if alt:
        base.append(0)
    return base + [lat, lon, value]


# --------------------------------------------------------------------------
@respx.mock
async def test_url_construction_uses_griddap_json_and_axis_order() -> None:
    respx.get(NOAA_INFO).respond(json=_info())
    data = respx.get(NOAA_DATA).respond(json=_table([_row(1, 0.42)]))
    await oc.fetch_chlorophyll(LAT, LON, WHEN, settings=_settings())
    url = str(data.calls.last.request.url)
    assert "/griddap/noaacwNPPVIIRSchlaDaily.json?chlor_a" in url
    # axis order time-range, altitude index, lat, lon
    assert "%5B0%5D" in url or "[0]" in url          # altitude singleton
    assert "12.87000" in url and "74.84000" in url


@respx.mock
async def test_valid_response_parses_value_time_pixel_and_unit() -> None:
    respx.get(NOAA_INFO).respond(json=_info())
    respx.get(NOAA_DATA).respond(json=_table([_row(1.0, 0.55, lat=12.8751, lon=74.8449)]))
    r = await oc.fetch_chlorophyll(LAT, LON, WHEN, settings=_settings())
    assert isinstance(r, oc.ChlorophyllResult)
    assert r.value == pytest.approx(0.55)
    assert r.unit == "mg m-3"
    assert r.observed_at == datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
    assert r.observed_at.tzinfo is not None
    assert r.pixel_latitude == pytest.approx(12.8751)
    assert r.pixel_longitude == pytest.approx(74.8449)
    assert r.distance_m >= 0.0
    assert r.source == "noaa-coastwatch-erddap:noaacwNPPVIIRSchlaDaily"


@respx.mock
async def test_nearest_in_time_composite_is_selected() -> None:
    respx.get(NOAA_INFO).respond(json=_info())
    respx.get(NOAA_DATA).respond(json=_table([
        _row(5.0, 0.20), _row(1.0, 0.90), _row(3.0, 0.50),
    ]))
    r = await oc.fetch_chlorophyll(LAT, LON, WHEN, settings=_settings())
    assert r.value == pytest.approx(0.90)  # the 1-day-old row


@respx.mock
async def test_malformed_response_raises_schema_error() -> None:
    respx.get(NOAA_INFO).respond(json=_info())
    respx.get(NOAA_DATA).respond(json={"not": "a table"})
    with pytest.raises(oc.SchemaValidationError):
        await oc.fetch_chlorophyll(LAT, LON, WHEN, settings=_settings())


@respx.mock
async def test_non_json_response_raises_schema_error() -> None:
    respx.get(NOAA_INFO).respond(json=_info())
    respx.get(NOAA_DATA).respond(200, text="<html>ERDDAP error</html>")
    with pytest.raises(oc.SchemaValidationError):
        await oc.fetch_chlorophyll(LAT, LON, WHEN, settings=_settings())


@respx.mock
async def test_empty_rows_is_typed_no_data() -> None:
    respx.get(NOAA_INFO).respond(json=_info())
    respx.get(NOAA_DATA).respond(json=_table([]))
    with pytest.raises(oc.OceanColorNoData):
        await oc.fetch_chlorophyll(LAT, LON, WHEN, settings=_settings())


@respx.mock
async def test_all_nan_rows_is_no_data_and_never_zero() -> None:
    # ERDDAP .json emits null for NaN; some proxies emit the string "NaN".
    respx.get(NOAA_INFO).respond(json=_info())
    respx.get(NOAA_DATA).respond(json=_table([
        _row(1.0, None), _row(2.0, "NaN"), _row(3.0, None),
    ]))
    with pytest.raises(oc.OceanColorNoData):
        await oc.fetch_chlorophyll(LAT, LON, WHEN, settings=_settings())


@respx.mock
async def test_non_positive_values_are_dropped_not_used_as_zero() -> None:
    respx.get(NOAA_INFO).respond(json=_info())
    respx.get(NOAA_DATA).respond(json=_table([
        _row(1.0, 0.0), _row(2.0, -1.5), _row(4.0, 0.33),
    ]))
    r = await oc.fetch_chlorophyll(LAT, LON, WHEN, settings=_settings())
    assert r.value == pytest.approx(0.33)  # not 0.0


@respx.mock
async def test_spatial_rejection_when_pixel_too_far() -> None:
    respx.get(NOAA_INFO).respond(json=_info())
    respx.get(NOAA_DATA).respond(json=_table([_row(1.0, 0.4, lat=LAT + 0.6, lon=LON + 0.6)]))
    with pytest.raises(oc.OceanColorNoData):
        await oc.fetch_chlorophyll(LAT, LON, WHEN, settings=_settings())


@respx.mock
async def test_temporal_rejection_when_composite_too_old() -> None:
    respx.get(NOAA_INFO).respond(json=_info())
    respx.get(NOAA_DATA).respond(json=_table([_row(30.0, 0.4)]))  # 30 days old
    with pytest.raises(oc.OceanColorNoData) as ei:
        await oc.fetch_chlorophyll(LAT, LON, WHEN, settings=_settings())
    assert "freshest composite" in str(ei.value)


@respx.mock
async def test_range_404_retries_with_last() -> None:
    respx.get(NOAA_INFO).respond(json=_info())
    data = respx.get(NOAA_DATA)
    data.side_effect = [
        httpx.Response(404, text='Error {code=404; message="axis maximum";}'),
        httpx.Response(200, json=_table([_row(1.0, 0.71)])),
    ]
    r = await oc.fetch_chlorophyll(LAT, LON, WHEN, settings=_settings())
    assert r.value == pytest.approx(0.71)
    assert data.call_count == 2


@respx.mock
async def test_tls_transport_error_is_typed_unavailable() -> None:
    respx.get(NOAA_INFO).mock(
        side_effect=httpx.ConnectError("unable to verify the first certificate")
    )
    with pytest.raises(oc.OceanColorUnavailable):
        await oc.fetch_chlorophyll(LAT, LON, WHEN, settings=_settings())


@respx.mock
async def test_incois_fallback_used_when_noaa_yields_nothing() -> None:
    respx.get(NOAA_INFO).respond(json=_info())
    respx.get(NOAA_DATA).respond(json=_table([]))          # NOAA: cloud gap
    respx.get(INCOIS_INFO).respond(json=_info(axes=("time", "latitude", "longitude")))
    respx.get(INCOIS_DATA).respond(
        json=_table([_row(2.0, 0.61, alt=False)], with_altitude=False)
    )
    s = _settings(
        oceancolor_incois_erddap_url="https://erddap.incois.gov.in/erddap",
        oceancolor_incois_chl_dataset="incoisChl",
    )
    r = await oc.fetch_chlorophyll(LAT, LON, WHEN, settings=s)
    assert r.value == pytest.approx(0.61)
    assert r.source == "incois-erddap:incoisChl"


@respx.mock
async def test_incois_not_tried_when_not_configured() -> None:
    respx.get(NOAA_INFO).respond(json=_info())
    respx.get(NOAA_DATA).respond(json=_table([]))
    incois = respx.get(INCOIS_DATA).respond(json=_table([_row(1.0, 0.5)]))
    with pytest.raises(oc.OceanColorNoData):
        await oc.fetch_chlorophyll(LAT, LON, WHEN, settings=_settings())
    assert incois.call_count == 0


@respx.mock
async def test_both_sources_fail_raises_no_data_with_combined_context() -> None:
    respx.get(NOAA_INFO).respond(json=_info())
    respx.get(NOAA_DATA).respond(json=_table([]))
    respx.get(INCOIS_INFO).respond(json=_info(axes=("time", "latitude", "longitude")))
    respx.get(INCOIS_DATA).respond(json=_table([], with_altitude=False))
    s = _settings(
        oceancolor_incois_erddap_url="https://erddap.incois.gov.in/erddap",
        oceancolor_incois_chl_dataset="incoisChl",
    )
    with pytest.raises(oc.OceanColorNoData) as ei:
        await oc.fetch_chlorophyll(LAT, LON, WHEN, settings=s)
    assert "noaa" in str(ei.value).lower() and "incois" in str(ei.value).lower()


async def test_disabled_raises_not_configured() -> None:
    with pytest.raises(oc.OceanColorNotConfigured):
        await oc.fetch_chlorophyll(LAT, LON, WHEN, settings=_settings(oceancolor_enabled=False))


def test_oceancolor_status_shape() -> None:
    s = oc.oceancolor_status(_settings())
    assert s["role"] == "environmental / non-blocking"
    assert s["primary"].startswith("noaa-coastwatch-erddap:")
    assert s["fallback"] == "none (INCOIS not configured)"
    assert s["integrated"] is True
    assert "not a measure of fish presence" in s["note"]


def test_no_llm_or_langgraph_import_in_oceancolor() -> None:
    code = (
        "import sys, app.services.oceancolor;"
        "bad=[m for m in sys.modules if m.split('.')[0] in "
        "('groq','langgraph','langchain','langchain_core','openai','anthropic','ollama')];"
        "print('BAD' if bad else 'CLEAN', bad)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out.startswith("CLEAN"), out
