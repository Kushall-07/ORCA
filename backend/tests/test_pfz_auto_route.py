"""Automatic PFZ-to-route destination for an explicit compound "PFZ + route"
natural-language request, e.g. "Show me the nearest PFZ at Mangalore and
route me there." (see app.orchestration.nodes.normalize /
app.gis.pfz_reference.resolve_pfz_route_destination).

Two independent concerns are covered:

* the isolated resolver (``resolve_pfz_route_destination`` /
  ``incois_pfz.nearest_pfz_zone_point``) - deterministic nearest-zone-point
  matching against the SAME official INCOIS dataset the map layer and the PFZ
  reference summary already use;
* the full pipeline - intent detection, automatic PFZ selection wired into
  route_node without any manual UI click, and the two interaction modes
  (Mode A: "... and route me there." vs Mode B: PFZ reference only) staying
  distinct exactly as before.
"""

from __future__ import annotations

from app.agents.query_understanding import QueryUnderstandingAgent
from app.core.config import Settings
from app.gis.pfz_reference import resolve_pfz_route_destination
from app.models.common import Coordinate
from app.services import incois_pfz
from app.services.cache import InMemoryCache, JsonCache
from tests.orchestration_fakes import NOW, FakeWeatherAgent, make_pipeline

WATER_ORIGIN = Coordinate(latitude=12.85, longitude=74.60)       # confirmed navigable water
WATER_DESTINATION = Coordinate(latitude=12.85, longitude=74.70)  # confirmed navigable water
MANGALORE_CITY = Coordinate(latitude=12.87, longitude=74.84)     # on land (real bathymetry)

COMPOUND_QUERY = "Show me the nearest PFZ at Mangalore and route me there."
PFZ_ONLY_QUERY = "Show me the nearest PFZ at Mangalore."


def _zone_point_feature(lat: float, lon: float, *, state: str = "KARNATAKA") -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {"State_Name": state, "Julian_day": "250"},
    }


def _landing_centre_feature(lat: float, lon: float, name: str) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
            "SECTOR_NAM": "KARNATAKA", "LC_NAME": name, "DIST_NAME": "Dakshina Kannada",
            "LATITUDE": lat, "LONGITUDE": lon, "DIRECTION": "SW", "BEARING": 260,
            "DISTANCE_F": 18, "DISTANCE_T": 23, "DEPTH_FROM": 20, "DEPTH_TO": 25,
            "FORECAST_D": "2026-09-11T18:30:00Z", "VALIDITY_D": "2026-09-12T18:30:00Z",
            "UPDATED_DA": "2026-09-11T06:00:00Z",
        },
    }


def _patch_pfz_fetches(monkeypatch, *, lines_fc: dict | None = None, landing_fc: dict | None = None) -> None:
    async def _lines(*a, **k):
        return lines_fc or {"type": "FeatureCollection", "features": []}

    async def _landing(*a, **k):
        return landing_fc or {"type": "FeatureCollection", "features": []}

    monkeypatch.setattr(incois_pfz, "fetch_pfz_lines", _lines)
    monkeypatch.setattr(incois_pfz, "fetch_pfz_landing_centres", _landing)


def _cache() -> JsonCache:
    return JsonCache(InMemoryCache())


# ---- 1. "... and route me there." sets requests_route (and requests_pfz) --
async def test_compound_query_sets_requests_route_and_requests_pfz() -> None:
    u = await QueryUnderstandingAgent(None).understand(
        COMPOUND_QUERY, session=None, language_hint=None
    )
    assert u.requests_route is True
    assert u.requests_pfz is True


async def test_pfz_only_query_does_not_set_requests_route() -> None:
    u = await QueryUnderstandingAgent(None).understand(
        PFZ_ONLY_QUERY, session=None, language_hint=None
    )
    assert u.requests_route is False
    assert u.requests_pfz is True


