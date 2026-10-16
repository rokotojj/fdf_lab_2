"""Чтение файла карты .fdf.

Парсер ничего не печатает и не завершает программу: при ошибке он бросает
MapFormatError, а что сказать пользователю, решает main.py.
"""

import string
from pathlib import Path

from fdf.errors import MapFormatError
from fdf.model import Map, Point

__all__ = ["MapFormatError", "parse_map", "parse_value"]

BOM = b"\xef\xbb\xbf"  # метка UTF-8 в начале файла, её добавляет Блокнот


def is_integer(text: str) -> bool:
    """Целое число из цифр 0-9, можно с минусом."""
    digits = text.removeprefix("-")
    return digits.isascii() and digits.isdigit()


def is_color(text: str) -> bool:
    """0x и от 1 до 6 шестнадцатеричных цифр: 0xFF0000, 0xff, 0Xff00."""
    digits = text[2:]
    return (
        text[:2] in ("0x", "0X")
        and 1 <= len(digits) <= 6
        and all(c in string.hexdigits for c in digits)
    )


def parse_value(text: str, line: int = 1, column: int = 1) -> tuple[int, str | None]:
    """Одно значение карты: "5" -> (5, None), "2,0xff" -> (2, "#0000FF").

    line и column нужны только для текста ошибки.
    """
    height, comma, color = text.partition(",")
    if not is_integer(height):
        raise MapFormatError(line, column, f"'{height}' — не целое число")
    if not comma:
        return int(height), None
    if not is_color(color):
        raise MapFormatError(line, column, f"'{color}' — неверный цвет, нужно 0xRRGGBB")
    return int(height), f"#{int(color, 16):06X}"


def parse_map(path: str | Path) -> Map:
    """Читает карту из файла.

    Если файла нет - OSError (его разбирает main.py), ошибка формата - MapFormatError.
    """
    points: list[Point] = []
    width = height = 0
    blank = 0  # номер первой пустой строки; после неё карта продолжаться не может

    lines = Path(path).read_bytes().removeprefix(BOM).splitlines()
    for number, raw in enumerate(lines, start=1):
        try:
            tokens = raw.decode("utf-8").split()
        except UnicodeDecodeError as error:
            raise MapFormatError(number, 1, "это не текст в кодировке UTF-8") from error

        if not tokens:
            blank = blank or number
            continue
        if blank:
            raise MapFormatError(blank, 1, "пустая строка внутри карты")
        if height and len(tokens) != width:
            column = min(len(tokens), width) + 1  # первая лишняя или недостающая колонка
            raise MapFormatError(number, column, f"значений {len(tokens)}, а нужно {width}")

        width = len(tokens)
        for x, token in enumerate(tokens):
            z, color = parse_value(token, number, x + 1)
            points.append(Point(x, height, z, color))
        height += 1

    if not height:
        raise MapFormatError(1, 1, "файл пуст")
    return Map(width, height, points)
