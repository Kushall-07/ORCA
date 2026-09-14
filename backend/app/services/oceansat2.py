"""Local INCOIS Oceansat-2 OCM archive - Marine Researcher R2/R3 support.

Reads ONE real, already-downloaded NetCDF-3 classic file (see
``Settings.oceansat2_nc_path``): historical chlorophyll-a (CHL) and Total
Suspended Matter (TSM) over a fixed Mangalore/Netravati coastal box
(~12.76-13.11N, 74.64-75.04E), 2015-01-01 to 2019-12-31. No netCDF4 / xarray /
h5py / scipy is installed or required - this module implements only the
handful of NetCDF-3 classic header/data records this ONE file actually uses
(a fixed-size, non-record ``time`` dimension; ``double`` coordinate variables;
``float`` data variables with a ``_FillValue``/``missing_value`` sentinel).
It is not a general NetCDF reader and must not be extended into one.

Purely offline and read-only: no network access, nothing here is ever on the
request-blocking path (a missing/unreadable file degrades to ``None``, the
same non-blocking posture as every other optional environmental source - see
``app.services.oceancolor``). Never imported by risk, safety, decision,
suitability, routing, GIS/geofencing or PFZ code.

Because the archive stops in 2019, it can never provide a "current" value -
every value this module returns is an explicitly historical reference
statistic (median / percentile / valid-day count over the whole 2015-2019
series at the nearest grid cell), never a live observation and never
extrapolated to the present.
"""

from __future__ import annotations

import math
import struct
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Final

import numpy as np

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# The file's CHL/TSM fill value is -9.999999790214768e+33 (stored as 4-byte
# float, so only ~7 significant digits survive) - anything more negative than
# this threshold is a fill/missing sentinel, never a real concentration.
_FILL_THRESHOLD: Final[float] = -1.0e30

_NC_DTYPE: Final[dict[int, str]] = {1: ">i1", 2: "S1", 3: ">i2", 4: ">i4", 5: ">f4", 6: ">f8"}
_NC_ELEM_SIZE: Final[dict[int, int]] = {1: 1, 2: 1, 3: 2, 4: 4, 5: 4, 6: 8}

_SUPPORTED_VARIABLES: Final[tuple[str, ...]] = ("CHL", "TSM")
_UNITS: Final[dict[str, str]] = {"CHL": "mg/m3", "TSM": "mg/L"}


class Oceansat2Error(RuntimeError):
    """A genuinely malformed/unreadable file. Callers treat this as
    non-blocking (see :func:`get_dataset`) - it is never raised to a request."""


@dataclass(frozen=True)
class _NcVar:
    dtype: str
    shape: tuple[int, ...]
    begin: int
    size: int


def _read_name(buf: bytes, pos: int) -> tuple[str, int]:
    (nelems,) = struct.unpack_from(">i", buf, pos)
    pos += 4
    name = buf[pos : pos + nelems].decode("utf-8", errors="replace")
    pos += nelems
    pad = (4 - nelems % 4) % 4
    return name, pos + pad


def _read_attr_values(buf: bytes, pos: int, nc_type: int, count: int) -> int:
    """Skip over one attribute's values (this reader never needs attribute
    *content*, only to advance past them to the next header record)."""
    size = _NC_ELEM_SIZE[nc_type]
    total = size * count
    pad = (4 - total % 4) % 4
    return pos + total + pad


def _skip_attr_list(buf: bytes, pos: int) -> int:
    (_tag,) = struct.unpack_from(">i", buf, pos)
    pos += 4
    (nelems,) = struct.unpack_from(">i", buf, pos)
    pos += 4
    for _ in range(nelems):
        _name, pos = _read_name(buf, pos)
        (nc_type,) = struct.unpack_from(">i", buf, pos)
        pos += 4
        (count,) = struct.unpack_from(">i", buf, pos)
        pos += 4
        pos = _read_attr_values(buf, pos, nc_type, count)
    return pos


