"""app.services.http.get_json - retries, timeouts, transport + decode errors."""

from __future__ import annotations

import httpx
import pytest
import respx

from app.services.http import (
    HttpDecodeError,
    HttpStatusError,
    HttpTimeoutError,
    HttpTransportError,
    get_json,
)

URL = "https://example.test/api"


@respx.mock
async def test_success() -> None:
    respx.get(URL).respond(json={"ok": True, "n": 1})
    assert await get_json(URL) == {"ok": True, "n": 1}


@respx.mock
async def test_retries_a_500_then_succeeds() -> None:
    route = respx.get(URL)
    route.side_effect = [
        httpx.Response(500),
        httpx.Response(200, json={"ok": True}),
    ]
    assert await get_json(URL, retries=1, backoff_s=0.0) == {"ok": True}
    assert route.call_count == 2


@respx.mock
async def test_gives_up_after_retries_on_500() -> None:
    respx.get(URL).mock(return_value=httpx.Response(503))
    with pytest.raises(HttpStatusError) as exc:
        await get_json(URL, retries=1, backoff_s=0.0)
    assert exc.value.status_code == 503


@respx.mock
async def test_404_is_not_retried() -> None:
    route = respx.get(URL).mock(return_value=httpx.Response(404))
    with pytest.raises(HttpStatusError):
        await get_json(URL, retries=2, backoff_s=0.0)
    assert route.call_count == 1


@respx.mock
async def test_timeout_raises_after_retries() -> None:
    respx.get(URL).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(HttpTimeoutError):
        await get_json(URL, retries=1, backoff_s=0.0)


@respx.mock
async def test_transport_error() -> None:
    respx.get(URL).mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(HttpTransportError):
        await get_json(URL, retries=0)


@respx.mock
async def test_non_json_body_is_decode_error() -> None:
    respx.get(URL).respond(text="<html>not json</html>")
    with pytest.raises(HttpDecodeError):
        await get_json(URL, retries=0)


@respx.mock
async def test_json_array_body_is_decode_error() -> None:
    respx.get(URL).respond(json=[1, 2, 3])
    with pytest.raises(HttpDecodeError):
        await get_json(URL, retries=0)


@respx.mock
async def test_retries_zero_means_one_attempt() -> None:
    route = respx.get(URL).mock(return_value=httpx.Response(500))
    with pytest.raises(HttpStatusError):
        await get_json(URL, retries=0)
    assert route.call_count == 1