# ---- isolated resolver: deterministic nearest PFZ zone point --------------
async def test_resolve_pfz_route_destination_returns_nearest_zone_point(monkeypatch) -> None:
    _patch_pfz_fetches(monkeypatch, lines_fc={
        "type": "FeatureCollection",
        "features": [
            _zone_point_feature(12.85, 74.70),                       # near, same sector
            _zone_point_feature(9.97, 76.24, state="KERALA"),         # far, different sector
        ],
    })
    result = await resolve_pfz_route_destination(
        WATER_ORIGIN, settings=Settings(), cache=_cache(),
    )
    assert result.available is True
    assert result.coordinate == WATER_DESTINATION
    assert result.distance_km is not None
    assert result.area_matched == "KARNATAKA"


async def test_resolve_pfz_route_destination_unavailable_when_no_zone_matches(monkeypatch) -> None:
    _patch_pfz_fetches(monkeypatch, lines_fc={"type": "FeatureCollection", "features": []})
    result = await resolve_pfz_route_destination(
        WATER_ORIGIN, settings=Settings(), cache=_cache(),
    )
    assert result.available is False
    assert result.coordinate is None


# ---- 2/3/4. PFZ auto-selected and wired into route_node's destination -----
async def test_pfz_auto_selected_and_wired_into_route_destination(monkeypatch) -> None:
    _patch_pfz_fetches(monkeypatch, lines_fc={
        "type": "FeatureCollection", "features": [_zone_point_feature(12.85, 74.70)],
    })
    pipe = make_pipeline()
    r = await pipe.run(
        message=COMPOUND_QUERY, session_id="s-pfz-1", coordinate=WATER_ORIGIN, now=NOW,
    )
    assert r.route is not None
    assert r.route.pfz_auto_destination is True
    assert r.route.destination == [WATER_DESTINATION.latitude, WATER_DESTINATION.longitude]


# ---- 5. route is generated without any manual UI click ---------------------
async def test_route_generated_without_manual_navigate_click(monkeypatch) -> None:
    _patch_pfz_fetches(monkeypatch, lines_fc={
        "type": "FeatureCollection", "features": [_zone_point_feature(12.85, 74.70)],
    })
    pipe = make_pipeline()
    r = await pipe.run(
        message=COMPOUND_QUERY, session_id="s-pfz-2", coordinate=WATER_ORIGIN, now=NOW,
    )
    assert r.route is not None
    assert r.route.status == "ROUTE_FOUND"
    assert "Found the nearest official INCOIS PFZ reference and routed you there." in r.answer


# ---- 6. PFZ-only query: PFZ shown, no automatic route ----------------------
async def test_pfz_only_query_shows_pfz_without_auto_routing(monkeypatch) -> None:
    _patch_pfz_fetches(monkeypatch, lines_fc={
        "type": "FeatureCollection", "features": [_zone_point_feature(12.85, 74.70)],
    })
    pipe = make_pipeline()
    r = await pipe.run(
        message=PFZ_ONLY_QUERY, session_id="s-pfz-3", coordinate=WATER_ORIGIN, now=NOW,
    )
    assert r.route is None
    assert r.pfz_reference is not None
    assert r.pfz_reference.availability == "available"


# ---- 7. explicit PFZ route preserves safety isolation ----------------------
def test_pfz_auto_route_state_never_reaches_risk_or_safety_models() -> None:
    from app.gis.pfz_reference import PfzRouteDestination  # noqa: F401 - exists, importable
    from app.models.safety import SafetyGuardInput
    from app.risk.engine import RiskEngineInput

    assert "pfz_route_destination" not in RiskEngineInput.model_fields
    assert "pfz_route_destination" not in SafetyGuardInput.model_fields
    assert "pfz_route_destination" not in RiskEngineInput.model_fields
    assert not any("pfz" in f.lower() for f in RiskEngineInput.model_fields)
    assert not any("pfz" in f.lower() for f in SafetyGuardInput.model_fields)