class Oceansat2Dataset:
    """Read-only accessor for one Oceansat-2 OCM NetCDF-3 classic file.

    The (small) header is parsed once at construction; each variable's data is
    read directly from its file offset only when first requested and then
    cached on the instance (each of CHL/TSM is ~0.8 MB - never re-read after
    the first access, never eagerly loaded before it is needed).
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        with open(path, "rb") as f:
            header = f.read(65_536)
        if header[:3] != b"CDF":
            raise Oceansat2Error(f"{path}: not a NetCDF-3 (classic) file")
        version = header[3]
        if version not in (1, 2):
            raise Oceansat2Error(f"{path}: unsupported NetCDF-3 version {version}")

        pos = 4
        (_numrecs,) = struct.unpack_from(">i", header, pos)
        pos += 4

        # ---- dim_list ----
        (dim_tag,) = struct.unpack_from(">i", header, pos)
        pos += 4
        (ndims,) = struct.unpack_from(">i", header, pos)
        pos += 4
        dim_names: list[str] = []
        dim_lens: list[int] = []
        if dim_tag != 0:
            for _ in range(ndims):
                name, pos = _read_name(header, pos)
                (dimlen,) = struct.unpack_from(">i", header, pos)
                pos += 4
                dim_names.append(name)
                dim_lens.append(dimlen)
        dims = dict(zip(dim_names, dim_lens))

        # ---- gatt_list (skipped - no global attribute is needed) ----
        pos = _skip_attr_list(header, pos)

        # ---- var_list ----
        (var_tag,) = struct.unpack_from(">i", header, pos)
        pos += 4
        (nvars,) = struct.unpack_from(">i", header, pos)
        pos += 4
        variables: dict[str, _NcVar] = {}
        if var_tag != 0:
            for _ in range(nvars):
                name, pos = _read_name(header, pos)
                (ndim,) = struct.unpack_from(">i", header, pos)
                pos += 4
                dimids = []
                for _d in range(ndim):
                    (did,) = struct.unpack_from(">i", header, pos)
                    pos += 4
                    dimids.append(did)
                pos = _skip_attr_list(header, pos)
                (nc_type,) = struct.unpack_from(">i", header, pos)
                pos += 4
                (vsize,) = struct.unpack_from(">i", header, pos)
                pos += 4
                if version == 2:
                    (begin,) = struct.unpack_from(">q", header, pos)
                    pos += 8
                else:
                    (begin,) = struct.unpack_from(">i", header, pos)
                    pos += 4
                if nc_type not in _NC_DTYPE:
                    raise Oceansat2Error(f"{path}: unsupported NetCDF type {nc_type} for {name!r}")
                shape = tuple(dims[dim_names[d]] for d in dimids)
                variables[name] = _NcVar(dtype=_NC_DTYPE[nc_type], shape=shape, begin=begin, size=vsize)

        required = ("time", "latitude", "longitude", "CHL", "TSM")
        missing = [v for v in required if v not in variables]
        if missing:
            raise Oceansat2Error(f"{path}: missing required variable(s) {missing}")

        self._vars = variables
        self._lock = threading.Lock()
        self._cache: dict[str, np.ndarray] = {}

        self.time_seconds = self._read_full("time").astype(np.float64, copy=False)
        self.latitude = self._read_full("latitude").astype(np.float64, copy=False)
        self.longitude = self._read_full("longitude").astype(np.float64, copy=False)

    # ------------------------------------------------------------------
    def _read_full(self, name: str) -> np.ndarray:
        var = self._vars[name]
        with open(self._path, "rb") as f:
            f.seek(var.begin)
            raw = f.read(var.size)
        return np.frombuffer(raw, dtype=var.dtype).reshape(var.shape)

    def _array(self, name: str) -> np.ndarray:
        with self._lock:
            cached = self._cache.get(name)
            if cached is not None:
                return cached
            arr = self._read_full(name).astype(np.float32, copy=False)
            self._cache[name] = arr
            return arr

    # ------------------------------------------------------------------
    @property
    def time_range(self) -> tuple[datetime, datetime]:
        t0 = datetime.fromtimestamp(float(self.time_seconds[0]), tz=timezone.utc)
        t1 = datetime.fromtimestamp(float(self.time_seconds[-1]), tz=timezone.utc)
        return t0, t1

    @property
    def lat_bounds(self) -> tuple[float, float]:
        return float(self.latitude.min()), float(self.latitude.max())

    @property
    def lon_bounds(self) -> tuple[float, float]:
        return float(self.longitude.min()), float(self.longitude.max())

    def contains(self, latitude: float, longitude: float) -> bool:
        lat_lo, lat_hi = self.lat_bounds
        lon_lo, lon_hi = self.lon_bounds
        return lat_lo <= latitude <= lat_hi and lon_lo <= longitude <= lon_hi

    def nearest_cell(self, latitude: float, longitude: float) -> tuple[int, int] | None:
        """Nearest (lat_idx, lon_idx), or ``None`` when the point falls outside
        the dataset's fixed spatial box - this dataset is never extrapolated
        beyond its real coverage."""
        if not self.contains(latitude, longitude):
            return None
        lat_idx = int(np.argmin(np.abs(self.latitude - latitude)))
        lon_idx = int(np.argmin(np.abs(self.longitude - longitude)))
        return lat_idx, lon_idx

    def valid_day_count(self, variable: str) -> tuple[int, int]:
        """(days with >=1 valid pixel anywhere in the box, total days) - used
        only for dataset-level coverage reporting/tests, matching the dataset
        audit's ~65.8%-of-days figure."""
        arr = self._array(variable)
        valid_any = np.any(arr > _FILL_THRESHOLD, axis=(1, 2))
        return int(valid_any.sum()), int(arr.shape[0])

    def _nearest_valid_cell(self, variable: str, latitude: float, longitude: float) -> tuple[int, int] | None:
        """Nearest grid cell to ``(latitude, longitude)`` that has AT LEAST ONE
        real (non-cloud/non-land-masked) observation across the whole archive,
        searched over the WHOLE fixed box (only 10x11 = 110 cells - a plain
        distance scan, never an approximation). The coastal cells immediately
        around this box's shoreline are almost entirely land/cloud-masked (see
        the dataset audit's ~18.9% valid-cell figure), so trusting the single
        raw-index-nearest cell would silently return "no data" for a point
        exactly at a harbour/river-mouth gazetteer coordinate even though a
        real nearby ocean pixel exists a few km away - the same "search a
        small neighbourhood for the nearest valid pixel" reasoning
        ``app.services.oceancolor`` already uses for the live NOAA feed.
        ``distance_km`` on the returned stats always reports the real
        separation, so this is never presented as an exact-point reading.
        """
        if not self.contains(latitude, longitude):
            return None
        valid_any = np.any(self._array(variable) > _FILL_THRESHOLD, axis=0)
        if not valid_any.any():
            return None
        best: tuple[float, int, int] | None = None
        for i in range(self.latitude.shape[0]):
            for j in range(self.longitude.shape[0]):
                if not valid_any[i, j]:
                    continue
                d = _haversine_km(latitude, longitude, float(self.latitude[i]), float(self.longitude[j]))
                if best is None or d < best[0]:
                    best = (d, i, j)
        return (best[1], best[2]) if best is not None else None

    def reference_stats(
        self, variable: str, latitude: float, longitude: float
    ) -> "Oceansat2ReferenceStats | None":
        """Deterministic historical reference statistics (median / p10 / p90 /
        min / max / valid-day count) for ``variable`` at the nearest grid cell
        to ``(latitude, longitude)`` that has real data, computed over the FULL
        2015-2019 series - never a single fabricated point, never interpolated
        across cells.

        Returns ``None`` when the point is outside the dataset's spatial box,
        or when no cell in the box has any valid (non-cloud/land-masked)
        observation - both are honest "no data here" outcomes, not errors.
        """
        if variable not in _SUPPORTED_VARIABLES:
            raise ValueError(f"unsupported Oceansat-2 variable: {variable!r}")
        cell = self._nearest_valid_cell(variable, latitude, longitude)
        if cell is None:
            return None
        lat_idx, lon_idx = cell
        series = self._array(variable)[:, lat_idx, lon_idx]
        valid = series[series > _FILL_THRESHOLD]
        n_total = int(series.shape[0])
        n_valid = int(valid.shape[0])
        if n_valid == 0:
            return None
        start, end = self.time_range
        cell_lat = float(self.latitude[lat_idx])
        cell_lon = float(self.longitude[lon_idx])
        return Oceansat2ReferenceStats(
            variable=variable,
            unit=_UNITS[variable],
            median=float(np.median(valid)),
            p10=float(np.percentile(valid, 10)),
            p90=float(np.percentile(valid, 90)),
            minimum=float(valid.min()),
            maximum=float(valid.max()),
            n_valid=n_valid,
            n_total=n_total,
            cell_latitude=cell_lat,
            cell_longitude=cell_lon,
            distance_km=round(_haversine_km(latitude, longitude, cell_lat, cell_lon), 2),
            coverage_start=start.strftime("%Y-%m-%d"),
            coverage_end=end.strftime("%Y-%m-%d"),
        )


