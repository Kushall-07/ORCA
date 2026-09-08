"""Temporal Validity Gate.

Deterministically classifies a :class:`FabricRecord` as VALID / STALE / INVALID /
MISSING against a requested decision time, using configurable per-variable
windows from ``temporal_config.yaml``. It never turns stale data into valid data.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Final

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.models.fabric import FabricRecord, ValidityState

_DEFAULT_PATH: Final[Path] = Path(__file__).with_name("temporal_config.yaml")


class TemporalConfigError(RuntimeError):
    pass


class _Window(BaseModel):
    model_config = ConfigDict(frozen=True)
    fresh_seconds: int = Field(gt=0)
    stale_seconds: int = Field(gt=0)


class _ForecastRule(BaseModel):
    model_config = ConfigDict(frozen=True)
    max_retrieval_seconds: int = Field(gt=0)
    stale_retrieval_seconds: int = Field(gt=0)
    # The decision time may fall up to this many seconds BEFORE ``valid_from``
    # (the forecast provider's publish boundary) and still be served by that
    # window - an hourly forecast has one-hour native resolution, so a query a
    # few minutes before the first published hour is genuinely "now".
    # ``valid_until`` stays a hard upper bound; a decision time past it, or more
    # than one step before ``valid_from``, is still INVALID.
    alignment_seconds: int = Field(default=3600, gt=0)


class TemporalConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    disclaimer: str = ""
    default: _Window
    forecast: _ForecastRule
    by_variable: dict[str, _Window] = {}

    def window(self, variable: str) -> _Window:
        return self.by_variable.get(variable, self.default)


def load_temporal_config(path: str | Path | None = None) -> TemporalConfig:
    resolved = Path(path) if path is not None else _DEFAULT_PATH
    if not resolved.is_file():
        raise TemporalConfigError(f"temporal config not found: {resolved}")
    try:
        raw = yaml.safe_load(resolved.read_text(encoding="utf-8"))
        return TemporalConfig.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        raise TemporalConfigError(f"invalid temporal config: {exc}") from exc


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class GateVerdict(BaseModel):
    model_config = ConfigDict(frozen=True)
    state: ValidityState
    reason: str


def classify(
    record: FabricRecord,
    *,
    decision_time: datetime,
    now: datetime | None = None,
    config: TemporalConfig | None = None,
) -> GateVerdict:
    cfg = config or load_temporal_config()
    now = _aware(now) or datetime.now(timezone.utc)
    decision_time = _aware(decision_time)  # type: ignore[assignment]
    obs = record.observation

    if obs.value is None:
        return GateVerdict(state=ValidityState.MISSING, reason="no value")

    valid_from = _aware(obs.valid_from)
    valid_until = _aware(obs.valid_until)
    observed_at = _aware(obs.observed_at)
    retrieved_at = _aware(obs.retrieved_at)

    # ---- forecast record --------------------------------------------
    if valid_from is not None and valid_until is not None:
        # One-step lead tolerance on the lower bound only (see _ForecastRule):
        # a "right now" query issued minutes before the first published hourly
        # window is still that window's; the upper bound is not relaxed.
        lead = timedelta(seconds=cfg.forecast.alignment_seconds)
        if not (valid_from - lead <= decision_time <= valid_until):
            return GateVerdict(
                state=ValidityState.INVALID,
                reason=(
                    f"decision time {decision_time.isoformat()} outside forecast "
                    f"window [{valid_from.isoformat()}, {valid_until.isoformat()}] "
                    f"(lead tolerance {cfg.forecast.alignment_seconds}s)"
                ),
            )
        if retrieved_at is None:
            return GateVerdict(
                state=ValidityState.INVALID, reason="forecast has no retrieval timestamp"
            )
        retrieval_age = (now - retrieved_at).total_seconds()
        if retrieval_age > cfg.forecast.max_retrieval_seconds:
            return GateVerdict(
                state=ValidityState.INVALID,
                reason=f"forecast retrieved {retrieval_age:.0f}s ago (> max)",
            )
        if retrieval_age > cfg.forecast.stale_retrieval_seconds:
            return GateVerdict(
                state=ValidityState.STALE,
                reason=f"forecast retrieved {retrieval_age:.0f}s ago",
            )
        return GateVerdict(
            state=ValidityState.VALID, reason="forecast window covers the decision time"
        )

    # ---- observation record --------------------------------------
    if observed_at is None:
        return GateVerdict(state=ValidityState.INVALID, reason="no usable timestamp")
    window = cfg.window(obs.variable)
    age = abs((decision_time - observed_at).total_seconds())
    if age <= window.fresh_seconds:
        return GateVerdict(state=ValidityState.VALID, reason=f"age {age:.0f}s within fresh window")
    if age <= window.stale_seconds:
        return GateVerdict(state=ValidityState.STALE, reason=f"age {age:.0f}s within stale window")
    return GateVerdict(state=ValidityState.INVALID, reason=f"age {age:.0f}s exceeds stale window")


def apply_gate(
    records: list[FabricRecord],
    *,
    decision_time: datetime,
    now: datetime | None = None,
    config: TemporalConfig | None = None,
) -> list[FabricRecord]:
    cfg = config or load_temporal_config()
    out: list[FabricRecord] = []
    for r in records:
        verdict = classify(r, decision_time=decision_time, now=now, config=cfg)
        out.append(
            r.model_copy(update={"validity": verdict.state, "validity_reason": verdict.reason})
        )
    return out