# ---- 8. maritime-origin substitution still works alongside PFZ auto-route -
async def test_maritime_origin_substitution_and_pfz_auto_route_together(monkeypatch) -> None:
    _patch_pfz_fetches(
        monkeypatch,
        lines_fc={"type": "FeatureCollection", "features": [_zone_point_feature(12.85, 74.70)]},
        landing_fc={"type": "FeatureCollection", "features": [
            _landing_centre_feature(12.85, 74.60, "Mangalore Fishing Harbour"),
        ]},
    )
    pipe = make_pipeline()
    r = await pipe.run(
        message=COMPOUND_QUERY, session_id="s-pfz-4", coordinate=MANGALORE_CITY, now=NOW,
    )
    assert r.route is not None
    assert r.route.status == "ROUTE_FOUND"
    assert r.route.maritime_origin_verified is True
    assert r.route.pfz_auto_destination is True
    # The ordinary safety-query location this turn is still the raw city coordinate.
    assert r.location is not None
    assert r.location.latitude == MANGALORE_CITY.latitude


# ---- 9. PFZ unavailable -> honest response, no fabricated route -----------
async def test_pfz_unavailable_gives_honest_response_no_fabricated_route(monkeypatch) -> None:
    _patch_pfz_fetches(monkeypatch)  # no lines, no landing centres anywhere
    pipe = make_pipeline()
    r = await pipe.run(
        message=COMPOUND_QUERY, session_id="s-pfz-5", coordinate=WATER_ORIGIN, now=NOW,
    )
    assert r.route is None
    assert "unavailable" in r.answer.lower()


# ---- 10. NO_SAFE_RECOMMENDATION: PFZ may show, route must not be generated
async def test_no_safe_recommendation_blocks_auto_route_but_pfz_may_still_show(monkeypatch) -> None:
    _patch_pfz_fetches(monkeypatch, lines_fc={
        "type": "FeatureCollection", "features": [_zone_point_feature(12.85, 74.70)],
    })
    pipe = make_pipeline(weather=FakeWeatherAgent(missing=True))
    r = await pipe.run(
        message=COMPOUND_QUERY, session_id="s-pfz-6", coordinate=WATER_ORIGIN, now=NOW,
    )
    assert r.decision is not None
    assert r.decision.status == "NO_SAFE_RECOMMENDATION"
    assert r.route is None
    assert r.pfz_reference is not None
    assert r.pfz_reference.availability == "available"


# ---- 11. manual "Navigate to this PFZ" (destination_override) still works -
async def test_manual_destination_override_still_works_and_is_not_flagged_auto(monkeypatch) -> None:
    _patch_pfz_fetches(monkeypatch, lines_fc={
        "type": "FeatureCollection", "features": [_zone_point_feature(12.85, 74.70)],
    })
    pipe = make_pipeline()
    r = await pipe.run(
        message="conditions here",  # the manual flow sends no route wording
        session_id="s-pfz-7",
        coordinate=WATER_ORIGIN,
        destination=WATER_DESTINATION,
        now=NOW,
    )
    assert r.route is not None
    assert r.route.status == "ROUTE_FOUND"
    assert r.route.destination == [WATER_DESTINATION.latitude, WATER_DESTINATION.longitude]
    # Even though the coordinate happens to match a PFZ zone, this came from
    # the explicit destination_override path, not automatic PFZ selection.
    assert r.route.pfz_auto_destination is False


# ---- a real second place is never overridden by PFZ auto-selection --------
async def test_route_with_two_distinct_named_places_is_not_overridden_by_pfz(monkeypatch) -> None:
    _patch_pfz_fetches(monkeypatch, lines_fc={
        "type": "FeatureCollection", "features": [_zone_point_feature(12.85, 74.70)],
    })
    pipe = make_pipeline()
    r = await pipe.run(
        message="Give me a route from here to Kochi and show me the nearest PFZ.",
        session_id="s-pfz-8",
        coordinate=WATER_ORIGIN,
        now=NOW,
    )
    if r.route is not None:
        assert r.route.pfz_auto_destination is False
