"""Проекция точек карты на экран.

Формула из задания (раздел 4):
    x' = (x - y) * cos(angle)
    y' = (x + y) * sin(angle) - z * z_scale
    X = x' * scale + offset_x,  Y = y' * scale + offset_y
Ось Y экрана направлена вниз, поэтому высота вычитается.

Формула линейная, значит её целиком задают шесть коэффициентов - матрица 2x3:
    x' = ax*x + bx*y + cx*z,  y' = ay*x + by*y + cy*z.
Матрица считается один раз на всю перерисовку, а не для каждой точки.

Мышью карту можно вращать, как камеру в игре:
    rotation  - поворот карты вокруг вертикали до проекции:
                xr = x*cos(r) - y*sin(r),  yr = x*sin(r) + y*cos(r);
    elevation - наклон камеры. Формула задания - это взгляд под углом ~35.26 градуса
                (классическая изометрия, sin(e) = tan(30)). При другом наклоне глубина
                умножается на sin(e) / sin(35.26), высота - на cos(e) / cos(35.26).
При rotation = 0 и elevation = ISO_ELEVATION получается ровно формула задания.
"""

import math
from collections.abc import Iterable
from dataclasses import dataclass, replace

from fdf.model import Map, Point

Row = tuple[float, float, float]

FIT_MARGIN = 0.9  # карта занимает 90 % окна
ISO_ELEVATION = math.asin(math.tan(math.radians(30)))  # ~35.26 градуса
MIN_ELEVATION = math.radians(5)  # почти сбоку
MAX_ELEVATION = math.radians(90)  # строго сверху

# Цвета по высоте, как на физической карте: вода, низина, равнина, холмы, горы, снег.
PALETTE = ["#2F6FB5", "#2A9D8F", "#8AB17D", "#E9C46A", "#C07A3A", "#F2F2F2"]


def lerp_color(a: str, b: str, t: float) -> str:
    """Цвет между a (t = 0) и b (t = 1): C = (1 - t) * A + t * B по каждому каналу.

    Целиком число 0xRRGGBB смешивать нельзя - каналы перемешаются и выйдут чужие цвета.
    """
    start = bytes.fromhex(a[1:])  # "#FF8000" -> байты 255, 128, 0
    end = bytes.fromhex(b[1:])
    mixed = bytes(round(s + (e - s) * t) for s, e in zip(start, end, strict=True))
    return "#" + mixed.hex().upper()


def height_color(z: float, z_min: float, z_max: float) -> str:
    """Цвет по высоте: z_min - первый цвет PALETTE, z_max - последний, между ними плавно."""
    if z_max == z_min:
        return PALETTE[0]
    pos = (z - z_min) / (z_max - z_min) * (len(PALETTE) - 1)  # 2.5 = между 2-м и 3-м
    i = min(int(pos), len(PALETTE) - 2)
    return lerp_color(PALETTE[i], PALETTE[i + 1], pos - i)


@dataclass
class Camera:
    """Параметры вида. Карта не меняется, меняется только то, как на неё смотрят."""

    scale: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    z_scale: float = 1.0
    angle: float = math.radians(30)  # угол осей x и y к горизонтали
    top_view: bool = False  # вид сверху: X = x, Y = y, высота не видна
    rotation: float = 0.0  # поворот карты мышью вокруг вертикали
    elevation: float = ISO_ELEVATION  # наклон камеры мышью

    def matrix(self) -> tuple[Row, Row]:
        """Коэффициенты (ax, bx, cx) и (ay, by, cy) для текущих настроек."""
        if self.top_view:
            return (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)
        c, s = math.cos(self.rotation), math.sin(self.rotation)
        depth = math.sin(self.elevation) / math.sin(ISO_ELEVATION)
        rise = math.cos(self.elevation) / math.cos(ISO_ELEVATION)
        kx = math.cos(self.angle)
        ky = math.sin(self.angle) * depth
        # x' = (xr - yr) * kx,  y' = (xr + yr) * ky - z * z_scale * rise
        return (
            ((c - s) * kx, -(c + s) * kx, 0.0),
            ((c + s) * ky, (c - s) * ky, -self.z_scale * rise),
        )

    def project_all(self, points: Iterable[Point]) -> list[tuple[float, float]]:
        """Экранные координаты (X, Y) для каждой точки."""
        (ax, bx, cx), (ay, by, cy) = self.matrix()
        k, dx, dy = self.scale, self.offset_x, self.offset_y
        return [
            ((ax * p.x + bx * p.y + cx * p.z) * k + dx, (ay * p.x + by * p.y + cy * p.z) * k + dy)
            for p in points
        ]

    def project(self, point: Point) -> tuple[float, float]:
        return self.project_all([point])[0]

    def bounds(self, fdf_map: Map) -> tuple[float, float, float, float]:
        """Прямоугольник вокруг карты при scale = 1 и без сдвига: x0, y0, x1, y1."""
        flat = replace(self, scale=1.0, offset_x=0.0, offset_y=0.0).project_all(fdf_map)
        xs = [x for x, _ in flat]
        ys = [y for _, y in flat]
        return min(xs), min(ys), max(xs), max(ys)

    def center(self, fdf_map: Map, width: float, height: float) -> None:
        """Сдвигает карту так, чтобы центр её прямоугольника совпал с центром окна."""
        x0, y0, x1, y1 = self.bounds(fdf_map)
        self.offset_x = width / 2 - (x0 + x1) / 2 * self.scale
        self.offset_y = height / 2 - (y0 + y1) / 2 * self.scale

    def fit(self, fdf_map: Map, width: float, height: float) -> None:
        """Подбирает масштаб (карта - 90 % окна) и ставит карту в центр."""
        x0, y0, x1, y1 = self.bounds(fdf_map)
        # у карты из одной точки ширина и высота нулевые - берём 1, чтобы не делить на 0
        self.scale = FIT_MARGIN * min(width / ((x1 - x0) or 1), height / ((y1 - y0) or 1))
        self.center(fdf_map, width, height)

    def zoom(self, factor: float, x: float, y: float) -> None:
        """Масштаб в factor раз вокруг точки экрана (x, y): она остаётся на месте."""
        self.scale *= factor
        self.offset_x = x - (x - self.offset_x) * factor
        self.offset_y = y - (y - self.offset_y) * factor

    def move(self, dx: float, dy: float) -> None:
        self.offset_x += dx
        self.offset_y += dy

    def turn(self, d_rotation: float, d_elevation: float) -> None:
        """Вращение мышью. Наклон не выходит за пределы от 5 до 90 градусов."""
        self.rotation += d_rotation
        elevation = self.elevation + d_elevation
        self.elevation = min(max(elevation, MIN_ELEVATION), MAX_ELEVATION)
