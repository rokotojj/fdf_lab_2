"""Запуск: python main.py <карта.fdf>"""

import sys

from fdf.errors import FdfError
from fdf.parser import parse_map


def fail(message: str) -> int:
    print(f"fdf: {message}", file=sys.stderr)
    return 1


def main(args: list[str]) -> int:
    """Возвращает код завершения: 0 - успех, 1 - ошибка файла, 2 - неверные аргументы."""
    if len(args) != 1:
        print("использование: python main.py <карта.fdf>", file=sys.stderr)
        return 2
    path = args[0]

    try:
        fdf_map = parse_map(path)
    except FileNotFoundError:
        return fail(f"{path}: файл не найден")
    except OSError as error:  # нет прав, это папка и т. п.
        return fail(f"{path}: не удалось прочитать ({error.strerror or error})")
    except FdfError as error:
        return fail(f"{path}: {error}")

    from fdf.app import App  # tkinter нужен только здесь: тесты main() работают без него

    try:
        App(fdf_map, f"FdF - {path}").run()
    except FdfError as error:
        return fail(str(error))
    except KeyboardInterrupt:  # Ctrl+C в консоли - просто выход, без traceback
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
