"""Marine Researcher / Oceanographer analytical support.

Deterministic, LLM-free, I/O-free capability validation for a RESEARCH_QUERY
(see app.models.query.QueryIntent.RESEARCH_QUERY). This package never fetches
data itself - it only classifies which variables a research request needs and
whether ORCA's already-configured data sources can serve them, so the
orchestration layer can reuse the existing environmental engines for the
supported part and render an honest limitation for the rest.
"""
