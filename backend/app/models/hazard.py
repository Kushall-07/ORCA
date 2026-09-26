"""GDACS global tropical-cyclone reference models - Phase 11.

A REFERENCE hazard signal only: describes active tropical-cyclone systems
within a bounded radius of a coordinate, sourced from GDACS (the Global
Disaster Alert and Coordination System, EC-JRC/UN OCHA), which - unlike NOAA
NHC (Atlantic/East Pacific only) - actually covers the Bay of Bengal and
Arabian Sea. In this phase it feeds only the deterministic Alert Engine
(app.alerts.engine); it never enters the Marine Data Fabric, fusion,
arbitration, RiskEngineInput, the Safety Guard or the Decision Engine. Every
alert built from it is worded as a reference/context signal, not a certified
forecast - see app.alerts.engine.generate_alerts.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class CycloneAlertLevel(str, Enum):
    GREEN = "green"
    ORANGE = "orange"
    RED = "red"


class CycloneEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    name: str
    alert_level: CycloneAlertLevel
    latitude: float
    longitude: float
    distance_km: float
    from_date: str | None = None
    source: str = "GDACS"


class CycloneHazardResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    events: tuple[CycloneEvent, ...] = ()   # nearest first
    checked_radius_km: float
    source: str = "GDACS"
    # False only when the feed itself could not be reached/parsed - distinct
    # from "reachable, but nothing active within the radius" (available=True,
    # events=()). Never a reason to fail the query either way.
    available: bool = True
    note: str | None = None

    @property
    def nearest(self) -> CycloneEvent | None:
        return self.events[0] if self.events else None
