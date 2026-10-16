from pathlib import Path

import pytest

from fdf.model import Map
from fdf.parser import parse_map


@pytest.fixture
def maps() -> Path:
    """Папка maps/ проекта."""
    return Path(__file__).resolve().parent.parent / "maps"


@pytest.fixture
def elem(maps: Path) -> Map:
    return parse_map(maps / "elem.fdf")
