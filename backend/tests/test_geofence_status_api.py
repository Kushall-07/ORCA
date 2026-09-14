"""Fisherman-demo fix (Part E): the API must never let "unavailable" read as
"clear" for the hard-geofence check.

``GisSummary.inside_hard_geofence: false`` alone is ambiguous between "checked
against real spatial data and found nothing" and "could not be checked at
all" - exactly the pitfall the master fix prompt calls out ("geofence
unavailable" != "no geofence violation"). ``geofence_status`` (see
app.orchestration.pipeline) makes the three cases explicit and traces
straight back to the already-tested ``_geofence_evaluated_clear`` in
app.orchestration.nodes, so these are the same three cases at the API
boundary rather than a new policy.
"""

from __future__ import annotations

from tests.orchestration_fakes import NOW, FakeGisAgent, make_pipeline


async def test_geofence_status_clear_when_gis_ran_with_real_data() -> None:
    r = await make_pipeline(gis=FakeGisAgent()).run(
        message="Is it safe to go fishing from Mangalore now?", session_id="gf-1", now=NOW,
    )
    assert r.gis is not None
    assert r.gis.geofence_status == "clear"
    assert r.gis.inside_hard_geofence is False


async def test_geofence_status_inside_when_hard_geofence_hit() -> None:
    gis = FakeGisAgent(inside_hard=True, hard_ids=("naval-exclusion-1",))
    r = await make_pipeline(gis=gis).run(
        message="Is it safe to go fishing from Mangalore now?", session_id="gf-2", now=NOW,
    )
    assert r.gis is not None
    assert r.gis.geofence_status == "inside"
    assert r.gis.inside_hard_geofence is True


async def test_geofence_status_unavailable_when_static_layers_not_loaded() -> None:
    gis = FakeGisAgent(
        warnings=(
            "static GIS layers not found at /nowhere; EEZ / coastline / depth / "
            "protected-area evidence is unavailable",
        ),
    )
    r = await make_pipeline(gis=gis).run(
        message="Is it safe to go fishing from Mangalore now?", session_id="gf-3", now=NOW,
    )
    assert r.gis is not None
    assert r.gis.geofence_status == "unavailable"
    # NEVER let "unavailable" read as a genuine "clear" finding.
    assert r.gis.inside_hard_geofence is False


async def test_geofence_status_unavailable_when_spatial_backend_unavailable() -> None:
    gis = FakeGisAgent(backend="unavailable")
    r = await make_pipeline(gis=gis).run(
        message="Is it safe to go fishing from Mangalore now?", session_id="gf-4", now=NOW,
    )
    assert r.gis is not None
    assert r.gis.geofence_status == "unavailable"


async def test_geofence_status_absent_when_gis_agent_fails_entirely() -> None:
    r = await make_pipeline(gis=FakeGisAgent(fail=True)).run(
        message="Is it safe to go fishing from Mangalore now?", session_id="gf-5", now=NOW,
    )
    assert r.gis is None
