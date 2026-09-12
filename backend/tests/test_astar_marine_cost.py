"""A* with an optional per-cell marine cost multiplier (Phase 10D).

Proves the old distance-only behaviour is exactly unchanged when no
``cost_field`` is supplied, and that a spatially-varying cost field can (and
does) change which path A* prefers - without ever making a blocked cell
reachable or weakening the existing invariants (no corner cutting, admissible
heuristic, deterministic tie-breaking, max_expanded budget)."""

from __future__ import annotations

import numpy as np
import pytest

from app.routing.astar import a_star, path_cost, weighted_path_cost
from tests.factories import blank_grid, grid_with_blocks


# ---- backward compatibility --------------------------------------------

def test_cost_field_none_is_bit_identical_to_prior_behaviour() -> None:
    grid = grid_with_blocks({(1, 1), (2, 1), (3, 1)})
    without_kwarg = a_star(grid, (0, 0), (4, 4), allow_diagonal=True)
    with_none = a_star(grid, (0, 0), (4, 4), allow_diagonal=True, cost_field=None)
    assert without_kwarg == with_none


def test_uniform_cost_field_of_one_matches_distance_only_path() -> None:
    grid = grid_with_blocks({(1, 1), (2, 1), (3, 1)})
    baseline, _ = a_star(grid, (0, 0), (4, 4), allow_diagonal=True)
    uniform_field = np.ones((5, 5), dtype=np.float64)
    with_field, _ = a_star(grid, (0, 0), (4, 4), allow_diagonal=True, cost_field=uniform_field)
    assert with_field == baseline


def test_cost_field_shape_mismatch_raises() -> None:
    grid = blank_grid(5, 5)
    bad_field = np.ones((3, 3), dtype=np.float64)
    with pytest.raises(ValueError):
        a_star(grid, (0, 0), (4, 4), cost_field=bad_field)


def test_blocked_cells_still_unreachable_with_cost_field() -> None:
    grid = grid_with_blocks({(2, 2)})
    field = np.ones((5, 5), dtype=np.float64) * 1.5
    path, _ = a_star(grid, (0, 0), (2, 2), cost_field=field)
    assert path is None


def test_max_expanded_budget_unchanged_with_cost_field() -> None:
    grid = blank_grid(20, 20)
    field = np.ones((20, 20), dtype=np.float64)
    without, exp_without = a_star(grid, (0, 0), (19, 19), max_expanded=5)
    withf, exp_with = a_star(grid, (0, 0), (19, 19), max_expanded=5, cost_field=field)
    assert without is None and withf is None
    assert exp_without == exp_with == 5


def test_no_corner_cutting_preserved_with_cost_field() -> None:
    grid = grid_with_blocks({(0, 1), (1, 0)}, n_rows=2, n_cols=2)
    field = np.ones((2, 2), dtype=np.float64) * 2.0
    path, _ = a_star(grid, (0, 0), (1, 1), allow_diagonal=True, cost_field=field)
    assert path is None


def test_determinism_preserved_with_cost_field() -> None:
    grid = grid_with_blocks({(1, 1), (2, 1), (3, 1)})
    field = np.full((5, 5), 1.3)
    first = a_star(grid, (0, 0), (4, 4), allow_diagonal=True, cost_field=field)
    for _ in range(10):
        assert a_star(grid, (0, 0), (4, 4), allow_diagonal=True, cost_field=field) == first


# ---- values below 1.0 are clamped (admissibility can never be broken) --

def test_sub_one_multiplier_is_clamped_to_one() -> None:
    grid = blank_grid(5, 5)
    cheap = np.full((5, 5), 0.1)  # would break admissibility if honoured raw
    path, _ = a_star(grid, (0, 0), (4, 4), allow_diagonal=False, cost_field=cheap)
    assert path is not None
    assert path_cost(path) == 8.0  # still the true distance-only cost


# ---- synthetic detour: spatial variation changes the chosen corridor ---
#
# A single wall (column 4) separates west from east, with exactly two gaps:
#   * gap A at row 3 - only 1 row away from the start/goal row (4): the
#     SHORTER corridor (10 grid steps).
#   * gap B at row 0 - 4 rows away: the LONGER corridor (16 grid steps).
# Distance-only A* must prefer gap A (it is strictly shorter). Taxing row 3
# with a high cost multiplier must flip marine-aware A* onto gap B instead -
# a slightly longer route with a lower total (weighted) cost.

def _two_corridor_grid():
    n = 9
    blocked = {(r, 4) for r in range(n) if r not in (0, 3)}
    grid = grid_with_blocks(blocked, n_rows=n, n_cols=n)
    return grid, (4, 0), (4, 8)


def test_synthetic_detour_distance_only_prefers_the_shorter_corridor() -> None:
    grid, start, goal = _two_corridor_grid()
    path, _ = a_star(grid, start, goal, allow_diagonal=False)
    assert path is not None
    assert (3, 4) in path  # shorter gap (row 3)
    assert (0, 4) not in path


def test_synthetic_detour_marine_aware_prefers_the_low_cost_corridor() -> None:
    grid, start, goal = _two_corridor_grid()
    field = np.ones((9, 9), dtype=np.float64)
    field[3, 3:6] = 5.0  # tax the shorter corridor's gap-crossing cells heavily
    path, _ = a_star(grid, start, goal, allow_diagonal=False, cost_field=field)
    assert path is not None
    assert (0, 4) in path  # detours through the longer, untaxed gap
    assert (3, 4) not in path


def test_marine_aware_route_has_lower_weighted_cost_even_if_longer() -> None:
    grid, start, goal = _two_corridor_grid()
    field = np.ones((9, 9), dtype=np.float64)
    field[3, 3:6] = 5.0

    distance_only, _ = a_star(grid, start, goal, allow_diagonal=False)
    marine_aware, _ = a_star(grid, start, goal, allow_diagonal=False, cost_field=field)

    cost_of_distance_only_under_field = weighted_path_cost(distance_only, field)
    cost_of_marine_aware = weighted_path_cost(marine_aware, field)
    assert cost_of_marine_aware < cost_of_distance_only_under_field
    # ...even though it is not shorter (in fact longer) in pure grid-step terms.
    assert path_cost(marine_aware) > path_cost(distance_only)


# ---- weighted_path_cost ---------------------------------------------------

def test_weighted_path_cost_matches_path_cost_for_uniform_ones() -> None:
    cells = [(0, 0), (0, 1), (0, 2), (0, 3)]
    field = np.ones((1, 4), dtype=np.float64)
    assert weighted_path_cost(cells, field) == path_cost(cells)


def test_weighted_path_cost_scales_with_multiplier() -> None:
    cells = [(0, 0), (0, 1), (0, 2)]
    field = np.full((1, 3), 2.0)
    assert weighted_path_cost(cells, field) == pytest.approx(2 * path_cost(cells))


def test_weighted_path_cost_clamps_sub_one_multipliers() -> None:
    cells = [(0, 0), (0, 1)]
    field = np.full((1, 2), 0.2)
    assert weighted_path_cost(cells, field) == 1.0
