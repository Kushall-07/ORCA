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
from app.models.environmental import EnvironmentalObservation, ReferenceSeriesPoint
from app.environmental.comparison import EnvironmentalComparisonEngine
from app.environmental.engine import EnvironmentalProductivityEngine
from app.environmental.evidence import EnvironmentalEvidenceEngine
from app.environmental.neighbourhood import EnvironmentalNeighbourhoodEngine
from app.environmental.stability import EnvironmentalStabilityEngine
from app.agents.historical_environment import HistoricalReference
from app.services.oceancolor import ChlorophyllNeighbourhood, NeighbourhoodPixelRaw
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


def _synth_series(median: float, count: int, span_days: int, window_days: int):
    """Deterministic (value, observed_at) points evenly spread across a window.
    Values fan symmetrically around ``median`` so quartiles are predictable."""
    if count <= 0:
        return ()
    pts: list[ReferenceSeriesPoint] = []
    step = span_days / max(1, count - 1) if count > 1 else 0
    for i in range(count):
        days_ago = window_days - 2 - i * step
        offset = ((i % 5) - 2) * 0.1 * (1.0 if median < 5 else 1.0)
        value = round(median + offset, 3)
        pts.append(
            ReferenceSeriesPoint(
                value=value,
                observed_at=(NOW - timedelta(days=days_ago)).isoformat(),
            )
        )
    return tuple(pts)


class FakeHistoricalEnvironmentalAgent:
    """Deterministic reference-fetch stand-in for the graph tests.

    ``sst`` / ``chl`` None -> that variable's reference is absent (honest
    insufficient history). ``fail=True`` raises inside fetch_reference to prove
    the comparison node still does not break the graph.

    ``sst_series`` / ``chl_series`` (tuples of ``ReferenceSeriesPoint``) let a
    test hand the Step 6 stability node an exact accepted series; when omitted a
    deterministic spread of ``sst_points`` / ``chl_points`` points is synthesised.
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
        sst_points: int = 14,
        chl_points: int = 8,
        series_span_days: int = 26,
        sst_series: tuple | None = None,
        chl_series: tuple | None = None,
    ) -> None:
        self._sst = sst
        self._chl = chl
        self._sst_validity = sst_validity
        self._chl_validity = chl_validity
        self._window = window_label
        self._fail = fail
        self._sst_points = sst_points
        self._chl_points = chl_points
        self._span = series_span_days
        self._sst_series = sst_series
        self._chl_series = chl_series

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
        if self._sst_series is not None:
            sst_series = tuple(self._sst_series)
        elif self._sst is not None:
            sst_series = _synth_series(
                self._sst, self._sst_points, self._span, window_days
            )
        else:
            sst_series = ()

        if self._chl_series is not None:
            chl_series = tuple(self._chl_series)
        elif self._chl is not None:
            chl_series = _synth_series(
                self._chl, self._chl_points, self._span, window_days
            )
        else:
            chl_series = ()

        return HistoricalReference(
            sst=sst_obs, chlorophyll_a=chl_obs, reference_window=self._window,
            sst_series=sst_series, chlorophyll_series=chl_series,
            window_days=window_days,
        )


class FakeNeighbourhoodProbe:
    """Deterministic chlorophyll-a pixel-neighbourhood box-fetch stand-in for the
    graph tests. ``fail=True`` raises so the node still degrades non-blocking.
    ``n_valid`` / ``cells_total`` control how many nearby pixels carried a value
    (the rest are left missing, never zero-filled). Never enters the fabric /
    risk / safety. ``calls`` counts invocations so a test can assert the HTTP
    budget."""

    def __init__(
        self, *, median: float = 1.1, n_valid: int = 19, cells_total: int = 25,
        fail: bool = False,
    ) -> None:
        self.median = median
        self.n_valid = n_valid
        self.cells_total = cells_total
        self.fail = fail
        self.calls = 0

    async def __call__(
        self, latitude, longitude, when, *, half_width_deg, settings, client=None
    ) -> ChlorophyllNeighbourhood:
        self.calls += 1
        if self.fail:
            raise RuntimeError("neighbourhood box fetch blew up")
        composite_at = when if getattr(when, "tzinfo", None) else when.replace(
            tzinfo=timezone.utc
        )
        pixels = tuple(
            NeighbourhoodPixelRaw(
                value=round(self.median + ((i % 5) - 2) * 0.1, 3),
                latitude=latitude + (i % 5 - 2) * 0.03,
                longitude=longitude + (i // 5 - 2) * 0.03,
                observed_at=composite_at,
                distance_m=round(1500.0 + i * 400.0, 1),
            )
            for i in range(self.n_valid)
        )
        return ChlorophyllNeighbourhood(
            pixels=pixels,
            cells_total=max(self.cells_total, self.n_valid),
            composite_at=composite_at,
            box=f"+/-{half_width_deg:.2f} deg around {latitude:.3f}, {longitude:.3f}",
            half_width_deg=half_width_deg,
            dataset="noaacwNPPVIIRSchlaDaily",
            source="noaa-coastwatch-erddap:noaacwNPPVIIRSchlaDaily",
        )


def make_pipeline(
    *,
    weather=None,
    ocean=None,
    gis=None,
    environment=None,
    productivity_engine=_UNSET,
    comparison_engine=_UNSET,
    evidence_engine=_UNSET,
    stability_engine=_UNSET,
    neighbourhood_engine=_UNSET,
    neighbourhood_probe=None,
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
        evidence_engine=(
            EnvironmentalEvidenceEngine()
            if evidence_engine is _UNSET
            else evidence_engine
        ),
        stability_engine=(
            EnvironmentalStabilityEngine()
            if stability_engine is _UNSET
            else stability_engine
        ),
        neighbourhood_engine=(
            EnvironmentalNeighbourhoodEngine()
            if neighbourhood_engine is _UNSET
            else neighbourhood_engine
        ),
        neighbourhood_probe=neighbourhood_probe,
        historical_environment_agent=historical_environment_agent,
    )
    return OrcaPipeline(deps)
