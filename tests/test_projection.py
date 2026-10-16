import math
from pathlib import Path

import pytest

from fdf.model import Map, Point
from fdf.parser import parse_map
from fdf.projection import Camera

W, H = 800, 600
COS30, SIN30 = math.cos(math.radians(30)), math.sin(math.radians(30))


def screen_box(camera: Camera, fdf_map: Map) -> tuple[float, float, float, float]:
    points = camera.project_all(fdf_map)
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    return min(xs), min(ys), max(xs), max(ys)


def test_origin_stays_at_origin() -> None:
    assert Camera().project(Point(0, 0, 0)) == (0, 0)


def test_higher_point_is_higher_on_screen() -> None:
    _, y = Camera().project(Point(0, 0, 1))
    assert y < 0


def test_formula_from_task() -> None:
    x, y = Camera().project(Point(4, 1, 2))
    assert x == pytest.approx((4 - 1) * COS30)
    assert y == pytest.approx((4 + 1) * SIN30 - 2)


def test_scale_and_offset() -> None:
    camera = Camera(scale=10, offset_x=100, offset_y=50)
    assert camera.project(Point(0, 0, 1)) == (100, 40)


def test_project_all_matches_project(elem: Map) -> None:
    camera = Camera(scale=3, offset_x=7)
    assert camera.project_all(elem) == [camera.project(p) for p in elem]


@pytest.mark.parametrize("name", ["elem.fdf", "42.fdf", "flat.fdf"])
def test_fit_keeps_map_inside_window(maps: Path, name: str) -> None:
    fdf_map = parse_map(maps / name)
    camera = Camera()
    camera.fit(fdf_map, W, H)
    x0, y0, x1, y1 = screen_box(camera, fdf_map)
    assert 0 <= x0 <= x1 <= W
    assert 0 <= y0 <= y1 <= H


def test_fit_puts_map_in_the_middle(maps: Path) -> None:
    fdf_map = parse_map(maps / "42.fdf")
    camera = Camera()
    camera.fit(fdf_map, W, H)
    x0, y0, x1, y1 = screen_box(camera, fdf_map)
    assert ((x0 + x1) / 2, (y0 + y1) / 2) == pytest.approx((W / 2, H / 2))


def test_flat_map_is_symmetric(maps: Path) -> None:
    fdf_map = parse_map(maps / "flat.fdf")
    camera = Camera()
    camera.fit(fdf_map, W, H)
    top_x, _ = camera.project(fdf_map[0, 0])
    bottom_x, _ = camera.project(fdf_map[fdf_map.width - 1, fdf_map.height - 1])
    assert top_x == pytest.approx(W / 2) == pytest.approx(bottom_x)


def test_fit_single_point() -> None:
    camera = Camera()
    camera.fit(Map(1, 1, [Point(0, 0, 9)]), W, H)
    assert camera.project(Point(0, 0, 9)) == pytest.approx((W / 2, H / 2))


def test_zoom_keeps_point_under_cursor() -> None:
    camera = Camera(scale=10, offset_x=100, offset_y=50)
    point = Point(3, 1, 2)
    cursor = camera.project(point)
    camera.zoom(2, *cursor)
    assert camera.scale == 20
    assert camera.project(point) == pytest.approx(cursor)


def test_zoom_changes_distances() -> None:
    camera = Camera(scale=10)
    camera.zoom(1.5, 400, 300)
    (x1, _), (x2, _) = camera.project_all([Point(0, 0, 0), Point(1, 0, 0)])
    assert x2 - x1 == pytest.approx(15 * COS30)


def test_move() -> None:
    camera = Camera()
    camera.move(20, -10)
    assert camera.project(Point(0, 0, 0)) == (20, -10)


@pytest.mark.parametrize(("z_scale", "y"), [(0, 0), (1, -4), (2.5, -10), (-1, 4)])
def test_z_scale(z_scale: float, y: float) -> None:
    assert Camera(z_scale=z_scale).project(Point(0, 0, 4))[1] == pytest.approx(y)


def test_top_view_ignores_height() -> None:
    camera = Camera(top_view=True)
    assert camera.project(Point(3, 2, 100)) == camera.project(Point(3, 2, -5)) == (3, 2)


def test_top_view_fit(maps: Path) -> None:
    fdf_map = parse_map(maps / "42.fdf")
    camera = Camera(top_view=True)
    camera.fit(fdf_map, W, H)
    x0, y0, x1, y1 = screen_box(camera, fdf_map)
    assert 0 <= x0 <= x1 <= W
    assert 0 <= y0 <= y1 <= H


def test_zero_angle_is_side_view() -> None:
    camera = Camera(angle=0)
    assert camera.project(Point(3, 1, 0)) == pytest.approx((2, 0))
    assert camera.project(Point(3, 1, 2)) == pytest.approx((2, -2))


@pytest.mark.parametrize("degrees", [0, 15, 45, 60, 90])
def test_center_after_angle_change(maps: Path, degrees: float) -> None:
    fdf_map = parse_map(maps / "42.fdf")
    camera = Camera()
    camera.fit(fdf_map, W, H)
    camera.angle = math.radians(degrees)
    camera.center(fdf_map, W, H)
    x0, y0, x1, y1 = screen_box(camera, fdf_map)
    assert ((x0 + x1) / 2, (y0 + y1) / 2) == pytest.approx((W / 2, H / 2))


def test_rotation_by_quarter_turn() -> None:
    # поворот на 90 градусов: (1, 0) переходит в (0, 1), а (0, 1) - в (-1, 0)
    turned, plain = Camera(rotation=math.pi / 2), Camera()
    assert turned.project(Point(1, 0, 5)) == pytest.approx(plain.project(Point(0, 1, 5)))
    assert turned.project(Point(0, 1, 0)) == pytest.approx(plain.project(Point(-1, 0, 0)))


def test_full_turn_changes_nothing() -> None:
    p = Point(3, 1, 2)
    assert Camera(rotation=2 * math.pi).project(p) == pytest.approx(Camera().project(p))


def test_rotation_does_not_touch_height() -> None:
    assert Camera(rotation=1.0).project(Point(0, 0, 4)) == pytest.approx((0, -4))


def test_view_from_above_hides_height() -> None:
    camera = Camera(elevation=math.pi / 2)
    assert camera.project(Point(2, 1, 0)) == pytest.approx(camera.project(Point(2, 1, 7)))


@pytest.mark.parametrize(("d_elevation", "degrees"), [(-1.0, 5), (1.0, 90), (0.0, 35.26)])
def test_turn_keeps_elevation_in_limits(d_elevation: float, degrees: float) -> None:
    camera = Camera()
    camera.turn(0.5, d_elevation)
    assert camera.rotation == 0.5
    assert math.degrees(camera.elevation) == pytest.approx(degrees, abs=0.01)


@pytest.mark.parametrize("degrees", [45, 90, 180, 270])
def test_center_after_rotation(maps: Path, degrees: float) -> None:
    fdf_map = parse_map(maps / "42.fdf")
    camera = Camera()
    camera.fit(fdf_map, W, H)
    camera.rotation = math.radians(degrees)
    camera.center(fdf_map, W, H)
    x0, y0, x1, y1 = screen_box(camera, fdf_map)
    assert ((x0 + x1) / 2, (y0 + y1) / 2) == pytest.approx((W / 2, H / 2))
