import pytest

from fdf.projection import PALETTE, height_color, lerp_color


@pytest.mark.parametrize(
    ("t", "expected"),
    [(0, "#FF0000"), (0.25, "#BF0040"), (0.5, "#800080"), (1, "#0000FF")],
)
def test_lerp_red_to_blue(t: float, expected: str) -> None:
    assert lerp_color("#FF0000", "#0000FF", t) == expected


def test_lerp_each_channel_separately() -> None:
    assert lerp_color("#000000", "#204060", 0.5) == "#102030"


def test_lerp_same_color() -> None:
    assert lerp_color("#2A9D8F", "#2A9D8F", 0.7) == "#2A9D8F"


@pytest.mark.parametrize(("z", "index"), [(0, 0), (2, 1), (4, 2), (6, 3), (8, 4), (10, 5)])
def test_height_hits_palette_colors(z: int, index: int) -> None:
    assert height_color(z, 0, 10) == PALETTE[index]


def test_height_with_negative_values() -> None:
    assert height_color(-5, -5, 5) == PALETTE[0]
    assert height_color(5, -5, 5) == PALETTE[-1]


def test_height_on_flat_map() -> None:
    assert height_color(3, 3, 3) == PALETTE[0]
