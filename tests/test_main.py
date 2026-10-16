from pathlib import Path

import pytest

from main import main


@pytest.mark.parametrize("args", [[], ["one.fdf", "two.fdf"]])
def test_wrong_arguments(args: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert main(args) == 2
    assert "использование" in capsys.readouterr().err


def test_missing_file(maps: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(maps / "nothing_here.fdf")]) == 1
    assert "файл не найден" in capsys.readouterr().err


def test_folder_instead_of_file(maps: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(maps)]) == 1
    assert "fdf:" in capsys.readouterr().err


def test_bad_map(maps: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(maps / "bad" / "ragged.fdf")]) == 1
    assert "строка 3, колонка 5" in capsys.readouterr().err
