"""Authority operational-intelligence aggregation (Milestone 5).

This package is a presentation/aggregation layer ONLY. It never computes risk,
safety, or a decision itself - it calls the existing, frozen
``OrcaPipeline`` (query understanding -> weather/ocean/GIS agents ->
``RiskEngine`` -> ``SafetyGuard`` -> ``DecisionEngine``) once per coastal
location and projects the resulting ``QueryResponse`` objects into a compact
operational summary for the Authority dashboard.

No second risk engine, safety engine, or decision engine is introduced here.
"""
