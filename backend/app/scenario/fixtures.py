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
from app.models.common import Coordinate, SignalKind, SourceTier
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
}


def fixture_names() -> tuple[str, ...]:
    return tuple(_FIXTURES)


def make_scenario_pipeline(
    *,
    weather=None,
    ocean=None,
    gis=None,
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
    )
    return OrcaPipeline(deps)


def pipeline_for_fixture(name: str) -> OrcaPipeline:
    if name not in _FIXTURES:
        raise KeyError(f"unknown scenario fixture: {name!r}")
    return make_scenario_pipeline(**_FIXTURES[name]())
