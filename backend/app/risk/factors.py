"""Per-factor risk functions.

Every function is pure: given the same input value(s) and the same
:class:`FactorConfig` it returns the same :class:`RiskFactor`. Missing input is
represented as ``FactorStatus.MISSING_DATA`` - never as a zero score.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.models.common import SignalKind
from app.models.risk import FactorStatus, RiskFactor
from app.risk.config import FactorConfig, interpolate

# WMO 4677 present-weather codes that denote a thunderstorm - used only as a
# thunderstorm / lightning PROXY, never as strike-level detection.
THUNDERSTORM_WMO_CODES: frozenset[int] = frozenset({95, 96, 97, 98, 99})


def _contribution(weight: float, normalized: float) -> float:
    return round(weight * normalized * 100.0, 6)


def _missing(
    name: str, config: FactorConfig, note: str, evidence_ids: Sequence[str]
) -> RiskFactor:
    return RiskFactor(
        name=name,
        status=FactorStatus.MISSING_DATA,
        unit=config.unit,
        weight=config.weight,
        signal_kind=config.signal_kind,
        required_for_safety=config.required_for_safety,
        evidence_ids=tuple(evidence_ids),
        notes=(note,),
    )


def evaluate_numeric_factor(
    name: str,
    value: float | None,
    config: FactorConfig,
    *,
    evidence_ids: Sequence[str] = (),
    band_label: str | None = None,
) -> RiskFactor:
    """Generic factor: interpolate a single numeric input through the config."""
    if value is None:
        return _missing(name, config, f"{name}: no input value", evidence_ids)
    normalized = interpolate(float(value), config.breakpoints)
    return RiskFactor(
        name=name,
        status=FactorStatus.EVALUATED,
        input_value=float(value),
        unit=config.unit,
        normalized_score=normalized,
        weight=config.weight,
        contribution=_contribution(config.weight, normalized),
        band=band_label or f"{name} sub-score {normalized:.2f}",
        signal_kind=config.signal_kind,
        required_for_safety=config.required_for_safety,
        evidence_ids=tuple(evidence_ids),
    )


def evaluate_lightning_proxy(
    config: FactorConfig,
    *,
    weather_codes: Sequence[int] | None = None,
    thunderstorm_proxy: bool | None = None,
    evidence_ids: Sequence[str] = (),
) -> RiskFactor:
    """Thunderstorm / lightning PROXY from WMO codes 95-99 or an explicit flag."""
    active: bool | None
    trigger: str
    if thunderstorm_proxy is not None:
        active = bool(thunderstorm_proxy)
        trigger = "explicit thunderstorm_proxy flag"
    elif weather_codes is not None:
        hits = sorted(c for c in weather_codes if c in THUNDERSTORM_WMO_CODES)
        active = bool(hits)
        trigger = f"WMO codes {hits}" if hits else "no thunderstorm WMO codes"
    else:
        active = None
        trigger = ""

    if active is None:
        return _missing(
            "lightning_proxy", config, "lightning_proxy: no weather codes or flag", evidence_ids
        )

    normalized = interpolate(1.0 if active else 0.0, config.breakpoints)
    state = "active" if active else "inactive"
    return RiskFactor(
        name="lightning_proxy",
        status=FactorStatus.EVALUATED,
        input_value=1.0 if active else 0.0,
        unit=config.unit,
        normalized_score=normalized,
        weight=config.weight,
        contribution=_contribution(config.weight, normalized),
        band=f"thunderstorm/lightning proxy {state}",
        signal_kind=SignalKind.PROXY,
        required_for_safety=config.required_for_safety,
        evidence_ids=tuple(evidence_ids),
        notes=(
            f"proxy/model-derived signal ({trigger}); not strike-level detection",
        ),
    )


def evaluate_cyclone_proxy(
    config: FactorConfig,
    *,
    min_pressure_hpa: float | None = None,
    max_gust_ms: float | None = None,
    cyclone_proxy: bool | None = None,
    evidence_ids: Sequence[str] = (),
) -> RiskFactor:
    """Model-derived cyclone PROXY: worst of a pressure and a gust sub-signal,
    or an explicit 0/1 flag. Not a certified cyclone tracker."""
    sub_scores: list[tuple[str, float]] = []
    if cyclone_proxy is not None:
        sub_scores.append(("explicit flag", 1.0 if cyclone_proxy else 0.0))
    if min_pressure_hpa is not None and config.pressure_hpa_breakpoints is not None:
        sub_scores.append(
            ("pressure", interpolate(float(min_pressure_hpa), config.pressure_hpa_breakpoints))
        )
    if max_gust_ms is not None and config.gust_ms_breakpoints is not None:
        sub_scores.append(
            ("gust", interpolate(float(max_gust_ms), config.gust_ms_breakpoints))
        )

    if not sub_scores:
        return _missing(
            "cyclone_proxy", config, "cyclone_proxy: no pressure, gust or flag", evidence_ids
        )

    driver, index = max(sub_scores, key=lambda item: item[1])
    normalized = interpolate(index, config.breakpoints)
    return RiskFactor(
        name="cyclone_proxy",
        status=FactorStatus.EVALUATED,
        input_value=round(index, 6),
        unit=config.unit,
        normalized_score=normalized,
        weight=config.weight,
        contribution=_contribution(config.weight, normalized),
        band=f"cyclone proxy index {index:.2f} (driver: {driver})",
        signal_kind=SignalKind.MODEL_DERIVED,
        required_for_safety=config.required_for_safety,
        evidence_ids=tuple(evidence_ids),
        notes=("model-derived cyclone proxy; not certified real-time detection",),
    )


def evaluate_geofence_factor(
    config: FactorConfig,
    *,
    inside_hard: bool | None = None,
    nearest_hard_distance_m: float | None = None,
    evidence_ids: Sequence[str] = (),
) -> RiskFactor:
    """Proximity to the nearest HARD geofence. Enforcement is the Safety Guard's
    job; this only feeds the risk score."""
    if inside_hard:
        distance = 0.0
    elif nearest_hard_distance_m is not None:
        distance = max(0.0, float(nearest_hard_distance_m))
    else:
        return _missing(
            "geofence", config, "geofence: no distance information", evidence_ids
        )

    normalized = interpolate(distance, config.breakpoints)
    label = "inside hard geofence" if distance == 0.0 else f"{distance:.0f} m from hard geofence"
    return RiskFactor(
        name="geofence",
        status=FactorStatus.EVALUATED,
        input_value=distance,
        unit=config.unit,
        normalized_score=normalized,
        weight=config.weight,
        contribution=_contribution(config.weight, normalized),
        band=label,
        signal_kind=config.signal_kind,
        required_for_safety=config.required_for_safety,
        evidence_ids=tuple(evidence_ids),
    )
