"""MOSDAC integration is structure-only and strictly non-blocking."""

from __future__ import annotations

import pytest

from app.services.mosdac import (
    MosdacClient,
    MosdacEndpointUnverified,
    MosdacNotConfigured,
    mosdac_status,
)


async def test_not_configured_raises_not_configured() -> None:
    client = MosdacClient(username="", password="")
    assert client.configured is False
    with pytest.raises(MosdacNotConfigured):
        await client.fetch()


async def test_configured_but_no_verified_endpoint() -> None:
    client = MosdacClient(username="u", password="p")
    assert client.configured is True
    with pytest.raises(MosdacEndpointUnverified):
        await client.fetch()


def test_status_is_non_blocking_and_not_integrated() -> None:
    status = mosdac_status(MosdacClient(username="u", password="p"))
    assert status["blocking"] is False
    assert status["integrated"] is False
    assert status["role"] == "secondary"
    assert status["configured"] is True


async def test_fabric_build_succeeds_even_though_mosdac_would_fail() -> None:
    from datetime import datetime, timezone

    from app.fabric.builder import build_fabric
    from app.models.common import Coordinate

    client = MosdacClient(username="u", password="p")
    try:
        await client.fetch()
    except (MosdacNotConfigured, MosdacEndpointUnverified):
        pass  # non-blocking: the pipeline just continues

    fabric = build_fabric(
        query_coordinate=Coordinate(latitude=12.87, longitude=74.84),
        query_time=datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc),
    )
    assert fabric is not None  # a MOSDAC failure never stops fabric construction
