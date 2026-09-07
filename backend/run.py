"""Local development launcher.

Run with:  python run.py

Exists mainly for Windows: the bare `uvicorn` CLI creates a ProactorEventLoop on
Windows in single-process mode, which psycopg's async driver cannot use. Enabling
reload puts uvicorn into subprocess mode, where it picks the selector loop that
psycopg needs. Inside Docker (Linux) this script is not used - the image runs
`uvicorn app.main:app` directly.
"""

from __future__ import annotations

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn  # noqa: E402 - must follow the loop-policy call

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
