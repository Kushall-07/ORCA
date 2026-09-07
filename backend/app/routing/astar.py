"""Deterministic A* over an occupancy :class:`Grid`.

Guarantees:
  * a blocked cell is never entered;
  * a diagonal step is allowed only when both orthogonally-adjacent cells it
    "cuts past" are free (no corner cutting past an obstacle);
  * identical (grid, start, goal, allow_diagonal) always yields the identical
    path - the open set is ordered by (f, h, insertion-counter).
"""

from __future__ import annotations

import heapq
import itertools
import math
from collections.abc import Iterator

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


def _neighbours(grid: Grid, cell: Cell, *, allow_diagonal: bool) -> Iterator[tuple[Cell, float]]:
    row, col = cell
    for dr, dc in _ORTHO:
        nxt = (row + dr, col + dc)
        if grid.in_bounds(nxt) and not grid.is_blocked(nxt):
            yield nxt, 1.0
    if not allow_diagonal:
        return
    for dr, dc in _DIAG:
        nxt = (row + dr, col + dc)
        if not grid.in_bounds(nxt) or grid.is_blocked(nxt):
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
) -> tuple[list[Cell] | None, int]:
    """Return ``(path, expanded_node_count)``.

    ``path`` is ``None`` when start/goal are invalid or unreachable. When found it
    includes both endpoints.
    """
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
        _, current_g, _, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        if current == goal:
            return _reconstruct(came_from, current), expanded
        closed.add(current)
        expanded += 1

        for nxt, step_cost in _neighbours(grid, current, allow_diagonal=allow_diagonal):
            if nxt in closed:
                continue
            tentative = current_g + step_cost
            if tentative < g_score.get(nxt, math.inf):
                g_score[nxt] = tentative
                came_from[nxt] = current
                f = tentative + _heuristic(nxt, goal, allow_diagonal=allow_diagonal)
                h = _heuristic(nxt, goal, allow_diagonal=allow_diagonal)
                heapq.heappush(open_heap, (f, h, next(counter), nxt))

    return None, expanded


def _reconstruct(came_from: dict[Cell, Cell], current: Cell) -> list[Cell]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path
