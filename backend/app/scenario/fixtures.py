"""Controlled, clearly-labelled DEMO / TEST fixtures for the Scenario Engine.

Nothing here touches the live system. ``build_default_deps`` (production) still
wires the real Open-Meteo / GIS agents. These fakes exist only so that demo and
regression scenarios are deterministic and offline. Every synthetic observation
is tagged ``DEMO`` intent via its scenario id and the source string
``scenario-fixture:*`` so it can never be mistaken for a live reading.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.agents.base import AgentResult
from app.agents.evidence_explanation import ExplanationAgent
from app.agents.query_understanding import QueryUnderstandingAgent
from app.agents.route import RouteAgent
from app.core.config import get_settings
from app.environmental.comparison import EnvironmentalComparisonEngine
from app.environmental.engine import EnvironmentalProductivityEngine
from app.agents.historical_environment import HistoricalReference
from app.models.common import Coordinate, SignalKind, SourceTier
from app.models.environmental import EnvironmentalObservation
from app.models.fabric import DataTier, SourceStatus
from app.models.geo import Geofence, GeofenceSeverity, GeofenceType, LayerAuthority
from app.models.gis_agent import EezResult, GisQueryResult, LayerKind, ProtectedAreaHit
from app.models.observations import MarineObservation
from app.models.reference import ReferenceArtifact, ReferenceKind
from app.orchestration.deps import OrcaDeps
from app.orchestration.pipeline import OrcaPipeline
from app.reasoning.arbitration import HierarchyArbitrator
from app.risk.engine import RiskEngine
from app.session.store import InMemorySessionStore
from app.suitability.engine import SuitabilityEngine

# A fixed clock so scenario runs are reproducible.
SCENARIO_NOW = datetime(2026, 9, 7, 7, 0, tzinfo=timezone.utc)
MANGALORE = Coordinate(latitude=12.87, longitude=74.84)

_PFZ_REFERENCE = ReferenceArtifact(
    reference_id="pfz-scenario",
    kind=ReferenceKind.PFZ,
    title="INCOIS Potential Fishing Zone (PFZ) Advisory",
    source="Indian National Centre for Ocean Information Services (INCOIS)",
    issued_at="7 September 2026",
    valid_until="8 September 2026",
    media_type="image/jpeg",
    machine_readable=False,
    disclaimer=(
        "Official INCOIS PFZ advisory reference snapshot. This is NOT an "
        "ORCA-derived fishing-suitability prediction and is never merged into "
        "ORCA's computed suitability score."
    ),
)


def _obs(
    variable: str,
    value: float,
    unit: str,
    source: str,
    *,
    when: datetime = SCENARIO_NOW,
    tier: SourceTier = SourceTier.MODEL,
    signal: SignalKind = SignalKind.MODEL_DERIVED,
) -> MarineObservation:
    return MarineObservation(
        variable=variable,
        value=value,
        unit=unit,
        coordinate=MANGALORE,
        valid_from=when - timedelta(minutes=20),
        valid_until=when + timedelta(minutes=40),
        retrieved_at=when - timedelta(minutes=5),
        source=source,
        source_tier=tier,
        signal_kind=signal,
    )


class ScenarioWeatherAgent:
    """Deterministic stand-in for the live weather agent."""

    def __init__(self, observations=None, *, tier: DataTier = DataTier.LIVE, missing: bool = False):
        self._obs = observations
        self._tier = tier
        self._missing = missing

    async def fetch(self, coordinate, when, **_):
        if self._missing:
            return AgentResult(
                kind="weather", coordinate=coordinate, query_time=when, observations=(),
                source_status=SourceStatus(tier=DataTier.MISSING, source="none"),
                errors=("scenario: live weather unavailable",),
            )
        default = (
            _obs("wind_speed", 5.0, "m/s", "open-meteo-forecast", when=when),
            _obs("weather_code", 2.0, "wmo", "open-meteo-forecast", when=when),
            _obs("mean_sea_level_pressure", 1010.0, "hPa", "open-meteo-forecast", when=when),
        )
        return AgentResult(
            kind="weather", coordinate=coordinate, query_time=when,
            observations=tuple(self._obs) if self._obs is not None else default,
            source_status=SourceStatus(tier=self._tier, source="open-meteo-forecast", retrieved_at=when),
        )


class ScenarioOceanAgent:
    def __init__(self, observations=None, *, tier: DataTier = DataTier.LIVE, missing: bool = False):
        self._obs = observations
        self._tier = tier
        self._missing = missing

    async def fetch(self, coordinate, when, **_):
        if self._missing:
            return AgentResult(
                kind="oceanographic", coordinate=coordinate, query_time=when, observations=(),
                source_status=SourceStatus(tier=DataTier.MISSING, source="none"),
                errors=("scenario: live marine unavailable",),
            )
        default = (_obs("wave_height", 1.0, "m", "open-meteo-marine", when=when),)
        return AgentResult(
            kind="oceanographic", coordinate=coordinate, query_time=when,
            observations=tuple(self._obs) if self._obs is not None else default,
            source_status=SourceStatus(tier=self._tier, source="open-meteo-marine", retrieved_at=when),
        )


class ScenarioEnvironmentalAgent:
    """Deterministic ocean-colour (chlorophyll-a) stand-in - Phase 9 Step 3.

    ``chlorophyll`` None -> a MISSING result (non-blocking); the productivity
    engine then honestly reports ``unknown``. Never enters the safety chain.
    """

    def __init__(self, chlorophyll: float | None = 0.28, *, days_old: int = 1,
                 tier: DataTier = DataTier.LIVE) -> None:
        self._value = chlorophyll
        self._days_old = days_old
        self._tier = tier

    async def fetch(self, coordinate, when, **_):
        if self._value is None:
            from app.agents.base import missing_result

            return missing_result("environmental", coordinate, when,
                                  "scenario: no chlorophyll pixel")
        chl = MarineObservation(
            variable="chlorophyll_a", value=float(self._value), unit="mg m-3",
            coordinate=coordinate,
            observed_at=when - timedelta(days=self._days_old),
            retrieved_at=when,
            source="orca-demo-environmental:scenario",
            source_tier=SourceTier.MODEL, signal_kind=SignalKind.MODEL_DERIVED,
        )
        return AgentResult(
            kind="environmental", coordinate=coordinate, query_time=when,
            observations=(chl,),
            source_status=SourceStatus(
                tier=self._tier, source="orca-demo-environmental:scenario",
                retrieved_at=when,
            ),
        )


class ScenarioHistoricalEnvironmentalAgent:
    """Deterministic reference-fetch stand-in - Phase 9 Step 4. Never enters the
    Marine Data Fabric; feeds only the comparison engine -> provenance /
    explanation. ``sst`` / ``chl`` None -> honest insufficient history."""

    def __init__(self, *, sst: float | None = 27.9, chl: float | None = 1.1) -> None:
        self._sst = sst
        self._chl = chl

    async def fetch_reference(self, coordinate, *, current_time, window_days):
        window = f"ORCA-computed reference over the {window_days} days before {current_time.date().isoformat()}"
        sst_obs = None
        if self._sst is not None:
            sst_obs = EnvironmentalObservation(
                variable="sea_surface_temperature", value=float(self._sst), unit="°C",
                validity="VALID", data_tier="REFERENCE",
                source="open-meteo-marine (median over 120 model values, 30-day history)",
                source_tier=3,
                observed_at=(current_time - timedelta(days=15)).isoformat(),
                role="reference",
            )
        chl_obs = None
        if self._chl is not None:
            chl_obs = EnvironmentalObservation(
                variable="chlorophyll_a", value=float(self._chl), unit="mg m-3",
                validity="VALID", data_tier="REFERENCE",
                source="noaa-coastwatch-erddap (median of 6 cloud-free composites, 30-day history)",
                source_tier=3,
                observed_at=(current_time - timedelta(days=14)).isoformat(),
                distance_m=1800.0, role="reference",
            )
        return HistoricalReference(sst=sst_obs, chlorophyll_a=chl_obs, reference_window=window)


class ScenarioGisAgent:
    def __init__(self, *, inside_hard=False, hard_ids=(), protected_areas=(), depth_m=-540.0,
                 on_land=False, fail=False):
        self._inside_hard = inside_hard
        self._hard_ids = tuple(hard_ids)
        self._pas = tuple(protected_areas)
        self._depth = depth_m
        self._on_land = on_land
        self._fail = fail

    async def query(self, coordinate):
        if self._fail:
            raise RuntimeError("scenario: spatial backend unavailable")
        return GisQueryResult(
            coordinate=coordinate, backend="offline",
            source_status=SourceStatus(tier=DataTier.REFERENCE, source="static-gis:offline"),
            eez=EezResult(inside=True, zones=("Indian Exclusive Economic Zone",)),
            coastline_distance_m=42000.0, depth_m=self._depth, on_land=self._on_land,
            protected_areas=self._pas,
            inside_hard_geofence=self._inside_hard, hard_geofence_ids=self._hard_ids,
        )


def _protected(name: str, *, inside: bool = False) -> ProtectedAreaHit:
    return ProtectedAreaHit(
        wdpa_id=f"DEMO-{abs(hash(name)) % 100000}", name=name,
        designation="Marine Protected Area", inside=inside,
        distance_m=0.0 if inside else 2200.0, layer_kind=LayerKind.REFERENCE,
        source="scenario-fixture:wdpa-demo",
    )


def _hard_zone(fence_id: str, wkt: str) -> Geofence:
    return Geofence(
        id=fence_id, name=f"scenario hard exclusion {fence_id}",
        geofence_type=GeofenceType.EXCLUSION, severity=GeofenceSeverity.HARD,
        authority=LayerAuthority.DEMO, source="scenario-fixture:geofence",
        geometry_wkt=wkt,
    )


# --- fixture registry -------------------------------------------------------
# Each entry returns kwargs for ``make_scenario_pipeline``.

def _thunderstorm_obs():
    return (
        _obs("wind_speed", 16.0, "m/s", "open-meteo-forecast"),
        _obs("weather_code", 96.0, "wmo", "open-meteo-forecast"),
        _obs("mean_sea_level_pressure", 1004.0, "hPa", "open-meteo-forecast"),
    )


def _cyclone_obs():
    return (
        _obs("wind_speed", 32.0, "m/s", "open-meteo-forecast"),
        _obs("weather_code", 99.0, "wmo", "open-meteo-forecast"),
        _obs("mean_sea_level_pressure", 946.0, "hPa", "open-meteo-forecast"),
    )


_FIXTURES = {
    "nominal": lambda: dict(),
    "pfz": lambda: dict(references=[_PFZ_REFERENCE]),
    "pfz_conflict": lambda: dict(
        references=[_PFZ_REFERENCE],
        ocean=ScenarioOceanAgent(observations=(
            _obs("wave_height", 3.4, "m", "open-meteo-marine"),
        )),
        weather=ScenarioWeatherAgent(observations=(
            _obs("wind_speed", 13.5, "m/s", "open-meteo-forecast"),
            _obs("weather_code", 3.0, "wmo", "open-meteo-forecast"),
            _obs("mean_sea_level_pressure", 1007.0, "hPa", "open-meteo-forecast"),
        )),
    ),
    "route_clear": lambda: dict(),
    # A hard wall that sits on top of Kochi (~9.97, 76.24).
    "route_dest_blocked": lambda: dict(hard_geofences=[
        _hard_zone("kochi-box", "POLYGON((76.0 9.7, 76.5 9.7, 76.5 10.2, 76.0 10.2, 76.0 9.7))"),
    ]),
    # A mid-corridor exclusion box astride the direct Mangalore->Kochi line,
    # with open sea to its south so a real detour exists.
    "route_around": lambda: dict(hard_geofences=[
        _hard_zone("mid-box", "POLYGON((75.15 10.60, 75.70 10.60, 75.70 12.20, 75.15 12.20, 75.15 10.60))"),
    ]),
    # A full-height wall spanning the whole padded grid -> no navigable path.
    "route_no_path": lambda: dict(hard_geofences=[
        _hard_zone("cordon", "POLYGON((75.30 8.0, 75.55 8.0, 75.55 14.0, 75.30 14.0, 75.30 8.0))"),
    ]),
    "missing_data": lambda: dict(
        weather=ScenarioWeatherAgent(missing=True),
        ocean=ScenarioOceanAgent(missing=True),
    ),
    "thunderstorm": lambda: dict(
        weather=ScenarioWeatherAgent(observations=_thunderstorm_obs()),
        ocean=ScenarioOceanAgent(observations=(_obs("wave_height", 2.6, "m", "open-meteo-marine"),)),
    ),
    "cyclone": lambda: dict(
        weather=ScenarioWeatherAgent(observations=_cyclone_obs()),
        ocean=ScenarioOceanAgent(observations=(_obs("wave_height", 6.4, "m", "open-meteo-marine"),)),
    ),
    "source_conflict": lambda: dict(
        weather=ScenarioWeatherAgent(observations=(
            _obs("wind_speed", 6.0, "m/s", "model-a"),
            _obs("weather_code", 3.0, "wmo", "model-a"),
        )),
        ocean=ScenarioOceanAgent(observations=(
            _obs("wave_height", 1.2, "m", "model-a"),
            _obs("wave_height", 4.3, "m", "model-b"),
        )),
    ),
    "coastal_protected": lambda: dict(
        gis=ScenarioGisAgent(protected_areas=(
            _protected("Gulf of Mannar Marine National Park", inside=False),
            _protected("Netravati Estuary Reserve", inside=False),
        )),
        weather=ScenarioWeatherAgent(observations=(
            _obs("wind_speed", 14.0, "m/s", "open-meteo-forecast"),
            _obs("weather_code", 3.0, "wmo", "open-meteo-forecast"),
            _obs("mean_sea_level_pressure", 1006.0, "hPa", "open-meteo-forecast"),
        )),
        ocean=ScenarioOceanAgent(observations=(_obs("wave_height", 2.3, "m", "open-meteo-marine"),)),
    ),
    "disaster": lambda: dict(
        weather=ScenarioWeatherAgent(observations=_thunderstorm_obs()),
        ocean=ScenarioOceanAgent(observations=(_obs("wave_height", 3.8, "m", "open-meteo-marine"),)),
    ),
    "injection": lambda: dict(
        weather=ScenarioWeatherAgent(observations=_cyclone_obs()),
        ocean=ScenarioOceanAgent(observations=(_obs("wave_height", 6.5, "m", "open-meteo-marine"),)),
        hard_geofences=[
            _hard_zone("restricted", "POLYGON((75.30 8.0, 75.45 8.0, 75.45 14.0, 75.30 14.0, 75.30 8.0))"),
        ],
    ),
    # Phase 9 Step 3 - researcher environmental-context fixtures. SST rides the
    # ocean agent; chlorophyll-a comes from the ocean-colour agent. Neither
    # feeds risk / safety / decision / routing.
    "researcher_env": lambda: dict(
        ocean=ScenarioOceanAgent(observations=(
            _obs("wave_height", 1.2, "m", "open-meteo-marine"),
            _obs("sea_surface_temperature", 28.6, "°C", "open-meteo-marine"),
        )),
        environment=ScenarioEnvironmentalAgent(1.8),  # -> moderate class
    ),
    "researcher_env_missing": lambda: dict(
        ocean=ScenarioOceanAgent(observations=(
            _obs("wave_height", 1.2, "m", "open-meteo-marine"),
            _obs("sea_surface_temperature", 28.6, "°C", "open-meteo-marine"),
        )),
        environment=ScenarioEnvironmentalAgent(None),  # chlorophyll unavailable
    ),
    # Phase 9 Step 4 - researcher temporal comparison fixtures. The historical
    # reference is fetched LOCALLY by the comparison node; it never enters the
    # fabric / fusion / arbitration / risk.
    "researcher_env_compare": lambda: dict(
        ocean=ScenarioOceanAgent(observations=(
            _obs("wave_height", 1.2, "m", "open-meteo-marine"),
            _obs("sea_surface_temperature", 29.1, "°C", "open-meteo-marine"),
        )),
        environment=ScenarioEnvironmentalAgent(1.8),
        historical_environment_agent=ScenarioHistoricalEnvironmentalAgent(sst=27.9, chl=1.1),
    ),
    "researcher_env_compare_nohist": lambda: dict(
        ocean=ScenarioOceanAgent(observations=(
            _obs("wave_height", 1.2, "m", "open-meteo-marine"),
            _obs("sea_surface_temperature", 29.1, "°C", "open-meteo-marine"),
        )),
        environment=ScenarioEnvironmentalAgent(1.8),
        historical_environment_agent=ScenarioHistoricalEnvironmentalAgent(sst=None, chl=None),
    ),
}


def fixture_names() -> tuple[str, ...]:
    return tuple(_FIXTURES)


def make_scenario_pipeline(
    *,
    weather=None,
    ocean=None,
    gis=None,
    environment=None,
    historical_environment_agent=None,
    hard_geofences=(),
    references=(),
) -> OrcaPipeline:
    """A real :class:`OrcaPipeline` wired with deterministic fixture agents.

    The graph, reasoning, risk, safety, decision, routing, provenance and
    explanation code are all the production ones - only the *data* agents are
    swapped for offline fakes.
    """
    settings = get_settings()
    deps = OrcaDeps(
        settings=settings,
        qu_agent=QueryUnderstandingAgent(None),          # deterministic rule parser
        weather_agent=weather or ScenarioWeatherAgent(),
        ocean_agent=ocean or ScenarioOceanAgent(),
        gis_agent=gis or ScenarioGisAgent(),
        explanation_agent=ExplanationAgent(None),         # deterministic template
        route_agent=RouteAgent(settings),
        risk_engine=RiskEngine(),
        suitability_engine=SuitabilityEngine(),
        arbitrator=HierarchyArbitrator(),
        session_store=InMemorySessionStore(settings.session_max_turns),
        references=tuple(references),
        hard_geofences=tuple(hard_geofences),
        environment_agent=environment,
        productivity_engine=EnvironmentalProductivityEngine(),
        comparison_engine=EnvironmentalComparisonEngine(),
        historical_environment_agent=historical_environment_agent,
    )
    return OrcaPipeline(deps)


def pipeline_for_fixture(name: str) -> OrcaPipeline:
    if name not in _FIXTURES:
        raise KeyError(f"unknown scenario fixture: {name!r}")
    return make_scenario_pipeline(**_FIXTURES[name]())
