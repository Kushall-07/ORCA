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

# On a host checkout this file lives at ``<repo>/backend/app/core/config.py`` so
# ``parents[3]`` is the repo root. Inside the backend container the code is copied
# to ``/app/app/...`` (``WORKDIR /app``), where ``parents[3]`` overshoots to
# ``/``. ``_resolve`` therefore probes several plausible bases and picks the
# first one that actually contains the requested relative path.
_CONFIG_FILE = Path(__file__).resolve()
_REPO_ROOT = _CONFIG_FILE.parents[3]


def _data_bases() -> tuple[Path, ...]:
    """Ordered candidate bases for resolving a *relative* data dir.

    The repo root covers a host checkout; ``parents[2]`` is ``backend/`` on a
    host and ``/app`` in the container; the CWD and ``/app`` are extra safety
    for the Docker layout. Evaluated per call so the CWD is current.
    """
    return (
        _REPO_ROOT,
        _CONFIG_FILE.parents[2],
        Path.cwd(),
        Path("/app"),
    )


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
    # Single authoritative model id, consumed by GroqLlmClient for BOTH the
    # Query Understanding agent and the Evidence & Explanation agent. Override
    # with the GROQ_MODEL env var. The earlier Llama 3.3 70B "versatile" model
    # was retired by Groq for the developer/free tier and now returns
    # 404 model_not_found.
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="openai/gpt-oss-120b")
    groq_timeout_seconds: float = Field(default=20.0, gt=0)
    llm_max_retries: int = Field(default=1, ge=0, le=3)

    # ---- Phase 5: orchestration ----
    session_max_turns: int = Field(default=5, ge=1, le=20)
    orca_grid_cell_deg: float = Field(default=0.05, gt=0.0, le=1.0)
    orca_grid_pad_deg: float = Field(default=0.35, gt=0.0, le=5.0)

    # ---- What-if / scenario-sensitivity simulation (competitor-audit adoption) ----
    # A completed query turn's realised Risk Engine input is kept on the
    # in-memory session so a follow-up ``POST /whatif`` can perturb wave height /
    # wind speed on a COPY and re-run the SAME deterministic Risk -> Safety ->
    # Decision chain. The baseline is refused once the turn it came from is older
    # than this - an honest staleness guard, never a re-score of stale data as if
    # it were current.
    whatif_baseline_max_age_minutes: int = Field(default=180, ge=1, le=1440)

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

    # ---- Phase 9: environmental data (SST + chlorophyll-a) ----
    # SST rides the existing Open-Meteo Marine call - no settings needed.
    # Chlorophyll-a is fetched from NOAA CoastWatch ERDDAP (primary, no auth).
    # INCOIS ERDDAP is an OPTIONAL secondary: it is only tried when BOTH a URL
    # and a dataset id are configured, and always with normal TLS verification
    # (verify=True, or verify=<oceancolor_incois_ca_bundle> if a chain file is
    # supplied). It is never a required dependency. All settings are non-secret.
    oceancolor_enabled: bool = Field(default=True)
    oceancolor_noaa_erddap_url: str = Field(
        default="https://coastwatch.noaa.gov/erddap"
    )
    oceancolor_noaa_chl_dataset: str = Field(default="noaacwNPPVIIRSchlaDaily")
    oceancolor_noaa_chl_variable: str = Field(default="chlor_a")
    # Blank unless a real INCOIS ERDDAP dataset id has been verified.
    oceancolor_incois_erddap_url: str = Field(default="")
    oceancolor_incois_chl_dataset: str = Field(default="")
    oceancolor_incois_chl_variable: str = Field(default="chlor_a")
    # Optional PEM file completing the INCOIS TLS chain. Empty -> plain verify=True.
    oceancolor_incois_ca_bundle: str = Field(default="")
    oceancolor_timeout_seconds: float = Field(default=15.0, gt=0)
    oceancolor_cache_ttl_seconds: int = Field(default=32400, gt=0)      # 9 h
    oceancolor_cache_max_age_seconds: int = Field(default=86400, gt=0)  # 24 h
    # A chlorophyll composite older than this (relative to the decision time) is
    # not an acceptable observation. Kept consistent with the Temporal Validity
    # Gate's chlorophyll_a stale window.
    oceancolor_chl_max_age_seconds: int = Field(default=864000, gt=0)   # 10 d

    # ---- Official IMD marine advisory (Sea Area Bulletin) ----
    # The live API (api.imd.gov.in) requires BOTH an API key header and a
    # bearer JWT; neither is self-service on the public reference page. With
    # either blank the advisory agent returns an explicit UNAVAILABLE result -
    # it never fabricates a warning. Never hard-code a real key/token here.
    imd_api_base_url: str = Field(default="https://api.imd.gov.in")
    imd_sea_bulletin_path: str = Field(default="/api/v1/seabulletin")
    imd_api_key: str = Field(default="")
    imd_api_bearer_token: str = Field(default="")
    imd_timeout_seconds: float = Field(default=10.0, gt=0)
    imd_cache_ttl_seconds: int = Field(default=3600, gt=0)       # 1 h
    imd_cache_max_age_seconds: int = Field(default=43200, gt=0)  # 12 h

    # ---- Official INCOIS PFZ reference geometry (public, no auth) ----
    incois_pfz_wfs_base_url: str = Field(default="https://www.incois.gov.in/geoserver")
    incois_pfz_timeout_seconds: float = Field(default=15.0, gt=0)
    incois_pfz_cache_ttl_seconds: int = Field(default=21600, gt=0)      # 6 h
    incois_pfz_cache_max_age_seconds: int = Field(default=86400, gt=0)  # 24 h
    incois_pfz_match_radius_km: float = Field(default=250.0, gt=0)
    incois_pfz_max_features: int = Field(default=40, ge=1, le=500)

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
        """Resolve a data directory so it works both on a host checkout and
        inside the container.

        Absolute paths (e.g. ``DATA_STATIC_DIR=/data/static``) are used as-is.
        A relative path is tried against each :data:`_DATA_BASES` candidate; the
        first base under which it exists wins. If none exist we fall back to the
        repo-root-relative path (unchanged historical behaviour) so a genuinely
        missing data dir stays visible rather than silently resolving elsewhere.
        """
        path = Path(value)
        if path.is_absolute():
            return path
        for base in _data_bases():
            candidate = base / path
            if candidate.exists():
                return candidate
        return _REPO_ROOT / path

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