@dataclass(frozen=True)
class Oceansat2ReferenceStats:
    """One deterministic historical reference summary - real archive values
    only, never fabricated or extrapolated beyond ``coverage_start``/``coverage_end``."""

    variable: str            # "CHL" | "TSM"
    unit: str                # "mg/m3" | "mg/L"
    median: float
    p10: float
    p90: float
    minimum: float
    maximum: float
    n_valid: int
    n_total: int
    cell_latitude: float
    cell_longitude: float
    distance_km: float
    coverage_start: str      # "2015-01-01"
    coverage_end: str        # "2019-12-31"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_km = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r_km * math.asin(math.sqrt(a))


@lru_cache(maxsize=1)
def _load(path_str: str) -> Oceansat2Dataset | None:
    path = Path(path_str)
    if not path.is_file():
        logger.warning("oceansat2 archive not found at %s - R2/R3 augmentation disabled", path)
        return None
    try:
        return Oceansat2Dataset(path)
    except Oceansat2Error as exc:
        logger.warning("oceansat2 archive unreadable: %s", exc)
        return None


def get_dataset(settings: Settings | None = None) -> Oceansat2Dataset | None:
    """The process-wide Oceansat-2 dataset singleton, or ``None`` if the local
    file is missing/unreadable - always non-blocking for the caller."""
    active = settings or get_settings()
    return _load(str(active.oceansat2_path))
