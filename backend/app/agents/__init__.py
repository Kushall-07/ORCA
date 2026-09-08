"""Specialist agents.

Data / spatial agents (Phase 4):
  * :class:`app.agents.weather.WeatherAgent`
  * :class:`app.agents.oceanographic.OceanographicAgent`
  * :class:`app.agents.gis_geofencing.GisGeofencingAgent`

Reasoning agents (Phase 5):
  * :class:`app.agents.query_understanding.QueryUnderstandingAgent`
  * :class:`app.agents.evidence_explanation.ExplanationAgent`
  * :class:`app.agents.route.RouteAgent`

risk_suitability.py stays a placeholder (its engines are non-agent deterministic
modules under app/risk and app/suitability).
"""

from app.agents.base import AgentResult
from app.agents.gis_geofencing import GisGeofencingAgent
from app.agents.oceanographic import OceanographicAgent
from app.agents.weather import WeatherAgent

__all__ = ["WeatherAgent", "OceanographicAgent", "GisGeofencingAgent", "AgentResult"]
