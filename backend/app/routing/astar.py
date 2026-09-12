"""Deterministic A* over an occupancy :class:`Grid`.

Guarantees:
  * a blocked cell is never entered (blocked includes out-of-bounds);
  * a diagonal step is allowed only when both orthogonally-adjacent cells it
    "cuts past" are free (no corner cutting past an obstacle);
  * identical ``(grid, start, goal, allow_diagonal, max_expanded)`` always yields
    the identical result - the open set is ordered by
    ``(f, h, insertion-counter)``, a total order with no ties, and no step
    depends on dict/set iteration order.

Costs: 1.0 orthogonal, sqrt(2) diagonal. Heuristic: octile (admissible and
consistent for this move set) with diagonals, Manhattan without.

An optional per-cell ``cost_field`` (Phase 10D marine-aware routing, see
``app.routing.marine_cost``) lets a caller supply a cost MULTIPLIER for the
cell being entered. Multipliers are clamped to a minimum of 1.0 so a step can
only ever cost *more* than the base 1.0 / sqrt(2) - this keeps the existing
heuristic admissible without any change to it, and ``cost_field=None`` (the
default) reproduces the exact prior distance-only behaviour bit-for-bit.
"""

from __future__ import annotations

import heapq
import itertools
import math
from collections.abc import Iterator

import numpy as np

from app.routing.grid import Cell, Grid

_ORTHO: tuple[Cell, ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))
_DIAG: tuple[Cell, ...] = ((-1, -1), (-1, 1), (1, -1), (1, 1))
_SQRT2 = math.sqrt(2.0)


def _heuristic(a: Cell, b: Cell, *, allow_diagonal: bool) -> float:
    dr = abs(a[0] - b[0])
    dc = abs(a[1] - b[1])
    if allow_diagonal:  # octile distance
        return (dr + dc) + (_SQRT2 - 2.0) * min(dr, dc)
    return float(dr + dc)  # manhattan


def _neighbours(
    grid: Grid, cell: Cell, *, allow_diagonal: bool
) -> Iterator[tuple[Cell, float]]:
    row, col = cell
    for dr, dc in _ORTHO:
        nxt = (row + dr, col + dc)
        if grid.is_navigable(nxt):
            yield nxt, 1.0
    if not allow_diagonal:
        return
    for dr, dc in _DIAG:
        nxt = (row + dr, col + dc)
        if not grid.is_navigable(nxt):
            continue
        # No corner cutting: both shared orthogonal cells must be free.
        if grid.is_blocked((row + dr, col)) or grid.is_blocked((row, col + dc)):
            continue
        yield nxt, _SQRT2


def a_star(
    grid: Grid,
    start: Cell,
    goal: Cell,
    *,
    allow_diagonal: bool = True,
    max_expanded: int | None = None,
    cost_field: np.ndarray | None = None,
) -> tuple[list[Cell] | None, int]:
    """Return ``(path, expanded_node_count)``.

    ``path`` is ``None`` when start/goal are invalid or unreachable, or when
    ``max_expanded`` is reached first (the caller can tell budget exhaustion from
    genuine unreachability by comparing ``expanded_node_count`` with the budget
    it passed). When found, ``path`` includes both endpoints.

    ``cost_field``, when given, must have shape ``(grid.spec.n_rows,
    grid.spec.n_cols)``; its value at the cell being entered multiplies that
    step's base cost (clamped to a minimum of 1.0). Omitting it (the default)
    is identical to every prior caller's behaviour.
    """
    if cost_field is not None and cost_field.shape != (grid.spec.n_rows, grid.spec.n_cols):
        raise ValueError(
            f"cost_field shape {cost_field.shape} != grid "
            f"{(grid.spec.n_rows, grid.spec.n_cols)}"
        )
    if not (grid.in_bounds(start) and grid.in_bounds(goal)):
        return None, 0
    if grid.is_blocked(start) or grid.is_blocked(goal):
        return None, 0
    if start == goal:
        return [start], 0

    counter = itertools.count()
    open_heap: list[tuple[float, float, int, Cell]] = [
        (_heuristic(start, goal, allow_diagonal=allow_diagonal), 0.0, next(counter), start)
    ]
    g_score: dict[Cell, float] = {start: 0.0}
    came_from: dict[Cell, Cell] = {}
    closed: set[Cell] = set()
    expanded = 0

    while open_heap:
        _, _, _, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        # The heap tuple's second slot is ``h`` (kept only for the documented
        # (f, h, counter) tie-break order); the true accumulated cost is
        # looked up from ``g_score``, which is always populated by the time a
        # node reaches the open heap.
        current_g = g_score[current]
        if current == goal:
            return _reconstruct(came_from, current), expanded
        closed.add(current)
        expanded += 1
        if max_expanded is not None and expanded >= max_expanded:
            return None, expanded

        for nxt, step_cost in _neighbours(grid, current, allow_diagonal=allow_diagonal):
            if nxt in closed:
                continue
            if cost_field is not None:
                step_cost = step_cost * max(1.0, float(cost_field[nxt[0], nxt[1]]))
            tentative = current_g + step_cost
            if tentative < g_score.get(nxt, math.inf):
                g_score[nxt] = tentative
                came_from[nxt] = current
                h = _heuristic(nxt, goal, allow_diagonal=allow_diagonal)
                heapq.heappush(open_heap, (tentative + h, h, next(counter), nxt))

    return None, expanded


def path_cost(cells: list[Cell] | tuple[Cell, ...]) -> float:
    """A* grid cost of a cell path: 1.0 per orthogonal step, sqrt(2) per
    diagonal, 0.0 for a repeated (stationary) cell."""
    total = 0.0
    for (r1, c1), (r2, c2) in zip(cells, cells[1:]):
        dr, dc = abs(r1 - r2), abs(c1 - c2)
        if dr == 0 and dc == 0:
            continue
        total += _SQRT2 if (dr and dc) else 1.0
    return round(total, 6)


def weighted_path_cost(cells: list[Cell] | tuple[Cell, ...], cost_field: np.ndarray) -> float:
    """Like :func:`path_cost` but multiplying each step by ``cost_field``'s
    value at the cell being entered (clamped to a minimum of 1.0, matching
    :func:`a_star`'s own clamping). Reporting-only - never consulted by A*
    itself for search or tie-breaking."""
    total = 0.0
    for (r1, c1), (r2, c2) in zip(cells, cells[1:]):
        dr, dc = abs(r1 - r2), abs(c1 - c2)
        if dr == 0 and dc == 0:
            continue
        base = _SQRT2 if (dr and dc) else 1.0
        total += base * max(1.0, float(cost_field[r2, c2]))
    return round(total, 6)


def _reconstruct(came_from: dict[Cell, Cell], current: Cell) -> list[Cell]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path
