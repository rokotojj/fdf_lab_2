"""Окно на tkinter. Это единственный модуль, который знает про графику."""

import math
import tkinter as tk
from collections.abc import Callable

from fdf.errors import FdfError
from fdf.model import Map
from fdf.projection import Camera, height_color, lerp_color

BG = "#14161A"
TEXT = "#8B93A1"
FONT = "TkFixedFont"
SIZE = (1000, 700)
PAN = 25  # сдвиг стрелками, px
ZOOM = 1.15  # масштаб за один щелчок колеса
Z_STEP = 0.25  # шаг z_scale для клавиш + и -
ANGLE_STEP = math.radians(5)  # шаг угла для PageUp и PageDown
MOUSE_TURN = math.radians(0.4)  # поворот на 1 px движения мыши
SEGMENT = 8  # примерная длина кусочка градиента, px
MIN_SEGMENTS, MAX_SEGMENTS = 8, 16  # на столько кусочков делится ребро (п. 8.1 задания)
HELP = (
    "ЛКМ: вращение | ПКМ, стрелки: сдвиг | колесо: масштаб | Home: сброс | Esc: выход\n"
    "+/-: высота | PgUp/PgDn: угол | пробел: вид сверху"
)


class App:
    """Окно с каркасом карты."""

    def __init__(self, fdf_map: Map, title: str = "FdF") -> None:
        try:
            self.root = tk.Tk()
        except tk.TclError as error:  # например, нет экрана
            raise FdfError(f"не удалось открыть окно: {error}") from error
        self.root.title(title)
        self.map = fdf_map
        self.camera = Camera()
        # цвет точки: из файла, а если его нет - по высоте; от вида не зависит, считаем один раз
        self.colors = [
            p.color or height_color(p.z, fdf_map.z_min, fdf_map.z_max) for p in fdf_map
        ]
        self.width, self.height = SIZE
        self.mouse = (0, 0)  # где была мышь при прошлом событии

        self.canvas = tk.Canvas(
            self.root, width=self.width, height=self.height, background=BG, highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.on_resize)
        self.root.bind("<Escape>", lambda _event: self.root.destroy())
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

        # клавиша -> действие; после любого действия карта перерисовывается
        self.keys: dict[str, Callable[[], None]] = {
            "Left": lambda: self.camera.move(-PAN, 0),
            "Right": lambda: self.camera.move(PAN, 0),
            "Up": lambda: self.camera.move(0, -PAN),
            "Down": lambda: self.camera.move(0, PAN),
            "Home": self.reset,
            "plus": lambda: self.add_height(Z_STEP),
            "equal": lambda: self.add_height(Z_STEP),  # та же клавиша, что +, но без Shift
            "KP_Add": lambda: self.add_height(Z_STEP),
            "minus": lambda: self.add_height(-Z_STEP),
            "KP_Subtract": lambda: self.add_height(-Z_STEP),
            "Prior": lambda: self.add_angle(ANGLE_STEP),  # PageUp
            "Next": lambda: self.add_angle(-ANGLE_STEP),  # PageDown
            "space": self.toggle_top_view,
        }
        self.root.bind("<Key>", self.on_key)
        self.root.bind("<MouseWheel>", self.on_wheel)  # Windows, macOS
        self.root.bind("<Button-4>", self.on_wheel)  # Linux: колесо вверх
        self.root.bind("<Button-5>", self.on_wheel)  # Linux: колесо вниз
        self.root.bind("<ButtonPress-1>", self.grab)
        self.root.bind("<ButtonPress-3>", self.grab)
        self.root.bind("<B1-Motion>", self.on_rotate)  # левая кнопка зажата
        self.root.bind("<B3-Motion>", self.on_pan)  # правая кнопка зажата

    def run(self) -> None:
        self.root.mainloop()

    def on_resize(self, event: "tk.Event[tk.Canvas]") -> None:
        """Окно изменило размер: заново вписываем карту."""
        self.width, self.height = event.width, event.height
        self.camera.fit(self.map, self.width, self.height)
        self.draw()

    def on_key(self, event: "tk.Event[tk.Misc]") -> None:
        action = self.keys.get(event.keysym)
        if action:
            action()
            self.draw()

    def on_wheel(self, event: "tk.Event[tk.Misc]") -> None:
        """Колесо: масштаб относительно центра окна, изображение не смещается."""
        closer = event.delta > 0 or event.num == 4
        self.camera.zoom(ZOOM if closer else 1 / ZOOM, self.width / 2, self.height / 2)
        self.draw()

    def grab(self, event: "tk.Event[tk.Misc]") -> None:
        self.mouse = (event.x, event.y)

    def mouse_step(self, event: "tk.Event[tk.Misc]") -> tuple[int, int]:
        """На сколько сдвинулась мышь с прошлого события."""
        dx, dy = event.x - self.mouse[0], event.y - self.mouse[1]
        self.mouse = (event.x, event.y)
        return dx, dy

    def on_rotate(self, event: "tk.Event[tk.Misc]") -> None:
        """Как камера в играх: влево-вправо - поворот карты, вверх-вниз - наклон."""
        dx, dy = self.mouse_step(event)
        self.camera.turn(dx * MOUSE_TURN, dy * MOUSE_TURN)
        self.camera.center(self.map, self.width, self.height)  # крутится на месте
        self.draw()

    def on_pan(self, event: "tk.Event[tk.Misc]") -> None:
        dx, dy = self.mouse_step(event)
        self.camera.move(dx, dy)
        self.canvas.move("map", dx, dy)  # двигаем готовые линии - быстрее, чем рисовать заново

    def add_height(self, step: float) -> None:
        self.camera.z_scale += step

    def add_angle(self, step: float) -> None:
        self.camera.angle += step
        self.camera.center(self.map, self.width, self.height)  # карта остаётся по центру

    def toggle_top_view(self) -> None:
        self.camera.top_view = not self.camera.top_view
        self.camera.fit(self.map, self.width, self.height)  # у вида сверху другие размеры

    def reset(self) -> None:
        """Вид как при запуске."""
        self.camera = Camera()
        self.camera.fit(self.map, self.width, self.height)

    def draw(self) -> None:
        """Каркас: рёбра к соседям справа и снизу, с переходом цвета от точки к точке."""
        self.canvas.delete("all")
        screen = self.camera.project_all(self.map)
        for a, b in self.map.edges():
            self.draw_edge(screen[a], screen[b], self.colors[a], self.colors[b])
        self.draw_labels()

    def draw_edge(
        self, a: tuple[float, float], b: tuple[float, float], color_a: str, color_b: str
    ) -> None:
        (x1, y1), (x2, y2) = a, b
        if color_a == color_b:
            self.canvas.create_line(x1, y1, x2, y2, fill=color_a, tags="map")
            return
        # tkinter рисует отрезок одним цветом, поэтому ребро режем на n кусочков (от 8 до 16,
        # чем длиннее ребро на экране, тем больше) и k-й кусочек красим цветом
        # C = (1 - t) * A + t * B, где t = k / n.
        n = min(MAX_SEGMENTS, max(MIN_SEGMENTS, int(math.dist(a, b) / SEGMENT)))
        for k in range(n):
            t0, t1 = k / n, (k + 1) / n
            self.canvas.create_line(
                x1 + (x2 - x1) * t0,
                y1 + (y2 - y1) * t0,
                x1 + (x2 - x1) * t1,
                y1 + (y2 - y1) * t1,
                fill=lerp_color(color_a, color_b, t0),
                tags="map",
            )

    def draw_labels(self) -> None:
        cam = self.camera
        info = (
            f"{self.map.width}x{self.map.height} | z {self.map.z_min}..{self.map.z_max}"
            f" | высота x{cam.z_scale:g} | угол {math.degrees(cam.angle):.0f}°"
            f" | вращение {round(math.degrees(cam.rotation)) % 360}°"
            f" | наклон {math.degrees(cam.elevation):.0f}°"
        )
        if cam.top_view:
            info += " | вид сверху"
        self.canvas.create_text(10, 10, text=HELP, anchor="nw", fill=TEXT, font=FONT)
        self.canvas.create_text(10, self.height - 10, text=info, anchor="sw", fill=TEXT, font=FONT)
