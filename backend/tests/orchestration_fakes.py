"""Fakes + builders for Phase 5 orchestration tests. No network, no real LLM."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.agents.base import AgentResult
from app.agents.evidence_explanation import ExplanationAgent
from app.agents.query_understanding import QueryUnderstandingAgent
from app.agents.route import RouteAgent
from app.core.config import get_settings
from app.models.common import Coordinate, SignalKind, SourceTier
from app.models.fabric import DataTier, SourceStatus
from app.models.gis_agent import EezResult, GisQueryResult, LayerKind, ProtectedAreaHit
from app.models.geo import Geofence, GeofenceSeverity, GeofenceType, LayerAuthority
from app.models.observations import MarineObservation
from app.models.environmental import EnvironmentalObservation
from app.environmental.comparison import EnvironmentalComparisonEngine
from app.environmental.engine import EnvironmentalProductivityEngine
from app.agents.historical_environment import HistoricalReference
from app.orchestration.deps import OrcaDeps
from app.orchestration.pipeline import OrcaPipeline
from app.reasoning.arbitration import HierarchyArbitrator
from app.risk.engine import RiskEngine
from app.session.store import InMemorySessionStore
from app.suitability.engine import SuitabilityEngine

NOW = datetime(2026, 9, 7, 7, 0, tzinfo=timezone.utc)
MANGALORE = Coordinate(latitude=12.87, longitude=74.84)

_UNSET = object()  # make_pipeline: default -> a real deterministic productivity engine


def obs(variable: str, value: float, unit: str, source: str, *, when: datetime = NOW,
        tier: SourceTier = SourceTier.MODEL) -> MarineObservation:
    return MarineObservation(
        variable=variable, value=value, unit=unit, coordinate=MANGALORE,
        valid_from=when - timedelta(minutes=20), valid_until=when + timedelta(minutes=40),
        retrieved_at=when - timedelta(minutes=5), source=source,
        source_tier=tier, signal_kind=SignalKind.MODEL_DERIVED,
    )


class FakeWeatherAgent:
    def __init__(self, observations=None, tier: DataTier = DataTier.LIVE, missing: bool = False):
        self._obs = observations
        self._tier = tier
        self._missing = missing

    async def fetch(self, coordinate, when, **_):
        if self._missing:
            return AgentResult(
                kind="weather", coordinate=coordinate, query_time=when, observations=(),
                source_status=SourceStatus(tier=DataTier.MISSING, source="none"),
                errors=("live weather unavailable",),
            )
        default = (
            obs("wind_speed", 5.0, "m/s", "open-meteo-forecast", when=when),
            obs("weather_code", 3.0, "wmo", "open-meteo-forecast", when=when),
            obs("mean_sea_level_pressure", 1009.0, "hPa", "open-meteo-forecast", when=when),
        )
        return AgentResult(
            kind="weather", coordinate=coordinate, query_time=when,
            observations=tuple(self._obs) if self._obs is not None else default,
            source_status=SourceStatus(tier=self._tier, source="open-meteo-forecast", retrieved_at=when),
        )


class FakeOceanAgent:
    def __init__(self, observations=None, tier: DataTier = DataTier.LIVE, missing: bool = False):
        self._obs = observations
        self._tier = tier
        self._missing = missing

    async def fetch(self, coordinate, when, **_):
        if self._missing:
            return AgentResult(
                kind="oceanographic", coordinate=coordinate, query_time=when, observations=(),
                source_status=SourceStatus(tier=DataTier.MISSING, source="none"),
                errors=("live marine unavailable",),
            )
        default = (obs("wave_height", 1.1, "m", "open-meteo-marine", when=when),)
        return AgentResult(
            kind="oceanographic", coordinate=coordinate, query_time=when,
            observations=tuple(self._obs) if self._obs is not None else default,
            source_status=SourceStatus(tier=self._tier, source="open-meteo-marine", retrieved_at=when),
        )


class FakeGisAgent:
    def __init__(self, *, inside_hard=False, hard_ids=(), protected_areas=(), depth_m=-560.0,
                 fail=False, on_land=False):
        self._inside_hard = inside_hard
        self._hard_ids = tuple(hard_ids)
        self._pas = tuple(protected_areas)
        self._depth = depth_m
        self._fail = fail
        self._on_land = on_land

    async def query(self, coordinate):
        if self._fail:
            raise RuntimeError("spatial backend unavailable")
        return GisQueryResult(
            coordinate=coordinate, backend="offline",
            source_status=SourceStatus(tier=DataTier.REFERENCE, source="static-gis:offline"),
            eez=EezResult(inside=True, zones=("Indian Exclusive Economic Zone",)),
            coastline_distance_m=88000.0, depth_m=self._depth, on_land=self._on_land,
            protected_areas=self._pas,
            inside_hard_geofence=self._inside_hard, hard_geofence_ids=self._hard_ids,
        )


def hard_zone(fence_id="demo-hard", wkt=None) -> Geofence:
    return Geofence(
        id=fence_id, name="demo hard exclusion", geofence_type=GeofenceType.EXCLUSION,
        severity=GeofenceSeverity.HARD, authority=LayerAuthority.DEMO, source="test",
        geometry_wkt=wkt or "POLYGON((74.5 12.6, 74.7 12.6, 74.7 12.8, 74.5 12.8, 74.5 12.6))",
    )


def protected(name="Gulf of Mannar MNP", inside=True) -> ProtectedAreaHit:
    return ProtectedAreaHit(
        wdpa_id="DEMO-GOM", name=name, designation="Marine National Park",
        inside=inside, distance_m=0.0 if inside else 1200.0, layer_kind=LayerKind.REFERENCE,
        source="orca-demo",
    )


class FakeEnvironmentalAgent:
    """Deterministic chlorophyll-a agent for the graph tests.

    ``chlorophyll`` None -> MISSING (non-blocking). ``fail=True`` raises inside
    fetch to prove the node still does not break the graph.
    """

    def __init__(self, chlorophyll: float | None = 0.32, *, days_old: int = 1,
                 tier: DataTier = DataTier.LIVE, fail: bool = False) -> None:
        self._value = chlorophyll
        self._days_old = days_old
        self._tier = tier
        self._fail = fail

    async def fetch(self, coordinate, when, **_):
        if self._fail:
            raise RuntimeError("environmental agent blew up")
        if self._value is None:
            from app.agents.base import missing_result

            return missing_result("environmental", coordinate, when, "no chlorophyll pixel")
        obs = MarineObservation(
            variable="chlorophyll_a", value=float(self._value), unit="mg m-3",
            coordinate=coordinate,
            observed_at=when - timedelta(days=self._days_old),
            retrieved_at=when,
            source="noaa-coastwatch-erddap:noaacwNPPVIIRSchlaDaily",
            source_tier=SourceTier.MODEL, signal_kind=SignalKind.MODEL_DERIVED,
        )
        return AgentResult(
            kind="environmental", coordinate=coordinate, query_time=when,
            observations=(obs,),
            source_status=SourceStatus(
                tier=self._tier, source="noaa-coastwatch-erddap:noaacwNPPVIIRSchlaDaily",
                retrieved_at=when,
            ),
        )


class FakeHistoricalEnvironmentalAgent:
    """Deterministic reference-fetch stand-in for the graph tests.

    ``sst`` / ``chl`` None -> that variable's reference is absent (honest
    insufficient history). ``fail=True`` raises inside fetch_reference to prove
    the comparison node still does not break the graph.
    """

    def __init__(
        self,
        *,
        sst: float | None = 27.9,
        chl: float | None = 1.1,
        sst_validity: str = "VALID",
        chl_validity: str = "VALID",
        window_label: str = "ORCA-computed reference over the last 30 days",
        fail: bool = False,
    ) -> None:
        self._sst = sst
        self._chl = chl
        self._sst_validity = sst_validity
        self._chl_validity = chl_validity
        self._window = window_label
        self._fail = fail

    async def fetch_reference(self, coordinate, *, current_time, window_days):
        if self._fail:
            raise RuntimeError("historical environment agent blew up")
        sst_obs = None
        if self._sst is not None:
            sst_obs = EnvironmentalObservation(
                variable="sea_surface_temperature", value=float(self._sst), unit="°C",
                validity=self._sst_validity, data_tier="REFERENCE",
                source="open-meteo-marine (median over 120 model values, 30-day history)",
                source_tier=3,
                observed_at=(current_time - timedelta(days=15)).isoformat(),
                role="reference",
            )
        chl_obs = None
        if self._chl is not None:
            chl_obs = EnvironmentalObservation(
                variable="chlorophyll_a", value=float(self._chl), unit="mg m-3",
                validity=self._chl_validity, data_tier="REFERENCE",
                source="noaa-coastwatch-erddap (median of 6 cloud-free composites, 30-day history)",
                source_tier=3,
                observed_at=(current_time - timedelta(days=14)).isoformat(),
                distance_m=1800.0, role="reference",
            )
        return HistoricalReference(
            sst=sst_obs, chlorophyll_a=chl_obs, reference_window=self._window,
        )


def make_pipeline(
    *,
    weather=None,
    ocean=None,
    gis=None,
    environment=None,
    productivity_engine=_UNSET,
    comparison_engine=_UNSET,
    historical_environment_agent=None,
    qu_llm=None,
    explain_llm=None,
    hard_geofences=(),
    references=(),
) -> OrcaPipeline:
    settings = get_settings()
    deps = OrcaDeps(
        settings=settings,
        qu_agent=QueryUnderstandingAgent(qu_llm),
        weather_agent=weather or FakeWeatherAgent(),
        ocean_agent=ocean or FakeOceanAgent(),
        gis_agent=gis or FakeGisAgent(),
        explanation_agent=ExplanationAgent(explain_llm),
        route_agent=RouteAgent(settings),
        risk_engine=RiskEngine(),
        suitability_engine=SuitabilityEngine(),
        arbitrator=HierarchyArbitrator(),
        session_store=InMemorySessionStore(settings.session_max_turns),
        references=tuple(references),
        hard_geofences=tuple(hard_geofences),
        environment_agent=environment,
        productivity_engine=(
            EnvironmentalProductivityEngine()
            if productivity_engine is _UNSET
            else productivity_engine
        ),
        comparison_engine=(
            EnvironmentalComparisonEngine()
            if comparison_engine is _UNSET
            else comparison_engine
        ),
        historical_environment_agent=historical_environment_agent,
    )
    return OrcaPipeline(deps)
