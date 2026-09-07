"""Minimal async JSON-over-HTTP helper built on the existing ``httpx`` dependency.

Deliberately small: one function, a bounded retry on transient failures, typed
errors so callers can distinguish "the network failed" from "the service
answered with garbage". No framework.
"""

from __future__ import annotations

import asyncio
from typing import Any, Mapping

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class HttpClientError(RuntimeError):
    """Base class for every failure of :func:`get_json`."""


class HttpTimeoutError(HttpClientError):
    pass


class HttpTransportError(HttpClientError):
    """Connection refused / DNS / TLS / read error."""


class HttpStatusError(HttpClientError):
    def __init__(self, status_code: int, url: str) -> None:
        super().__init__(f"HTTP {status_code} from {url}")
        self.status_code = status_code


class HttpDecodeError(HttpClientError):
    """The response body was not valid JSON."""


async def get_json(
    url: str,
    params: Mapping[str, Any] | None = None,
    *,
    timeout_s: float = 10.0,
    retries: int = 1,
    client: httpx.AsyncClient | None = None,
    backoff_s: float = 0.2,
) -> dict[str, Any]:
    """GET ``url`` and return the parsed JSON object.

    Retries at most ``retries`` times on a timeout, a transport error, or a
    retryable status (429 / 5xx). Raises a :class:`HttpClientError` subclass on
    definitive failure.
    """
    attempt = 0
    owns_client = client is None
    active = client or httpx.AsyncClient(timeout=timeout_s)
    try:
        while True:
            attempt += 1
            try:
                response = await active.get(url, params=params, timeout=timeout_s)
            except httpx.TimeoutException as exc:
                if attempt <= retries:
                    await asyncio.sleep(backoff_s)
                    continue
                raise HttpTimeoutError(f"timeout calling {url}") from exc
            except httpx.TransportError as exc:
                if attempt <= retries:
                    await asyncio.sleep(backoff_s)
                    continue
                raise HttpTransportError(f"transport error calling {url}: {exc}") from exc

            if response.status_code in _RETRYABLE_STATUS and attempt <= retries:
                await asyncio.sleep(backoff_s)
                continue
            if response.status_code >= 400:
                raise HttpStatusError(response.status_code, url)

            try:
                payload = response.json()
            except ValueError as exc:
                raise HttpDecodeError(f"non-JSON response from {url}") from exc
            if not isinstance(payload, dict):
                raise HttpDecodeError(f"expected a JSON object from {url}")
            return payload
    finally:
        if owns_client:
            await active.aclose()
