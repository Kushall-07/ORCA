"""A* on small deterministic grids."""

from __future__ import annotations

from app.routing.astar import a_star
from tests.factories import blank_grid, grid_with_blocks


def test_straight_path_on_empty_grid() -> None:
    grid = blank_grid(1, 5)
    path, expanded = a_star(grid, (0, 0), (0, 4), allow_diagonal=False)
    assert path == [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)]
    assert expanded >= 4


def test_start_equals_goal() -> None:
    grid = blank_grid(3, 3)
    path, expanded = a_star(grid, (1, 1), (1, 1))
    assert path == [(1, 1)]
    assert expanded == 0


def test_obstacle_avoidance() -> None:
    # Wall along column 2 for rows 0..3; row 4 is open.
    grid = grid_with_blocks({(0, 2), (1, 2), (2, 2), (3, 2)})
    path, _ = a_star(grid, (0, 0), (0, 4), allow_diagonal=False)
    assert path is not None
    assert (4, 2) in path  # had to go around the bottom
    assert all(cell not in {(0, 2), (1, 2), (2, 2), (3, 2)} for cell in path)


def test_blocked_destination_returns_none() -> None:
    grid = grid_with_blocks({(2, 2)})
    path, expanded = a_star(grid, (0, 0), (2, 2))
    assert path is None
    assert expanded == 0


def test_blocked_start_returns_none() -> None:
    grid = grid_with_blocks({(0, 0)})
    path, _ = a_star(grid, (0, 0), (2, 2))
    assert path is None


def test_completely_blocked_route() -> None:
    # Full wall on column 2 (all 5 rows) separates start from goal.
    grid = grid_with_blocks({(r, 2) for r in range(5)})
    path, expanded = a_star(grid, (0, 0), (0, 4), allow_diagonal=True)
    assert path is None
    assert expanded > 0  # it really searched


def test_out_of_bounds_endpoints() -> None:
    grid = blank_grid(3, 3)
    assert a_star(grid, (-1, 0), (2, 2)) == (None, 0)
    assert a_star(grid, (0, 0), (3, 3)) == (None, 0)


def test_no_diagonal_corner_cutting() -> None:
    # Blocks at (0,1) and (1,0) box the corner; a diagonal (0,0)->(1,1) would
    # cut between them and must NOT be taken. With only those two blocked and a
    # 2x2 grid there is no other path.
    grid = grid_with_blocks({(0, 1), (1, 0)}, n_rows=2, n_cols=2)
    path, _ = a_star(grid, (0, 0), (1, 1), allow_diagonal=True)
    assert path is None


def test_diagonal_shortcut_when_safe() -> None:
    grid = blank_grid(3, 3)
    path, _ = a_star(grid, (0, 0), (2, 2), allow_diagonal=True)
    assert path == [(0, 0), (1, 1), (2, 2)]


def test_path_reconstruction_is_contiguous() -> None:
    grid = grid_with_blocks({(1, 1), (1, 2), (1, 3)})
    path, _ = a_star(grid, (0, 0), (2, 4), allow_diagonal=True)
    assert path is not None
    for (r1, c1), (r2, c2) in zip(path, path[1:]):
        assert max(abs(r1 - r2), abs(c1 - c2)) == 1


def test_determinism() -> None:
    grid = grid_with_blocks({(1, 1), (2, 1), (3, 1)})
    first = a_star(grid, (0, 0), (4, 4), allow_diagonal=True)
    for _ in range(25):
        assert a_star(grid, (0, 0), (4, 4), allow_diagonal=True) == first
