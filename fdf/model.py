"""Точка и карта высот."""

from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    """x - колонка, y - строка файла, z - высота, color - "#RRGGBB" из файла или None."""

    x: int
    y: int
    z: int
    color: str | None = None


class Map:
    """Карта width x height.

    Точки хранятся одним списком, строка за строкой: точка (x, y) лежит
    по индексу y * width + x. Так проще обходить карту и строить рёбра.
    """

    def __init__(self, width: int, height: int, points: list[Point]) -> None:
        if len(points) != width * height:
            raise ValueError(f"нужно {width * height} точек, а передано {len(points)}")
        self.width = width
        self.height = height
        self.points = points
        heights = [p.z for p in points]
        self.z_min = min(heights, default=0)
        self.z_max = max(heights, default=0)

    def __len__(self) -> int:
        return len(self.points)

    def __iter__(self) -> Iterator[Point]:
        return iter(self.points)

    def __getitem__(self, xy: tuple[int, int]) -> Point:
        x, y = xy
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(f"на карте нет точки ({x}, {y})")
        return self.points[y * self.width + x]

    def __repr__(self) -> str:
        return f"Map({self.width}x{self.height}, z={self.z_min}..{self.z_max})"

    def _next_indexes(self, x: int, y: int) -> list[int]:
        """Индексы соседей справа и снизу."""
        i = y * self.width + x
        result = []
        if x + 1 < self.width:
            result.append(i + 1)
        if y + 1 < self.height:
            result.append(i + self.width)
        return result

    def neighbors(self, point: Point) -> list[Point]:
        """Соседи справа и снизу.

        Левых и верхних не берём: тогда каждое ребро строилось бы дважды.
        """
        return [self.points[j] for j in self._next_indexes(point.x, point.y)]

    def edges(self) -> Iterator[tuple[int, int]]:
        """Все рёбра каркаса - пары индексов точек в self.points."""
        for i, p in enumerate(self.points):
            for j in self._next_indexes(p.x, p.y):
                yield i, j
