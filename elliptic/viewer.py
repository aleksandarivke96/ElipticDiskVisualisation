"""Interactive matplotlib view of the closed-disk model of elliptic geometry.

A tool palette on the left drives a `Construction`: place as many points as you
like, join them into lines, segments, perpendiculars and triangles, name the
points where lines cross, swap points for their polars - then drag any free
point and watch the whole thing follow.
"""

from __future__ import annotations

import numpy as np
from matplotlib.patches import Circle
from matplotlib.widgets import Button

from . import gclc
from . import geometry as geo
from .model import (LINE, PALETTE, PERPENDICULAR, POLAR, SEGMENT, Construction,
                    Line, Point, Triangle)

PICK_POINT_PX = 13.0
PICK_LINE_PX = 9.0

COL_DISK = "#3f4756"
COL_INK = "#1f2430"
COL_MUTED = "#6b7280"
COL_PANEL = "#eef0f4"
COL_PANEL_ON = "#c9d8ee"
COL_MEET = "#111827"

TOOLS = [
    ("point", "Point", "1", "click anywhere to drop a point"),
    ("line", "Line", "2", "click two points (or two empty spots) to join them"),
    ("segment", "Segment", "3", "click two points for the shortest path between them"),
    ("perp", "Perpendicular", "4", "click a point and a line, in either order"),
    ("triangle", "Triangle", "5", "click three points; the angles give the area"),
    ("meet", "Meet", "6", "click two lines to name the point where they cross"),
    ("dual", "Polar / Pole", "7", "click a point for its polar, a line for its pole"),
    ("move", "Move", "8", "drag a point; everything built on it follows"),
    ("delete", "Delete", "9", "click a point or a line; a triangle goes with its sides"),
]
TOGGLES = [
    ("labels", "Labels", "l"),
    ("poles", "Poles", "p"),
    ("meets", "Meets", "x"),
    ("rim", "Rim ends", "e"),
    ("plain", "Plain", "b"),  # black ink and line weights, as it will be exported
]
PLAIN_INK = "#111111"
PLAIN_FAINT = "#8a8f98"
ACTIONS = [("undo", "Undo", "u"), ("clear", "Clear", "c"),
           ("gclc", "Save GCLC", "g")]  # shift-G saves the same thing in plain black
DEFAULT_EXPORT = "construction.gcl"


