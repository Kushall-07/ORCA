"""Fisherman-demo fix (Part E follow-up): "offline" is the identifier of
WHICH spatial backend answered the query (the git-tracked static/local
reference layers, vs. "postgis" for the live database), NOT an availability
flag - the genuine-failure case is the separate string "unavailable" (see
app.agents.gis_geofencing.GisGeofencingAgent.query). Bare in a provenance /
report view, "offline" reads to a demo audience as "the GIS check did not
run", even when the check genuinely executed against real data (e.g. the
Mandapam / Gulf of Mannar protected-area intersection below).

``GisQueryResult.backend_label`` (app.models.gis_agent) relabels this for
display only; ``.backend`` itself, the geofence decision, the risk factor and
every safety/routing input are all completely unchanged - these tests lock in
that the relabelling is purely cosmetic and consistently applied everywhere
the raw value used to leak through (provenance, data_quality.gis_backend).
"""

from __future__ import annotations

from app.models.decision import DecisionStatus
from app.models.gis_agent import EezResult, GisQueryResult
from app.models.common import Coordinate
from app.models.fabric import DataTier, SourceStatus

from tests.orchestration_fakes import NOW, FakeGisAgent, make_pipeline, protected

COORD = Coordinate(latitude=12.87, longitude=74.84)


def _gis(backend: str) -> GisQueryResult:
    return GisQueryResult(
        coordinate=COORD, backend=backend,
        source_status=SourceStatus(tier=DataTier.REFERENCE, source=f"static-gis:{backend}"),
        eez=EezResult(inside=True, zones=("Indian Exclusive Economic Zone",)),
    )


def test_offline_backend_labelled_as_static_local_checked() -> None:
    assert _gis("offline").backend_label == "Static/local reference data (checked)"


def test_postgis_backend_labelled_as_live_database() -> None:
    assert _gis("postgis").backend_label == "PostGIS (live database)"


def test_unavailable_backend_stays_unavailable() -> None:
    assert _gis("unavailable").backend_label == "Unavailable"


def test_backend_raw_value_unchanged_by_label() -> None:
    """The label is a display-only derived property; .backend (what every
    other test and the geofence-decision code path reads) is untouched."""
    g = _gis("offline")
    assert g.backend == "offline"
    assert g.backend_label != g.backend


# ---------------------------------------------------------------------------
# End-to-end: provenance and data_quality both show the SAME friendly label,
# never the bare "offline" string, while geofence_status / risk / safety are
# unaffected. Required-test 1 (Mangalore, clear) and required-test 5
# (provenance + API agree) from the master fix prompt.
# ---------------------------------------------------------------------------
async def test_mangalore_clear_check_shows_friendly_label_everywhere() -> None:
    r = await make_pipeline(gis=FakeGisAgent()).run(
        message="Is it safe to go fishing from Mangalore now?", session_id="lbl-1", now=NOW,
    )
    assert r.gis is not None
    assert r.gis.geofence_status == "clear"
    assert r.gis.backend == "offline"
    assert r.data_quality.gis_backend == "Static/local reference data (checked)"
    gis_node = next(n for n in r.provenance["nodes"] if n["id"] == "agent:gis")
    assert gis_node["value"] == "Static/local reference data (checked)"
    assert gis_node["detail"]["backend"] == "offline"


# Required-test 2: Mandapam - a real protected-area intersection is detected
# and reported, and does not change geofence_status ("clear" stays honest -
# see app.orchestration.nodes._geofence_evaluated_clear / GisGeofencingAgent's
# own "a protected area becomes HARD only when the operator configures it").
async def test_mandapam_protected_area_intersection_does_not_flip_geofence_status() -> None:
    gis = FakeGisAgent(protected_areas=(protected(inside=True),))
    r = await make_pipeline(gis=gis).run(
        message="Is it safe to go fishing near Mandapam now?", session_id="lbl-2", now=NOW,
    )
    assert r.gis is not None
    assert any(p.inside for p in r.gis.protected_areas)
    assert r.gis.inside_hard_geofence is False
    assert r.gis.geofence_status == "clear"


# Required-test 3: a hard geofence actually triggers.
async def test_hard_geofence_hit_reports_inside_everywhere() -> None:
    gis = FakeGisAgent(inside_hard=True, hard_ids=("naval-exclusion-1",))
    r = await make_pipeline(gis=gis).run(
        message="Is it safe to go fishing from Mangalore now?", session_id="lbl-3", now=NOW,
    )
    assert r.gis is not None
    assert r.gis.geofence_status == "inside"
    assert r.decision.status == DecisionStatus.DO_NOT_PROCEED.value


# Required-test 4: genuine GIS unavailable (spatial backend raised).
async def test_gis_agent_failure_reports_unavailable_not_clear() -> None:
    r = await make_pipeline(gis=FakeGisAgent(fail=True)).run(
        message="Is it safe to go fishing from Mangalore now?", session_id="lbl-4", now=NOW,
    )
    # The whole gis summary is absent when the agent itself failed (see
    # app.orchestration.nodes.collect_gis) - never silently reported "clear".
    assert r.gis is None


# risk_factor:geofence policy check - intentional, not a contradiction with
# geofence_status: the deterministic membership check (inside/not-inside a
# HARD zone) and the RiskEngine's CONTINUOUS distance-based scoring factor
# are different questions (see app.risk.factors.evaluate_geofence_factor and
# the comment on app.orchestration.nodes._geofence_evaluated_clear). With no
# continuous distance-to-nearest-hard-geofence dataset configured, the
# numeric factor is honestly MISSING_DATA for scoring purposes even though
# the binary membership check that feeds geofence_status ran and is
# conclusive.
async def test_geofence_risk_factor_missing_data_is_not_a_contradiction_with_clear_status() -> None:
    r = await make_pipeline(gis=FakeGisAgent()).run(
        message="Is it safe to go fishing from Mangalore now?", session_id="lbl-5", now=NOW,
    )
    assert r.gis.geofence_status == "clear"
    geofence_factor_node = next(
        n for n in r.provenance["nodes"] if n["id"] == "risk_factor:geofence"
    )
    assert geofence_factor_node["value"] == "missing_data"
