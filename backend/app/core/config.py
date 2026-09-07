"""Application configuration.

All settings come from environment variables (optionally loaded from a ``.env``
file). Secrets never have a hard-coded value: they default to an empty string so
that a missing secret is obvious at the point of use rather than silently wrong.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_CORS = ["http://localhost:3000", "http://127.0.0.1:3000"]
# backend/app/core/config.py -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Typed view of the process environment.

    Instantiated once via :func:`get_settings` (LRU-cached) so the environment is
    read a single time per process.
    """

    model_config = SettingsConfigDict(
        # Support both a repo-root .env (backend run on the host) and a
        # backend/.env (which takes priority if present).
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    app_name: str = "ORCA"
    app_version: str = "0.1.0"
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # ---- CORS (local frontend dev server) ----
    cors_origins: list[str] = Field(default_factory=lambda: list(_DEFAULT_CORS))

    # ---- Datastores ----
    # Docker network uses the service names; host runs override with localhost.
    database_url: str = Field(
        default="postgresql+psycopg://orca:orca@localhost:5432/orca"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    # ---- LLM provider (Groq is the sole provider; used from Phase 5) ----
    groq_api_key: str = Field(default="")

    # ---- Secondary / supplementary data sources (later phases) ----
    mosdac_username: str = Field(default="")
    mosdac_password: str = Field(default="")
    copernicus_username: str = Field(default="")
    copernicus_password: str = Field(default="")
    wdpa_api_token: str = Field(default="")

    # ---- Health-check tuning ----
    health_check_timeout_seconds: float = Field(default=3.0, gt=0)

    # ---- Phase 4: data agents (Open-Meteo is the MVP live source) ----
    openmeteo_weather_url: str = Field(
        default="https://api.open-meteo.com/v1/forecast"
    )
    openmeteo_marine_url: str = Field(
        default="https://marine-api.open-meteo.com/v1/marine"
    )
    openmeteo_timeout_seconds: float = Field(default=10.0, gt=0)
    openmeteo_retries: int = Field(default=1, ge=0, le=3)
    openmeteo_forecast_hours: int = Field(default=48, gt=0, le=384)

    # ---- Phase 4: Redis cache (bucketing keeps the key space bounded) ----
    cache_enabled: bool = Field(default=True)
    cache_coord_decimals: int = Field(default=2, ge=0, le=4)
    cache_time_bucket: str = Field(default="hour")  # hour | day
    weather_cache_ttl_seconds: int = Field(default=3600, gt=0)
    weather_cache_max_age_seconds: int = Field(default=21600, gt=0)
    marine_cache_ttl_seconds: int = Field(default=3600, gt=0)
    marine_cache_max_age_seconds: int = Field(default=21600, gt=0)

    # ---- Phase 4: data locations + GIS backend ----
    data_static_dir: str = Field(default="data/static")
    data_demo_dir: str = Field(default="data/demo")
    data_reference_dir: str = Field(default="data/reference")
    gis_backend: str = Field(default="auto")  # auto | postgis | offline
    # When true, agents may fall back to clearly-labelled DEMO data (never LIVE).
    agent_demo_fallback: bool = Field(default=False)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, value: object) -> object:
        """Accept a comma-separated string as well as a JSON list."""
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return list(_DEFAULT_CORS)
            if stripped.startswith("["):
                return value  # let pydantic parse JSON
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    def _resolve(self, value: str) -> Path:
        """Resolve a data directory against the repo root when it is relative,
        so agents work regardless of the process working directory."""
        path = Path(value)
        return path if path.is_absolute() else (_REPO_ROOT / path)

    @property
    def static_path(self) -> Path:
        return self._resolve(self.data_static_dir)

    @property
    def demo_path(self) -> Path:
        return self._resolve(self.data_demo_dir)

    @property
    def reference_path(self) -> Path:
        return self._resolve(self.data_reference_dir)


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide :class:`Settings` singleton."""
    return Settings()
