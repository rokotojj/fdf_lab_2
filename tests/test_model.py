import pytest

from fdf.model import Map, Point


def grid(width: int, height: int) -> Map:
    """Карта, где высота точки равна x * y."""
    return Map(width, height, [Point(x, y, x * y) for y in range(height) for x in range(width)])


def test_len() -> None:
    assert len(grid(4, 3)) == 12


def test_for_loop_goes_row_by_row() -> None:
    assert [(p.x, p.y) for p in grid(3, 2)] == [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1)]


def test_getitem() -> None:
    assert grid(4, 3)[3, 2] == Point(3, 2, 6)


def test_getitem_outside_map() -> None:
    with pytest.raises(IndexError):
        grid(4, 3)[4, 0]


def test_wrong_number_of_points() -> None:
    with pytest.raises(ValueError):
        Map(2, 2, [Point(0, 0, 0)])


def test_height_range() -> None:
    m = grid(4, 3)
    assert (m.z_min, m.z_max) == (0, 6)


@pytest.mark.parametrize(
    ("x", "y", "expected"),
    [
        (0, 0, [(1, 0), (0, 1)]),  # левый верхний угол
        (2, 0, [(2, 1)]),  # правый верхний: справа никого
        (0, 2, [(1, 2)]),  # левый нижний: снизу никого
        (2, 2, []),  # правый нижний
    ],
)
def test_neighbors_of_corners(x: int, y: int, expected: list[tuple[int, int]]) -> None:
    m = grid(3, 3)
    assert [(p.x, p.y) for p in m.neighbors(m[x, y])] == expected


def test_every_edge_once() -> None:
    m = grid(4, 3)
    edges = list(m.edges())
    assert len(edges) == len(set(edges)) == 3 * 3 + 4 * 2  # горизонтальные + вертикальные


def test_repr() -> None:
    assert repr(grid(2, 3)) == "Map(2x3, z=0..2)"
