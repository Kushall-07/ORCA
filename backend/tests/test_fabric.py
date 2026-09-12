"""Marine Data Fabric builder - normalisation, provenance, gate integration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.agents.base import AgentResult
from app.fabric.builder import build_fabric
from app.models.common import Coordinate, SignalKind, SourceTier
from app.models.fabric import DataTier, SourceStatus, ValidityState
from app.models.gis_agent import EezResult, GisQueryResult
from app.models.observations import MarineObservation

COORD = Coordinate(latitude=12.87, longitude=74.84)
T = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def _obs(variable, value, unit, *, valid=True):
    return MarineObservation(
        variable=variable, value=value, unit=unit, coordinate=COORD,
        valid_from=T - timedelta(minutes=30) if valid else T - timedelta(days=3),
        valid_until=T + timedelta(minutes=30) if valid else T - timedelta(days=2),
        retrieved_at=T - timedelta(minutes=5),
        source="open-meteo-marine", source_tier=SourceTier.MODEL,
        signal_kind=SignalKind.MODEL_DERIVED,
    )


def _agent_result(kind, observations, tier=DataTier.LIVE, source="open-meteo-marine"):
    return AgentResult(
        kind=kind, coordinate=COORD, query_time=T,
        observations=tuple(observations),
        source_status=SourceStatus(tier=tier, source=source, retrieved_at=T - timedelta(minutes=5)),
    )


def _gis():
    return GisQueryResult(
        coordinate=COORD, backend="offline",
        source_status=SourceStatus(tier=DataTier.REFERENCE, source="static-gis:offline"),
        eez=EezResult(inside=True, zones=("Indian Exclusive Economic Zone",)),
        coastline_distance_m=87000.0, depth_m=-560.0, on_land=False,
    )


def test_normalises_agent_observations_into_fabric_records() -> None:
    weather = _agent_result("weather", [_obs("wind_speed", 6.0, "m/s")])
    ocean = _agent_result("oceanographic", [_obs("wave_height", 1.8, "m")])
    fabric = build_fabric(
        query_coordinate=COORD, query_time=T, weather=weather, ocean=ocean, now=T
    )
    assert set(fabric.variables()) >= {"wind_speed", "wave_height"}
    wh = fabric.for_variable("wave_height")[0]
    assert wh.value == pytest.approx(1.8)
    assert wh.observation.unit == "m"
    assert wh.source == "open-meteo-marine"
    assert wh.source_status.tier is DataTier.LIVE
    assert wh.observation.retrieved_at is not None
    assert wh.validity is ValidityState.VALID


def test_gis_scalars_become_reference_records() -> None:
    fabric = build_fabric(query_coordinate=COORD, query_time=T, gis=_gis(), now=T)
    depth = fabric.for_variable("water_depth")[0]
    assert depth.value == pytest.approx(-560.0)
    assert depth.observation.signal_kind is SignalKind.REFERENCE
    assert depth.source_status.tier is DataTier.REFERENCE
    assert "coastline_distance" in fabric.variables()


def test_missing_agent_is_recorded_as_warning_not_fabricated() -> None:
    missing = AgentResult(
        kind="oceanographic", coordinate=COORD, query_time=T, observations=(),
        source_status=SourceStatus(tier=DataTier.MISSING, source="none"),
    )
    fabric = build_fabric(query_coordinate=COORD, query_time=T, ocean=missing, now=T)
    assert fabric.records == () or all(r.variable != "wave_height" for r in fabric.records)
    assert any("ocean" in w for w in fabric.warnings)


def test_stale_observation_is_flagged_by_the_gate() -> None:
    weather = _agent_result("weather", [_obs("wind_speed", 6.0, "m/s", valid=False)])
    fabric = build_fabric(query_coordinate=COORD, query_time=T, weather=weather, now=T)
    rec = fabric.for_variable("wind_speed")[0]
    assert rec.validity in (ValidityState.STALE, ValidityState.INVALID)
    assert rec.validity is not ValidityState.VALID


def test_multiple_candidate_observations_for_one_variable_are_all_kept() -> None:
    a = _agent_result("oceanographic", [_obs("wave_height", 1.5, "m")], source="open-meteo-marine")
    b = AgentResult(
        kind="oceanographic-b", coordinate=COORD, query_time=T,
        observations=(_obs("wave_height", 2.4, "m"),),
        source_status=SourceStatus(tier=DataTier.CACHE, source="redis", cached_at=T),
    )
    fabric = build_fabric(query_coordinate=COORD, query_time=T, ocean=a, now=T)
    extra = build_fabric(query_coordinate=COORD, query_time=T, ocean=b, now=T)
    combined = tuple(fabric.records) + tuple(extra.records)
    wh = [r for r in combined if r.variable == "wave_height"]
    assert len(wh) == 2
    assert {round(r.value, 1) for r in wh} == {1.5, 2.4}
    assert {r.source_status.tier for r in wh} == {DataTier.LIVE, DataTier.CACHE}


def test_reference_ids_carried_without_merging() -> None:
    from app.models.reference import ReferenceArtifact, ReferenceKind

    pfz = ReferenceArtifact(
        reference_id="pfz-0", kind=ReferenceKind.PFZ, title="PFZ", source="INCOIS",
        disclaimer="not ORCA-derived",
    )
    fabric = build_fabric(
        query_coordinate=COORD, query_time=T, gis=_gis(), references=(pfz,), now=T
    )
    assert "pfz-0" in fabric.reference_ids
    # the PFZ is not an observation
    assert all(r.variable != "pfz" for r in fabric.records)
    assert "pfz_advisory" not in fabric.variables()


# ---- Phase 9: environmental AgentResult folds in like weather / ocean ----
def _chl_obs(days_old: int):
    return MarineObservation(
        variable="chlorophyll_a", value=0.36, unit="mg m-3", coordinate=COORD,
        observed_at=T - timedelta(days=days_old), retrieved_at=T,
        source="noaa-coastwatch-erddap:noaacwNPPVIIRSchlaDaily",
        source_tier=SourceTier.MODEL, signal_kind=SignalKind.MODEL_DERIVED,
    )


def test_environment_agent_result_is_folded_into_the_fabric() -> None:
    weather = _agent_result("weather", [_obs("wind_speed", 6.0, "m/s")])
    ocean = _agent_result("oceanographic", [
        _obs("wave_height", 1.8, "m"),
        _obs("sea_surface_temperature", 29.3, "°C"),
    ])
    env = _agent_result("environmental", [_chl_obs(1)],
                        source="noaa-coastwatch-erddap:noaacwNPPVIIRSchlaDaily")
    fabric = build_fabric(
        query_coordinate=COORD, query_time=T,
        weather=weather, ocean=ocean, environment=env, now=T,
    )
    by_var = {r.variable: r for r in fabric.records}
    assert "sea_surface_temperature" in by_var
    assert by_var["sea_surface_temperature"].validity is ValidityState.VALID
    assert "chlorophyll_a" in by_var
    chl = by_var["chlorophyll_a"]
    assert chl.observation.value == pytest.approx(0.36)
    assert chl.observation.unit == "mg m-3"
    assert chl.source_status.tier is DataTier.LIVE
    assert chl.validity is ValidityState.VALID          # 1 day old, fresh window is 48 h


def test_missing_environment_agent_does_not_crash_or_add_records() -> None:
    weather = _agent_result("weather", [_obs("wind_speed", 6.0, "m/s")])
    fabric = build_fabric(
        query_coordinate=COORD, query_time=T, weather=weather, environment=None, now=T
    )
    assert "chlorophyll_a" not in fabric.variables()


def test_environment_agent_with_no_data_is_a_warning_not_a_fabricated_value() -> None:
    weather = _agent_result("weather", [_obs("wind_speed", 6.0, "m/s")])
    env = AgentResult(
        kind="environmental", coordinate=COORD, query_time=T, observations=(),
        source_status=SourceStatus(tier=DataTier.MISSING, source="none", note="cloud gap"),
    )
    fabric = build_fabric(
        query_coordinate=COORD, query_time=T, weather=weather, environment=env, now=T
    )
    assert "chlorophyll_a" not in fabric.variables()
    assert any("environment" in w for w in fabric.warnings)


def test_stale_chlorophyll_composite_is_flagged_stale_by_the_gate() -> None:
    env = _agent_result("environmental", [_chl_obs(6)])   # 6 days old
    fabric = build_fabric(
        query_coordinate=COORD, query_time=T, environment=env, now=T
    )
    chl = next(r for r in fabric.records if r.variable == "chlorophyll_a")
    assert chl.validity is ValidityState.STALE


# ---- Phase 10A: tide / sea level rides the SAME ocean AgentResult as wave ----
def test_tide_observation_from_ocean_agent_is_folded_into_the_fabric() -> None:
    ocean = _agent_result("oceanographic", [
        _obs("wave_height", 1.8, "m"),
        _obs("sea_level_height", 0.42, "m"),
    ])
    fabric = build_fabric(query_coordinate=COORD, query_time=T, ocean=ocean, now=T)
    tide = fabric.for_variable("sea_level_height")[0]
    assert tide.value == pytest.approx(0.42)
    assert tide.observation.unit == "m"
    assert tide.source == "open-meteo-marine"
    assert tide.validity is ValidityState.VALID


def test_stale_tide_forecast_is_flagged_by_the_gate_not_treated_as_no_tide() -> None:
    ocean = _agent_result("oceanographic", [_obs("sea_level_height", 0.42, "m", valid=False)])
    fabric = build_fabric(query_coordinate=COORD, query_time=T, ocean=ocean, now=T)
    tide = fabric.for_variable("sea_level_height")[0]
    assert tide.validity is not ValidityState.VALID
    # still carries the real value - a stale/invalid verdict is not "no tide"
    assert tide.value == pytest.approx(0.42)


def test_missing_ocean_agent_leaves_no_tide_record_not_a_fabricated_zero() -> None:
    missing = AgentResult(
        kind="oceanographic", coordinate=COORD, query_time=T, observations=(),
        source_status=SourceStatus(tier=DataTier.MISSING, source="none"),
    )
    fabric = build_fabric(query_coordinate=COORD, query_time=T, ocean=missing, now=T)
    assert "sea_level_height" not in fabric.variables()
