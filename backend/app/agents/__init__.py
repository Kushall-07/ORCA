"""Specialist agents.

Phase 4 implements the three live/spatial data agents:
  * :class:`app.agents.weather.WeatherAgent`
  * :class:`app.agents.oceanographic.OceanographicAgent`
  * :class:`app.agents.gis_geofencing.GisGeofencingAgent`

query_understanding.py, risk_suitability.py, route.py and evidence_explanation.py
remain placeholders (Phase 5+).
"""

from app.agents.base import AgentResult
from app.agents.gis_geofencing import GisGeofencingAgent
from app.agents.oceanographic import OceanographicAgent
from app.agents.weather import WeatherAgent

__all__ = ["WeatherAgent", "OceanographicAgent", "GisGeofencingAgent", "AgentResult"]
