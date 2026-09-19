"""``GET /authority/overview`` - Milestone 5 operational aggregation.

Calls the existing ``OrcaPipeline`` once per curated coastal location (never
a second risk/safety/decision engine) and projects the results into a
compact ``AuthorityOverview`` for the Authority dashboard. See
``app.authority`` for the aggregation rules.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query

from app.api.query import get_pipeline
from app.authority.aggregation import build_overview
from app.authority.locations import DEFAULT_LOCATIONS, AuthorityLocation
from app.core.logging import get_logger
from app.models.authority import AuthorityOverview

logger = get_logger(__name__)
router = APIRouter(tags=["authority"])

_demo_pipelines: dict[str, object] = {}


def _demo_pipeline_for(location: AuthorityLocation):
    """Lazily built, cached per-fixture demo pipeline (mirrors
    ``app.api.query.get_pipeline``'s lazy-singleton pattern) so a demo
    overview request does not rebuild the LangGraph six times."""
    pipeline = _demo_pipelines.get(location.demo_fixture)
    if pipeline is None:
        from app.scenario.fixtures import pipeline_for_fixture

        pipeline = pipeline_for_fixture(location.demo_fixture)
        _demo_pipelines[location.demo_fixture] = pipeline
    return pipeline


def _message_for(location: AuthorityLocation) -> str:
    return f"Is it safe to go fishing near {location.display_name} right now?"


async def _evaluate(location: AuthorityLocation, *, edition: str):
    if edition == "demo":
        from app.scenario.fixtures import MANGALORE, SCENARIO_NOW

        pipeline = _demo_pipeline_for(location)
        # Every scenario fixture's synthetic weather/ocean observations are
        # hardcoded to MANGALORE and (for several fixtures, e.g. thunderstorm/
        # cyclone) to SCENARIO_NOW (see app.scenario.fixtures._obs / _thunder
        # storm_obs / _cyclone_obs) - that is what the frozen regression
        # scenarios query, at the one instant the fixture data is actually
        # "valid" for (app.scenario.runner passes the same SCENARIO_NOW).
        # Evaluating at the real coordinate and/or the real current time
        # instead would feed the Marine Data Fabric observations that are
        # spatially and/or temporally somewhere else entirely, which trips
        # its validity gate and falsely reports every such location as
        # data-insufficient. The map/table still show each location's real
        # position (from AuthorityLocation.coordinate, never from this call)
        # - only the demo pipeline's internal evaluation point/time is
        # pinned to where and when the fixture data actually is.
        coordinate = MANGALORE
        now = SCENARIO_NOW
    else:
        pipeline = get_pipeline()
        coordinate = location.coordinate
        now = None
    return await pipeline.run(
        message=_message_for(location),
        coordinate=coordinate,
        stakeholder="coastal_authority",
        now=now,
    )


@router.get("/authority/overview", response_model=AuthorityOverview)
async def authority_overview(
    edition: str = Query(default="live", pattern="^(live|demo)$"),
) -> AuthorityOverview:
    locations = list(DEFAULT_LOCATIONS)
    responses = await asyncio.gather(
        *(_evaluate(loc, edition=edition) for loc in locations)
    )
    return build_overview(locations, list(responses), data_edition=edition.upper())
