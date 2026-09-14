"""Local INCOIS Oceansat-2 OCM NetCDF-3 reader (app.services.oceansat2).

Every test here reads the REAL, already-downloaded archive file
(``data/ocean_color/incois_oceansat2_datasets_da14_9092_a246_U1789400830217.nc``)
- no network, no fixtures, no mocking of the file format. Nothing here touches
RiskEngine / SafetyGuard / routing / PFZ / GIS.
"""

from __future__ import annotations

import pathlib

import pytest

from app.core.config import Settings
from app.services import oceansat2 as oc2

_DATA_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / "data"
    / "ocean_color"
    / "incois_oceansat2_datasets_da14_9092_a246_U1789400830217.nc"
)

pytestmark = pytest.mark.skipif(
    not _DATA_PATH.is_file(), reason="local Oceansat-2 archive not present in this checkout"
)


@pytest.fixture(scope="module")
def dataset() -> oc2.Oceansat2Dataset:
    return oc2.Oceansat2Dataset(_DATA_PATH)


# ---------------------------------------------------------------------------
# header / dimensions / coordinates
# ---------------------------------------------------------------------------
def test_time_range_matches_audit(dataset: oc2.Oceansat2Dataset) -> None:
    start, end = dataset.time_range
    assert start.strftime("%Y-%m-%d") == "2015-01-01"
    assert end.strftime("%Y-%m-%d") == "2019-12-31"


def test_time_dimension_length(dataset: oc2.Oceansat2Dataset) -> None:
    assert dataset.time_seconds.shape == (1826,)


def test_lat_lon_bounds_match_audit(dataset: oc2.Oceansat2Dataset) -> None:
    lat_lo, lat_hi = dataset.lat_bounds
    lon_lo, lon_hi = dataset.lon_bounds
    assert dataset.latitude.shape == (10,)
    assert dataset.longitude.shape == (11,)
    assert 12.75 < lat_lo < 12.76
    assert 13.10 < lat_hi < 13.11
    assert 74.63 < lon_lo < 74.65
    assert 75.03 < lon_hi < 75.05


# ---------------------------------------------------------------------------
# fill-value / missing-value handling
# ---------------------------------------------------------------------------
def test_chl_and_tsm_exclude_fill_values(dataset: oc2.Oceansat2Dataset) -> None:
    chl = dataset._array("CHL")  # noqa: SLF001 - deliberately exercising the raw array
    tsm = dataset._array("TSM")  # noqa: SLF001
    valid_chl = chl[chl > oc2._FILL_THRESHOLD]  # noqa: SLF001
    valid_tsm = tsm[tsm > oc2._FILL_THRESHOLD]  # noqa: SLF001
    # ~18.9% of cells are valid per the dataset audit (cloud/land masking).
    assert 0.15 < valid_chl.size / chl.size < 0.23
    assert 0.15 < valid_tsm.size / tsm.size < 0.23
    # CHL ~0.17-7.07 mg/m3, TSM ~0.01-200 mg/L per the audit.
    assert 0.1 < float(valid_chl.min()) < 0.3
    assert 6.5 < float(valid_chl.max()) < 7.5
    assert float(valid_tsm.min()) == pytest.approx(0.01, abs=1e-3)
    assert float(valid_tsm.max()) == pytest.approx(200.0, abs=1e-3)


def test_valid_day_fraction_matches_audit(dataset: oc2.Oceansat2Dataset) -> None:
    valid_days, total_days = dataset.valid_day_count("CHL")
    assert total_days == 1826
    fraction = valid_days / total_days
    # ~65.8% of days have at least one valid pixel per the dataset audit.
    assert 0.60 < fraction < 0.72


# ---------------------------------------------------------------------------
# reference_stats: real values, honest "no data here" outside the box
# ---------------------------------------------------------------------------
def test_reference_stats_mangalore_returns_real_chl_and_tsm(dataset: oc2.Oceansat2Dataset) -> None:
    chl = dataset.reference_stats("CHL", 12.87, 74.84)
    tsm = dataset.reference_stats("TSM", 12.87, 74.84)
    assert chl is not None and tsm is not None
    assert chl.unit == "mg/m3"
    assert tsm.unit == "mg/L"
    assert 0.1 < chl.median < 10.0
    assert 0.0 < tsm.median < 250.0
    assert chl.n_valid > 0 and chl.n_total == 1826
    assert chl.coverage_start == "2015-01-01" and chl.coverage_end == "2019-12-31"
    assert chl.distance_km < 10.0  # nearest valid cell is a few km from the harbour point


def test_reference_stats_netravati_returns_real_values(dataset: oc2.Oceansat2Dataset) -> None:
    tsm = dataset.reference_stats("TSM", 12.85, 74.84)
    assert tsm is not None
    assert tsm.n_valid > 0


def test_reference_stats_outside_box_is_none(dataset: oc2.Oceansat2Dataset) -> None:
    # Kochi is nowhere near the Mangalore/Netravati box.
    assert dataset.reference_stats("CHL", 9.97, 76.24) is None
    assert dataset.reference_stats("TSM", 9.97, 76.24) is None


def test_reference_stats_rejects_unknown_variable(dataset: oc2.Oceansat2Dataset) -> None:
    with pytest.raises(ValueError):
        dataset.reference_stats("KD490", 12.87, 74.84)


def test_contains_and_nearest_cell(dataset: oc2.Oceansat2Dataset) -> None:
    assert dataset.contains(12.87, 74.84) is True
    assert dataset.contains(9.97, 76.24) is False
    assert dataset.nearest_cell(9.97, 76.24) is None
    cell = dataset.nearest_cell(12.87, 74.84)
    assert cell is not None


# ---------------------------------------------------------------------------
# get_dataset(): process-wide singleton, non-blocking when missing
# ---------------------------------------------------------------------------
def test_get_dataset_returns_singleton_for_real_path() -> None:
    oc2._load.cache_clear()  # noqa: SLF001 - isolate from other tests' cache state
    settings = Settings(oceansat2_nc_path=str(_DATA_PATH))
    first = oc2.get_dataset(settings)
    second = oc2.get_dataset(settings)
    assert first is not None
    assert first is second
    oc2._load.cache_clear()  # noqa: SLF001


def test_get_dataset_missing_file_returns_none_not_error() -> None:
    oc2._load.cache_clear()  # noqa: SLF001
    settings = Settings(oceansat2_nc_path="data/ocean_color/does_not_exist.nc")
    assert oc2.get_dataset(settings) is None
    oc2._load.cache_clear()  # noqa: SLF001