class EllipticDiskViewer:
    """Palette-driven construction tool for the elliptic plane."""

    def __init__(self, samples: int = 512):
        import matplotlib.pyplot as plt

        self.samples = samples
        self.construction = Construction()
        self.tool = "point"
        self.color: str | None = None  # None = cycle through the palette
        self.flags = {"labels": True, "poles": False, "meets": True, "rim": True,
                      "plain": False}
        self.picked: list[Point | Line] = []  # objects a half-finished tool holds
        self.message = ""
        self._dragging: Point | None = None
        self._artists: list = []
        self._prompt = None  # the filename box, built the first time it is asked for
        self._plain_export = False

        self.fig = plt.figure(figsize=(11.2, 8.0))
        self.fig.canvas.manager.set_window_title("Elliptic geometry - closed disk model")
        self.fig.patch.set_facecolor("white")
        self.ax = self.fig.add_axes([0.255, 0.085, 0.72, 0.845])
        self._setup_disk()
        self._build_palette()

        self.status = self.fig.text(0.615, 0.045, "", ha="center", va="center",
                                    fontsize=10, family="monospace", color=COL_INK)
        for event, handler in (
            ("button_press_event", self._on_press),
            ("motion_notify_event", self._on_motion),
            ("button_release_event", self._on_release),
            ("key_press_event", self._on_key),
        ):
            self.fig.canvas.mpl_connect(event, handler)

        self._redraw()

    @property
    def pending(self) -> Point | Line | None:
        """The most recent half-finished pick, if the current tool is waiting."""
        return self.picked[-1] if self.picked else None

    # ------------------------------------------------------------------ setup

    def _setup_disk(self) -> None:
        ax = self.ax
        ax.set_aspect("equal")
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1.2, 1.2)
        ax.axis("off")

        self._face = Circle((0, 0), 1.0, fc="#f7f8fa", ec="none", zorder=0)
        ax.add_patch(self._face)
        ax.add_patch(
            Circle((0, 0), 1.0, fc="none", ec=COL_DISK, lw=2.0, ls=(0, (6, 3)), zorder=1)
        )
        ax.plot([0], [0], "+", color=COL_DISK, ms=7, alpha=0.5, zorder=1)

        ax.set_title("Closed disk model of the elliptic plane\n"
                     "opposite boundary points are the same point",
                     fontsize=12, pad=10, color=COL_INK)

    def _build_palette(self) -> None:
        """Buttons live in their own little axes down the left-hand side."""
        self.buttons: dict[str, Button] = {}
        x, w, h, gap = 0.025, 0.175, 0.032, 0.006
        y = 0.912

        y = self._palette_heading("TOOLS", x, y)
        for key, label, shortcut, _ in TOOLS:
            self._palette_button(key, f"{label}   [{shortcut}]", x, y, w, h,
                                 lambda k=key: self._set_tool(k))
            y -= h + gap

        y = self._palette_heading("SHOW", x, y - 0.010)
        for key, label, shortcut in TOGGLES:
            self._palette_button(f"flag:{key}", f"{label}   [{shortcut}]", x, y, w, h * 0.82,
                                 lambda k=key: self._toggle(k))
            y -= h * 0.82 + gap

        y = self._palette_heading("COLOUR", x, y - 0.012)
        swatch = (w - 0.008 * 4) / 5
        for i, col in enumerate([None] + PALETTE[:9]):
            row, column = divmod(i, 5)
            self._swatch(col, x + column * (swatch + 0.008),
                         y - row * (swatch * 1.4 + 0.008), swatch, swatch * 1.4)
        y -= 2 * (swatch * 1.4 + 0.008) + 0.02

        y = self._palette_heading("EDIT", x, y)
        for key, label, shortcut in ACTIONS:
            self._palette_button(key, f"{label}   [{shortcut}]", x, y, w, h * 0.82,
                                 lambda k=key: self._action(k))
            y -= h * 0.82 + gap

    def _palette_heading(self, text: str, x: float, y: float) -> float:
        self.fig.text(x, y, text, fontsize=8, color=COL_MUTED,
                      fontweight="bold", va="center")
        return y - 0.028

    def _palette_button(self, key, label, x, y, w, h, callback) -> None:
        ax = self.fig.add_axes([x, y - h, w, h])
        button = Button(ax, label, color=COL_PANEL, hovercolor="#dde3ec")
        button.label.set_fontsize(9)
        button.label.set_color(COL_INK)
        button.on_clicked(lambda _event: callback())
        for spine in ax.spines.values():
            spine.set_color("#c4cad4")
        self.buttons[key] = button

    def _swatch(self, color, x, y, w, h) -> None:
        ax = self.fig.add_axes([x, y - h, w, h])
        button = Button(ax, "auto" if color is None else "",
                        color=color or "white", hovercolor=color or "#f0f0f0")
        button.label.set_fontsize(6.5)
        button.label.set_color(COL_MUTED)
        button.on_clicked(lambda _event, c=color: self._set_color(c))
        self.buttons[f"color:{color}"] = button

    # ------------------------------------------------------------------ palette state

    def _set_tool(self, tool: str) -> None:
        self.tool = tool
        self.picked.clear()
        self.message = ""
        self._redraw()

    def _toggle(self, flag: str) -> None:
        self.flags[flag] = not self.flags[flag]
        self._redraw()

    def _set_color(self, color: str | None) -> None:
        self.color = color
        self.message = f"colour: {color or 'auto'}"
        self._redraw()

    def _action(self, action: str) -> None:
        if action == "undo":
            removed = self.construction.undo()
            self.message = f"undid {self._describe(removed)}" if removed else "nothing to undo"
        elif action == "clear":
            self.construction.clear()
            self.message = "cleared"
        elif action == "gclc":
            self._ask_for_filename(self.flags["plain"])  # save what you can see
            return
        self.picked.clear()
        self._redraw()

    # ------------------------------------------------------------------ export

    def _ask_for_filename(self, plain: bool = False) -> None:
        """Open the little box that asks where the GCLC file should go."""
        if self._prompt is None:
            self._build_prompt()
        box, ax = self._prompt
        self._plain_export = plain
        box.set_val(DEFAULT_EXPORT)  # counts as a submit, so do it while the box
        ax.set_visible(True)         # is still put away and `_write_gclc` drops it
        box.set_active(True)
        box.label.set_text("save plain GCLC to  " if plain else "save GCLC to  ")
        box.begin_typing()
        self.message = ("plain, no colour - file name, then enter (esc cancels)" if plain
                        else "file name, then enter (esc cancels; G saves plain)")
        self._redraw()

    def _build_prompt(self) -> None:
        from matplotlib.widgets import TextBox

        ax = self.fig.add_axes([0.50, 0.48, 0.27, 0.05], zorder=20)  # over the disk
        box = TextBox(ax, "save GCLC to  ", initial=DEFAULT_EXPORT)
        box.label.set_fontsize(9)
        box.label.set_color(COL_INK)
        box.text_disp.set_fontsize(9)
        box.on_submit(self._write_gclc)
        ax.set_visible(False)
        box.set_active(False)
        self._prompt = (box, ax)

    def _close_prompt(self) -> None:
        if self._prompt is None:
            return
        box, ax = self._prompt
        # put the box away *first*: giving up the keyboard counts as a submit,
        # and cancelling must not write a file
        ax.set_visible(False)
        box.set_active(False)
        box.stop_typing()

    @property
    def _prompting(self) -> bool:
        return self._prompt is not None and self._prompt[1].get_visible()

    def _write_gclc(self, name: str) -> None:
        """Called when the box is submitted: write the file, or say why not."""
        if not self._prompting:  # a stale submit from a box already put away
            return
        self._close_prompt()
        try:
            path = gclc.export(self.construction, name, plain=self._plain_export)
        except (OSError, ValueError) as problem:
            self.message = f"could not write it: {problem}"
        else:
            how = "plain GCLC" if self._plain_export else "GCLC"
            counts = (f"{len(self.construction.points)} points, "
                      f"{len(self.construction.lines)} lines")
            self.message = f"wrote {path} for {how} - {counts}"
        self._redraw()

    def _refresh_palette(self) -> None:
        for key, *_ in TOOLS:
            self._paint(self.buttons[key], key == self.tool)
        for key, *_ in TOGGLES:
            self._paint(self.buttons[f"flag:{key}"], self.flags[key])
        for color in [None] + PALETTE[:9]:
            button = self.buttons[f"color:{color}"]
            selected = color == self.color
            for spine in button.ax.spines.values():
                spine.set_linewidth(2.4 if selected else 0.6)
                spine.set_color(COL_INK if selected else "#c4cad4")

    @staticmethod
    def _paint(button: Button, active: bool) -> None:
        button.color = COL_PANEL_ON if active else COL_PANEL
        button.ax.set_facecolor(button.color)
        button.label.set_fontweight("bold" if active else "normal")

    # ------------------------------------------------------------------ hit testing

    def _pixels(self, xy) -> np.ndarray:
        return self.ax.transData.transform(np.atleast_2d(xy))

    def _point_at(self, event) -> Point | None:
        best, best_d = None, PICK_POINT_PX
        for point in self.construction.points:
            xy = point.xy
            if xy is None:  # a derived point with nowhere to be right now
                continue
            px, py = self._pixels(xy)[0]
            d = float(np.hypot(px - event.x, py - event.y))
            if d <= best_d:
                best, best_d = point, d
        return best

    def _line_at(self, event) -> Line | None:
        best, best_d = None, PICK_LINE_PX
        for line in self.construction.lines:
            for path in self._paths(line):
                if len(path) < 2:
                    continue
                pixels = self._pixels(path)
                d = float(np.hypot(pixels[:, 0] - event.x, pixels[:, 1] - event.y).min())
                if d <= best_d:
                    best, best_d = line, d
        return best

    def _paths(self, line: Line) -> list[np.ndarray]:
        """Drawable pieces of a line, in disk coordinates.

        A segment is the arc between its two points and a perpendicular the arc
        down to its foot - either can come back in two pieces when the shortest
        route leaves the disk through the rim.
        """
        normal = line.normal
        if normal is None:
            return []
        if not line.is_partial:
            return [geo.line_points(normal, self.samples)]
        ends = line.endpoints()
        return [] if ends is None else geo.segment_paths(*ends, self.samples)

    # ------------------------------------------------------------------ events

    def _on_press(self, event) -> None:
        if self._prompting:  # clicking away from the box puts it away
            if event.inaxes is self._prompt[1]:
                return  # inside the box: let it place its cursor
            self._close_prompt()
            self.message = "cancelled"
            self._redraw()
            return
        if event.inaxes is not self.ax or event.xdata is None:
            return
        handler = {
            "point": self._press_point,
            "line": lambda e: self._press_join(e, LINE),
            "segment": lambda e: self._press_join(e, SEGMENT),
            "perp": self._press_perpendicular,
            "triangle": self._press_triangle,
            "meet": self._press_meet,
            "dual": self._press_dual,
            "move": self._press_move,
            "delete": self._press_delete,
        }[self.tool]
        handler(event)
        self._redraw()

    def _pick_point(self, event) -> Point:
        """The point clicked on, or a fresh one where the click landed."""
        return self._point_at(event) or self.construction.add_point(
            event.xdata, event.ydata, self.color)

    def _press_point(self, event) -> None:
        point = self.construction.add_point(event.xdata, event.ydata, self.color)
        self._dragging = point
        self.message = f"point {point.label}"

    def _press_join(self, event, kind: str) -> None:
        point = self._pick_point(event)
        if not self.picked:
            self.picked.append(point)
            self.message = f"{kind} from {point.label} - now pick the second point"
            return
        line = self.construction.add_line(self.picked[0], point, kind, self.color)
        self.picked.clear()
        if line is None:
            self.message = "those are the same elliptic point - no unique line"
        else:
            self.message = self._describe(line)

    def _press_perpendicular(self, event) -> None:
        """Two clicks: one on a point, one on a line, in whichever order."""
        if not self.picked:
            target = self._point_at(event) or self._line_at(event)
            if target is None:  # empty space: start from a fresh point
                target = self.construction.add_point(event.xdata, event.ydata, self.color)
            self.picked.append(target)
            wanted = "a line to drop onto" if isinstance(target, Point) else "a point"
            self.message = f"from {self._name(target)} - now pick {wanted}"
            return

        held = self.picked[0]
        if isinstance(held, Point):
            base = self._line_at(event)
            if base is None:
                self.message = "click on a line to drop the perpendicular onto"
                return
            point = held
        else:
            base = held
            point = self._pick_point(event)

        perpendicular = self.construction.add_perpendicular(point, base, self.color)
        self.picked.clear()
        if perpendicular is None:
            self.message = (f"{point.label} is the pole of {base.label} - "
                            "every line through it is perpendicular")
        else:
            self.message = self._describe(perpendicular)

    def _press_triangle(self, event) -> None:
        """Three clicks on points; the third closes the triangle."""
        point = self._pick_point(event)
        if any(point is held for held in self.picked):
            self.message = f"{point.label} is already a vertex - pick another"
            return
        self.picked.append(point)
        if len(self.picked) < 3:
            picked = " ".join(held.label for held in self.picked)
            self.message = f"triangle {picked} - pick another vertex"
            return
        triangle = self.construction.add_triangle(*self.picked, self.color)
        self.picked.clear()
        if triangle is None:
            self.message = "two of those are the same elliptic point - no triangle"
        else:
            self.message = self._describe(triangle)

    def _press_meet(self, event) -> None:
        """Two clicks on lines: name the point where they cross."""
        line = self._line_at(event)
        if line is None:
            self.message = "click on a line"
            return
        if not self.picked:
            self.picked.append(line)
            self.message = f"meet of {line.label} and - now pick the second line"
            return
        point = self.construction.add_meet(self.picked[0], line, self.color)
        self.picked.clear()
        if point is None:
            self.message = "that is the same line - it meets itself everywhere"
        else:
            self.message = self._describe(point)

    def _press_dual(self, event) -> None:
        """One click: a point gives its polar line, a line gives its pole."""
        point = self._point_at(event)
        if point is None and (line := self._line_at(event)) is not None:
            pole = self.construction.add_pole(line, self.color)
            self.message = ("that line is undetermined" if pole is None
                            else self._describe(pole))
            return
        with self.construction.group():  # a fresh point and its polar undo together
            point = point or self.construction.add_point(
                event.xdata, event.ydata, self.color)
            polar = self.construction.add_polar(point, self.color)
        self.message = ("that point is undetermined" if polar is None
                        else self._describe(polar))

    def _press_move(self, event) -> None:
        point = self._point_at(event)
        if point is None:
            self.message = "nothing to grab here"
            return
        if not point.is_free:
            self.message = (f"{point.label} is the {point.source.describe()} - "
                            "move what it is built on instead")
            return
        self._dragging = point
        self.message = f"moving {point.label}"

    def _press_delete(self, event) -> None:
        target = self._point_at(event) or self._line_at(event)
        if target is None:
            self.message = "nothing to delete here"
            return
        described = self._describe(target)
        self.construction.delete(target)
        self.message = f"deleted {described}"

    def _on_motion(self, event) -> None:
        if self._dragging is None or event.inaxes is not self.ax or event.xdata is None:
            return
        self._dragging.move_to(event.xdata, event.ydata)
        self._redraw()

    def _on_release(self, event) -> None:
        self._dragging = None

    def _on_key(self, event) -> None:
        if self._prompting:  # the filename box has the keyboard
            if event.key == "escape":
                self._close_prompt()
                self.message = "cancelled"
                self._redraw()
            return
        shortcuts = {s: k for k, _, s, _ in TOOLS}
        if event.key == "G":  # shift: the same save, in plain black and white
            self._ask_for_filename(plain=True)
        elif event.key in shortcuts:
            self._set_tool(shortcuts[event.key])
        elif event.key in {s: k for k, _, s in TOGGLES}:
            self._toggle({s: k for k, _, s in TOGGLES}[event.key])
        elif event.key in {s: k for k, _, s in ACTIONS}:
            self._action({s: k for k, _, s in ACTIONS}[event.key])
        elif event.key == "escape":
            self.picked.clear()
            self.message = "cancelled"
            self._redraw()

    # ------------------------------------------------------------------ drawing

    def _redraw(self) -> None:
        for artist in self._artists:
            artist.remove()
        self._artists.clear()
        self._face.set_facecolor("white" if self.flags["plain"] else "#f7f8fa")

        for line in self.construction.lines:
            self._draw_line(line)
        for triangle in self.construction.triangles:
            self._draw_triangle(triangle)
        if self.flags["meets"]:
            self._draw_meets()
        for point in self.construction.points:
            self._draw_point(point)

        self._refresh_palette()
        self.status.set_text(self._status_text())
        self.fig.canvas.draw_idle()

    def _keep(self, artists) -> None:
        self._artists.extend(np.atleast_1d(artists).tolist())

    def _ink(self, color: str) -> str:
        """An object's colour, or black when the picture is being drawn plain."""
        return PLAIN_INK if self.flags["plain"] else color

    def _draw_line(self, line: Line) -> None:
        normal = line.normal
        if normal is None:
            return
        plain = self.flags["plain"]
        ink = self._ink(line.color)
        if self._is_picked(line):  # halo round the line waiting for its partner
            for path in self._paths(line):
                self._keep(self.ax.plot(path[:, 0], path[:, 1], color=ink,
                                        lw=8.0, alpha=0.25, zorder=2))
        width = 3.4 if line.is_partial else 2.0
        if plain:  # weight carries what colour otherwise would
            width = 2.6 if line.is_partial else 1.3
        for path in self._paths(line):
            self._keep(self.ax.plot(path[:, 0], path[:, 1], color=ink,
                                    lw=width, zorder=3, solid_capstyle="round"))
        if line.is_partial:  # the rest of the line: faint, or dashed when plain
            whole = geo.line_points(normal, self.samples)
            self._keep(self.ax.plot(whole[:, 0], whole[:, 1],
                                    color=PLAIN_FAINT if plain else line.color,
                                    ls=(0, (5, 4)) if plain else "-",
                                    lw=0.8 if plain else 1.0,
                                    alpha=1.0 if plain else 0.28, zorder=2))
        if line.is_perpendicular:
            self._draw_foot(line, normal)

        ends = geo.line_endpoints(normal)
        if ends is not None and self.flags["rim"]:
            self._keep(self.ax.plot(ends[:, 0], ends[:, 1], "o", mfc="none",
                                    mec=ink, mew=1.6, ms=8, zorder=4))
            self._keep(self.ax.plot(ends[:, 0], ends[:, 1], ls=(0, (2, 4)),
                                    color=ink, lw=0.9, alpha=0.4, zorder=1))
        if ends is not None and self.flags["labels"]:
            self._keep(self.ax.text(*(ends[0] * 1.09), line.label, color=ink,
                                    fontsize=10, fontstyle="italic", ha="center",
                                    va="center", zorder=5))
        if self.flags["poles"]:
            pole = geo.polar_point(normal)
            self._keep(self.ax.plot([pole[0]], [pole[1]], "*", color=ink,
                                    ms=13, alpha=0.9, zorder=4))

    def _draw_foot(self, line: Line, normal: np.ndarray) -> None:
        """The landing point, plus a right-angle mark as the projection sees it."""
        foot = line.foot
        base_normal = line.base.normal if line.base is not None else None
        if foot is None or base_normal is None:
            return
        ink = self._ink(line.color)
        self._keep(self.ax.plot([foot[0]], [foot[1]], "s", color=ink,
                                ms=6, mec="white", mew=1.0, zorder=5))
        marker = geo.right_angle_marker(foot, base_normal, normal)
        if marker is not None:
            self._keep(self.ax.plot(marker[:, 0], marker[:, 1], color=ink,
                                    lw=1.4, alpha=0.9, zorder=4))

    def _draw_triangle(self, triangle: Triangle) -> None:
        """The sides are ordinary lines and draw themselves; this is the measuring."""
        vectors = triangle.vectors()
        if vectors is None:
            return
        a, b, c = vectors
        ink = self._ink(triangle.color)
        for vertex, first, second in ((a, b, c), (b, c, a), (c, a, b)):
            arc = geo.angle_arc(vertex, first, second)
            if arc is not None:
                self._keep(self.ax.plot(arc[:, 0], arc[:, 1], color=ink,
                                        lw=1.0 if self.flags["plain"] else 1.3,
                                        alpha=0.85, zorder=4))
        centre = triangle.centre()
        if centre is None or not self.flags["labels"]:
            return
        self._keep(self.ax.text(centre[0], centre[1], self._triangle_text(triangle),
                                color=ink, fontsize=8.5, ha="center",
                                va="center", zorder=5, linespacing=1.4))

    @staticmethod
    def _triangle_text(triangle: Triangle) -> str:
        angles = triangle.angles()
        if angles is None:
            return triangle.label
        area = triangle.area()
        excess = ("sides loop through the rim" if area is None
                  else f"area {area:.3f}")
        return f"{triangle.label}\nangles {np.degrees(sum(angles)):.1f}deg\n{excess}"

    def _draw_meets(self) -> None:
        """Crossings that no point of the construction already names."""
        named = [p.vector for p in self.construction.points if p.vector is not None]
        loose = [xy for xy, _, _ in self.construction.intersections()
                 if not any(geo.distance(geo.lift(*xy), v) < 1e-6 for v in named)]
        if not loose:
            return
        xy = np.array(loose)
        self._keep(self.ax.plot(xy[:, 0], xy[:, 1], "x", color=COL_MEET, ms=8,
                                mew=1.8, alpha=0.85, zorder=5))

    def _draw_point(self, point: Point) -> None:
        xy = point.xy
        if xy is None:  # a meet of two lines that have fallen together
            return
        ink, plain = self._ink(point.color), self.flags["plain"]
        if point.is_free:
            self._keep(self.ax.plot([xy[0]], [xy[1]], "o", color=ink,
                                    ms=6 if plain else 10, zorder=6,
                                    mec="white", mew=0.6 if plain else 1.2))
        else:  # derived: hollow, to say it is not yours to drag
            self._keep(self.ax.plot([xy[0]], [xy[1]], "D", mfc="white",
                                    ms=6 if plain else 8,
                                    mec=ink, mew=1.4 if plain else 2.0, zorder=6))
        if self._is_picked(point):
            self._keep(self.ax.plot([xy[0]], [xy[1]], "o", mfc="none",
                                    mec=ink, mew=2.0, ms=20, zorder=6))
        if self.flags["labels"]:
            self._keep(self.ax.text(xy[0] + 0.038, xy[1] + 0.028, point.label,
                                    color=ink, fontsize=11,
                                    fontstyle="italic" if plain else "normal",
                                    fontweight="normal" if plain else "bold",
                                    zorder=6))

    def _is_picked(self, obj) -> bool:
        return any(obj is held for held in self.picked)

    # ------------------------------------------------------------------ text

    @staticmethod
    def _name(obj) -> str:
        return f"{obj.kind} {obj.label}"

    def _describe(self, obj) -> str:
        if isinstance(obj, Triangle):
            return self._describe_triangle(obj)
        if isinstance(obj, Point):
            xy = obj.xy
            built = "" if obj.is_free else f" = {obj.source.describe()}"
            where = "undetermined" if xy is None else f"({xy[0]:+.3f}, {xy[1]:+.3f})"
            return f"{obj.kind} {obj.label}{built}   {where}"
        normal = obj.normal
        if normal is None:
            return f"{obj.kind} {obj.label}"
        shape = ("boundary circle" if geo.is_boundary_line(normal) else
                 "diameter" if abs(normal[2]) < 1e-6 else
                 f"semi-minor axis {abs(normal[2]):.3f}")
        if obj.is_perpendicular:
            d, foot = obj.length(), obj.foot
            where = "" if foot is None else f"   foot ({foot[0]:+.3f}, {foot[1]:+.3f})"
            return (f"perpendicular {obj.label} from {obj.p.label} to {obj.base.label}   "
                    f"distance {d:.4f} rad = {np.degrees(d):.2f}deg{where}")
        if obj.is_segment:
            d = obj.length()
            return (f"segment {obj.label} = {obj.p.label}{obj.q.label}   "
                    f"length {d:.4f} rad = {np.degrees(d):.2f}deg = {d / np.pi:.3f} pi")
        if obj.is_polar:
            pole = geo.polar_point(normal)
            return (f"polar {obj.label} of {obj.p.label}   every point of it is "
                    f"pi/2 from {obj.p.label}   pole ({pole[0]:+.3f}, {pole[1]:+.3f})")
        return (f"line {obj.label} through {obj.p.label}{obj.q.label}   "
                f"normal ({normal[0]:+.3f}, {normal[1]:+.3f}, {normal[2]:+.3f})   {shape}")

    @staticmethod
    def _describe_triangle(triangle: Triangle) -> str:
        angles = triangle.angles()
        if angles is None:
            return f"triangle {triangle.label}"
        total = sum(angles)
        listed = " ".join(f"{np.degrees(a):.1f}" for a in angles)
        area = triangle.area()
        excess = (f"area {area:.4f} = the {np.degrees(total) - 180:.2f}deg over pi"
                  if area is not None else
                  "its sides close up through the rim, so no disk is enclosed")
        return (f"triangle {triangle.label}   angles {listed} deg   "
                f"sum {np.degrees(total):.2f}deg   {excess}")

    def _wanted(self) -> str:
        """What the half-finished tool is waiting for."""
        if self.tool == "perp":
            return "a line to drop onto" if isinstance(self.pending, Point) else "a point"
        if self.tool == "meet":
            return "the second line"
        if self.tool == "triangle":
            return "the second vertex" if len(self.picked) == 1 else "the third vertex"
        return "the second point"

    def _status_text(self) -> str:
        name, hint = next((lbl, h) for k, lbl, _, h in TOOLS if k == self.tool)
        if self.picked:
            held = " ".join(self._name(obj) for obj in self.picked)
            hint = f"{held} selected - click {self._wanted()} (esc cancels)"
        counts = (f"{len(self.construction.points)} points   "
                  f"{len(self.construction.lines)} lines   "
                  f"{len(self.construction.intersections())} meets")
        if self.construction.triangles:
            counts += f"   {len(self.construction.triangles)} triangles"
        return f"{name.upper()}: {hint}\n{self.message}\n{counts}"

    # ------------------------------------------------------------------ run

    def show(self) -> None:
        import matplotlib.pyplot as plt

        plt.show()

    def save(self, path: str, dpi: int = 120) -> None:
        self.fig.savefig(path, dpi=dpi, facecolor=self.fig.get_facecolor())
