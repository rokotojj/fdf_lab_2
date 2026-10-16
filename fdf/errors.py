"""Ошибки программы."""


class FdfError(Exception):
    """Общая ошибка FdF. main.py ловит её и печатает текст."""


class MapFormatError(FdfError):
    """Ошибка в файле карты. Помнит место: номер строки и колонки (считаются с 1)."""

    def __init__(self, line: int, column: int, reason: str) -> None:
        super().__init__(f"строка {line}, колонка {column}: {reason}")
        self.line = line
        self.column = column
