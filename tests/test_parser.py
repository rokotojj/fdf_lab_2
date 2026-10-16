from pathlib import Path

import pytest

from fdf.errors import FdfError, MapFormatError
from fdf.model import Map
from fdf.parser import parse_map, parse_value


def test_elem_size(elem: Map) -> None:
    assert (elem.width, elem.height) == (5, 5)


def test_elem_center_is_highest(elem: Map) -> None:
    assert elem[2, 2].z == 5 == elem.z_max


def test_points_know_their_place(elem: Map) -> None:
    for i, p in enumerate(elem):
        assert (p.x, p.y) == (i % 5, i // 5)
    assert elem[1, 2].z == 2  # третья строка файла, второе число


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("7", (7, None)),
        ("-3", (-3, None)),
        ("2,0xFF8800", (2, "#FF8800")),
        ("1,0xff", (1, "#0000FF")),
        ("0,0XfF00", (0, "#00FF00")),
    ],
)
def test_parse_value(text: str, expected: tuple[int, str | None]) -> None:
    assert parse_value(text) == expected


@pytest.mark.parametrize("text", ["x", "1.5", "--1", "+", "", "²", "5,", "5,red", "5,0x", "5,ff"])
def test_parse_value_rejects(text: str) -> None:
    with pytest.raises(MapFormatError):
        parse_value(text)


@pytest.mark.parametrize(
    ("name", "line", "column"),
    [
        ("empty.fdf", 1, 1),
        ("not_int.fdf", 2, 3),
        ("ragged.fdf", 3, 5),
        ("bad_color.fdf", 2, 2),
        ("long_color.fdf", 2, 2),
        ("empty_line.fdf", 4, 1),
    ],
)
def test_bad_maps(maps: Path, name: str, line: int, column: int) -> None:
    with pytest.raises(MapFormatError) as caught:
        parse_map(maps / "bad" / name)
    assert (caught.value.line, caught.value.column) == (line, column)
    assert str(caught.value).startswith(f"строка {line}, колонка {column}: ")


def test_message_from_task(maps: Path) -> None:
    with pytest.raises(MapFormatError, match="строка 2, колонка 3: 'x' — не целое число"):
        parse_map(maps / "bad" / "not_int.fdf")


def test_format_error_is_fdf_error() -> None:
    assert issubclass(MapFormatError, FdfError)


def test_missing_file(maps: Path) -> None:
    with pytest.raises(OSError):
        parse_map(maps / "nothing_here.fdf")


def test_empty_lines_at_the_end(tmp_path: Path) -> None:
    path = tmp_path / "map.fdf"
    path.write_text("1 2\n3 4\n\n  \n", encoding="utf-8")
    assert len(parse_map(path)) == 4


def test_notepad_file(tmp_path: Path) -> None:
    path = tmp_path / "map.fdf"
    path.write_bytes(b"\xef\xbb\xbf1 2\r\n3 4\r\n")  # BOM и переводы строк Windows
    assert parse_map(path)[1, 1].z == 4


def test_binary_file(tmp_path: Path) -> None:
    path = tmp_path / "map.fdf"
    path.write_bytes(b"0 0\n0 \xff\n")
    with pytest.raises(MapFormatError) as caught:
        parse_map(path)
    assert caught.value.line == 2


def test_colors_in_file(maps: Path) -> None:
    peak = parse_map(maps / "peak.fdf")
    assert peak[5, 5].color == "#FF0000"  # вершина
    assert peak[0, 0].color == "#0000FF"  # край, записан коротко: 0xff
    assert peak[3, 2].color is None
