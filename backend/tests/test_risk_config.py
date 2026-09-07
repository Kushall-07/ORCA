"""Risk configuration loader: it validates, and it fails loudly."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from app.risk.config import (
    RiskConfigError,
    interpolate,
    load_risk_config,
)

_GOOD = textwrap.dedent(
    """
    version: "test-1"
    disclaimer: "test config"
    severity_bands:
      moderate: 25.0
      high: 50.0
      severe: 75.0
    factors:
      wave:
        weight: 0.30
        unit: m
        required_for_safety: true
        breakpoints: [[0, 0], [6, 1]]
      wind:
        weight: 0.25
        unit: m/s
        required_for_safety: true
        breakpoints: [[0, 0], [25, 1]]
      advisory:
        weight: 0.10
        unit: index
        breakpoints: [[0, 0], [1, 1]]
      lightning_proxy:
        weight: 0.10
        unit: bool
        breakpoints: [[0, 0], [1, 1]]
      cyclone_proxy:
        weight: 0.20
        unit: index
        breakpoints: [[0, 0], [1, 1]]
        pressure_hpa_breakpoints: [[940, 1], [1015, 0]]
        gust_ms_breakpoints: [[15, 0], [45, 1]]
      geofence:
        weight: 0.05
        unit: m
        breakpoints: [[0, 1], [10000, 0]]
    """
)


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "risk_weights.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_bundled_config_loads() -> None:
    cfg = load_risk_config()
    assert cfg.version
    assert abs(sum(f.weight for f in cfg.factors.values()) - 1.0) < 1e-6
    assert cfg.factors["wave"].required_for_safety is True
    assert cfg.factors["geofence"].required_for_safety is False


def test_good_temp_config(tmp_path: Path) -> None:
    cfg = load_risk_config(_write(tmp_path, _GOOD))
    assert cfg.version == "test-1"


def test_missing_file() -> None:
    with pytest.raises(RiskConfigError):
        load_risk_config("does/not/exist.yaml")


def test_not_yaml(tmp_path: Path) -> None:
    with pytest.raises(RiskConfigError):
        load_risk_config(_write(tmp_path, "::: not : yaml : ["))


def test_weights_not_summing_to_one(tmp_path: Path) -> None:
    bad = _GOOD.replace("weight: 0.30", "weight: 0.90")
    with pytest.raises(RiskConfigError):
        load_risk_config(_write(tmp_path, bad))


def test_missing_factor(tmp_path: Path) -> None:
    advisory_block = (
        "  advisory:\n"
        "    weight: 0.10\n"
        "    unit: index\n"
        "    breakpoints: [[0, 0], [1, 1]]\n"
    )
    assert advisory_block in _GOOD
    with pytest.raises(RiskConfigError):
        load_risk_config(_write(tmp_path, _GOOD.replace(advisory_block, "")))


def test_non_ascending_breakpoints(tmp_path: Path) -> None:
    assert "breakpoints: [[0, 0], [6, 1]]" in _GOOD
    bad = _GOOD.replace("breakpoints: [[0, 0], [6, 1]]", "breakpoints: [[6, 1], [0, 0]]")
    with pytest.raises(RiskConfigError):
        load_risk_config(_write(tmp_path, bad))


def test_score_out_of_range(tmp_path: Path) -> None:
    bad = _GOOD.replace("breakpoints: [[0, 0], [6, 1]]", "breakpoints: [[0, 0], [6, 2]]")
    with pytest.raises(RiskConfigError):
        load_risk_config(_write(tmp_path, bad))


def test_severity_bands_not_ascending(tmp_path: Path) -> None:
    bad = _GOOD.replace("high: 50.0", "high: 20.0")
    with pytest.raises(RiskConfigError):
        load_risk_config(_write(tmp_path, bad))


def test_cyclone_missing_subsignals(tmp_path: Path) -> None:
    target = "    pressure_hpa_breakpoints: [[940, 1], [1015, 0]]\n"
    assert target in _GOOD
    with pytest.raises(RiskConfigError):
        load_risk_config(_write(tmp_path, _GOOD.replace(target, "")))


@pytest.mark.parametrize(
    "value,expected",
    [(-1.0, 0.0), (0.0, 0.0), (3.0, 0.5), (6.0, 1.0), (10.0, 1.0)],
)
def test_interpolate(value: float, expected: float) -> None:
    assert interpolate(value, ((0.0, 0.0), (6.0, 1.0))) == pytest.approx(expected)


def test_interpolate_multi_segment() -> None:
    bp = ((0.0, 0.0), (1.0, 0.15), (2.0, 0.40))
    assert interpolate(1.5, bp) == pytest.approx(0.275)
