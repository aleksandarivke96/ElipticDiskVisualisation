"""The construction tool itself: which tool is armed, what a click does, what to say.

This module is deliberately free of any toolkit.  It owns a `Construction`, the
tool and flag state, and turns clicks in *disk coordinates* into edits; what it
hands back for drawing is a `scene.Scene`, in sphere coordinates.  The Qt window
in `elliptic.qtui` is one consumer of that, the 3-D sphere pane is another, and
the tests are a third - none of them are privileged.

Positions coming in are always disk coordinates *as currently drawn*, so a click
in the conformal view is lifted back through the stereographic map and a click in
the ordinary view straight down.  What the model stores never changes.
"""

from __future__ import annotations

import numpy as np

from . import gclc
from . import geometry as geo
from . import scene as sc
from .model import (LINE, PALETTE, SEGMENT, Circle, Construction, Line, Point,
                    Triangle)

PICK_POINT_PX = 13.0
PICK_LINE_PX = 9.0
DEFAULT_SCALE = 380.0  # pixels across one disk radius, until a canvas says otherwise

TOOLS = [
    ("point", "Point", "1", "click anywhere to drop a point"),
    ("line", "Line", "2", "click two points (or two empty spots) to join them"),
    ("segment", "Segment", "3", "click two points for the shortest path between them"),
    ("perp", "Perpendicular", "4", "click a point and a line, in either order"),
    ("triangle", "Triangle", "5", "click three points; the angles give the area"),
    ("circle", "Circle", "0", "click the centre, then a point on the circle"),
    ("midpoint", "Midpoint", "m", "click two points for the middle of the shortest path"),
    ("meet", "Meet", "6", "click two lines to name the point where they cross"),
    ("bisect", "Bisect angle", "n", "click two lines; both bisectors of their angles appear"),
    ("dual", "Polar / Pole", "7", "click a point for its polar, a line for its pole"),
    ("move", "Move", "8", "drag a point; everything built on it follows"),
    ("pivot", "Rotate about", "t", "click the point the Rotate slider should turn around"),
    ("delete", "Delete", "9", "click a point or a line; a triangle goes with its sides"),
]
TOGGLES = [
    ("labels", "Labels", "l"),
    ("poles", "Poles", "p"),
    ("meets", "Meets", "x"),
    ("rim", "Rim ends", "e"),
    ("plain", "Plain", "b"),        # black ink and line weights, as it will be exported
    ("conformal", "Conformal", "o"),  # stereographic instead of straight down
    ("sphere", "3-D sphere", "s"),  # the hemisphere the disk is a picture of
    ("rays", "Projectors", "r"),    # in 3-D: the rays that carry sphere to disk
    ("antipodes", "Antipodes", "a"),  # in 3-D: the other half of each pair
]
ACTIONS = [("undo", "Undo", "u"), ("clear", "Clear", "c"),
           ("gclc", "Save GCLC", "g")]  # shift-G saves the same thing in plain black
# The Rotate slider turns the whole construction about a chosen point - a live
# isometry of the plane.  A rotation about a point of the elliptic plane IS the
# rotation of the sphere about that point's axis, so the pivot can be any point
# of the construction; with none chosen it is the centre of the disk, and a
# pivot on the rim rolls the figure out through the rim and in the far side.
ARROW_STEP = 3.0  # degrees per arrow-key press
DEFAULT_EXPORT = "construction.gcl"

DEFAULT_FLAGS = {"labels": True, "poles": False, "meets": True, "rim": True,
                 # The textbook disk model is the stereographic picture.  Keep
                 # the orthogonal hemisphere view available through the same
                 # toggle, but open on the view in which its clines are circles.
                 "plain": False, "conformal": True,
                 "sphere": True, "rays": True, "antipodes": False}


class EllipticDiskViewer:
    """Palette-driven construction tool for the elliptic plane."""

    def __init__(self, samples: int = 512):
        self.samples = samples
        self.construction = Construction()
        self.tool = "point"
        self.color: str | None = None  # None = cycle through the palette
        self.flags = dict(DEFAULT_FLAGS)
        self.picked: list[Point | Line] = []  # objects a half-finished tool holds
        self.pivot: Point | None = None  # what the Rotate slider turns about
        self.turned = 0.0                # its accumulated angle, in degrees
        self.message = ""
        self.scale = DEFAULT_SCALE
        self.on_change: list = []  # canvases that want to know when to repaint

        self._dragging: Point | None = None
        self._prompting = False
        self._plain_export = False
        self.window = None

    # ------------------------------------------------------------------ state

    @property
    def pending(self) -> Point | Line | None:
        """The most recent half-finished pick, if the current tool is waiting."""
        return self.picked[-1] if self.picked else None

    @property
    def projection(self) -> geo.Projection:
        """How the hemisphere is being laid on the disk at the moment."""
        return geo.STEREOGRAPHIC if self.flags["conformal"] else geo.ORTHOGONAL

    @property
    def prompting(self) -> bool:
        """True while the box asking where to save is up."""
        return self._prompting

    @property
    def plain_export(self) -> bool:
        return self._plain_export

    def changed(self) -> None:
        """Tell whoever is drawing that the picture is out of date."""
        for callback in self.on_change:
            callback()

    def scene(self) -> sc.Scene:
        """Everything to draw, in sphere coordinates - see `elliptic.scene`."""
        return sc.build(self.construction, self.flags, self.picked, self.samples,
                        pivot=self.live_pivot())

    # ------------------------------------------------------------------ projecting

    def screen(self, vectors) -> np.ndarray:
        """Points of the sphere -> where they sit in the disk, as drawn now."""
        return self.projection.project(np.asarray(vectors, dtype=float))

    def lift(self, x: float, y: float) -> np.ndarray:
        """Where a click landed, as a point of the sphere."""
        return self.projection.lift(x, y)

    def paths(self, line: Line) -> list[np.ndarray]:
        """The drawn pieces of a line, in disk coordinates."""
        return [self.screen(path) for path in sc.line_curves(line, self.samples)]

    def circle_paths(self, circle: Circle) -> list[np.ndarray]:
        """The drawn pieces of a circle, in disk coordinates."""
        return [self.screen(path) for path in sc.circle_curves(circle, self.samples)]

    # ------------------------------------------------------------------ palette

    def set_tool(self, tool: str) -> None:
        self.tool = tool
        self.picked.clear()
        self.message = ""
        self.changed()

    def toggle(self, flag: str) -> None:
        self.flags[flag] = not self.flags[flag]
        self.changed()

    def set_color(self, color: str | None) -> None:
        self.color = color
        self.message = f"colour: {color or 'auto'}"
        self.changed()

    def live_pivot(self) -> Point | None:
        """The chosen pivot, so long as it is still part of the construction."""
        if (self.pivot is not None
                and not any(self.pivot is p for p in self.construction.points)):
            self.pivot = None  # deleted or cleared away: back to the centre
        return self.pivot

    def pivot_text(self) -> str:
        pivot = self.live_pivot()
        return "about the centre" if pivot is None else f"about {pivot.label}"

    def set_pivot(self, point: Point | None) -> None:
        """Choose what the Rotate slider turns about; the slider starts afresh."""
        self.pivot = point
        self.turned = 0.0
        self.message = ("the Rotate slider turns about the centre of the disk"
                        if point is None else
                        f"the Rotate slider now turns {self.pivot_text()}")
        self.changed()

    def rotate(self, degrees: float) -> None:
        """Turn the construction about the pivot, to an accumulated `degrees`.

        The slider hands in its absolute position; only the difference from
        where it last was is applied, so dragging it back to zero brings the
        figure back exactly.  Angles wrap at half a turn - a rotation by
        `delta - 360` is the same rotation, so wrapping costs nothing.
        """
        degrees = (degrees + 180.0) % 360.0 - 180.0
        delta = degrees - self.turned
        if not delta:
            return
        pivot = self.live_pivot()
        axis = np.array([0.0, 0.0, 1.0]) if pivot is None else pivot.vector
        if axis is None:  # a derived pivot with nowhere to be right now
            self.message = f"{pivot.label} is undetermined - nothing to turn about"
            self.changed()
            return
        self.turned = degrees
        moved = self.construction.rotate(geo.rotation(axis, np.radians(delta)))
        if moved:
            self.message = (f"turned {degrees:+.0f} deg {self.pivot_text()} - an "
                            "isometry: every distance, angle and area is unchanged")
        self.changed()

    def action(self, action: str) -> None:
        if action == "undo":
            removed = self.construction.undo()
            self.message = (f"undid {self.describe(removed)}" if removed
                            else "nothing to undo")
        elif action == "clear":
            self.construction.clear()
            self.message = "cleared"
        elif action == "gclc":
            self.begin_prompt(self.flags["plain"])  # save what you can see
            return
        self.picked.clear()
        self.changed()

    # ------------------------------------------------------------------ export

    def begin_prompt(self, plain: bool = False) -> None:
        """Open the little box that asks where the GCLC file should go."""
        self._prompting = True
        self._plain_export = plain
        self.message = ("plain, no colour - file name, then enter (esc cancels)" if plain
                        else "file name, then enter (esc cancels; G saves plain)")
        self.changed()

    def cancel_prompt(self) -> None:
        if not self._prompting:
            return
        self._prompting = False
        self.message = "cancelled"
        self.changed()

    def submit_prompt(self, name: str) -> str | None:
        """Write the file the box was asking about, or say why not."""
        if not self._prompting:
            return None
        self._prompting = False
        written = None
        try:
            written = gclc.export(self.construction, name, plain=self._plain_export,
                                  projection=self.projection)
        except (OSError, ValueError) as problem:
            self.message = f"could not write it: {problem}"
        else:
            how = "plain GCLC" if self._plain_export else "GCLC"
            counts = (f"{len(self.construction.points)} points, "
                      f"{len(self.construction.lines)} lines")
            self.message = f"wrote {written} for {how} - {counts}"
        self.changed()
        return written

    # ------------------------------------------------------------------ hit testing

    def point_at(self, x: float, y: float) -> Point | None:
        best, best_d = None, PICK_POINT_PX / self.scale
        for point in self.construction.points:
            vector = point.vector
            if vector is None:  # a derived point with nowhere to be right now
                continue
            d = float(np.hypot(*(self.screen(vector) - (x, y))))
            if d <= best_d:
                best, best_d = point, d
        return best

    def line_at(self, x: float, y: float) -> Line | None:
        best, best_d = None, PICK_LINE_PX / self.scale
        for line in self.construction.lines:
            for path in self.paths(line):
                if len(path) < 2:
                    continue
                d = float(np.hypot(path[:, 0] - x, path[:, 1] - y).min())
                if d <= best_d:
                    best, best_d = line, d
        return best

    def circle_at(self, x: float, y: float) -> Circle | None:
        best, best_d = None, PICK_LINE_PX / self.scale
        for circle in self.construction.circles:
            for path in self.circle_paths(circle):
                if len(path) < 2:
                    continue
                d = float(np.hypot(path[:, 0] - x, path[:, 1] - y).min())
                if d <= best_d:
                    best, best_d = circle, d
        return best

    # ------------------------------------------------------------------ events

    def press(self, x: float, y: float) -> None:
        if self._prompting:  # clicking away from the box puts it away
            self.cancel_prompt()
            return
        {
            "point": self._press_point,
            "line": lambda p: self._press_join(p, LINE),
            "segment": lambda p: self._press_join(p, SEGMENT),
            "perp": self._press_perpendicular,
            "triangle": self._press_triangle,
            "circle": self._press_circle,
            "midpoint": self._press_midpoint,
            "meet": self._press_meet,
            "bisect": self._press_bisect,
            "dual": self._press_dual,
            "move": self._press_move,
            "pivot": self._press_pivot,
            "delete": self._press_delete,
        }[self.tool]((x, y))
        self.changed()

    def motion(self, x: float, y: float) -> None:
        if self._dragging is None:
            return
        self._dragging.place(self.lift(x, y))
        self.changed()

    def release(self) -> None:
        self._dragging = None

    def key(self, pressed: str) -> None:
        if self._prompting:  # the filename box has the keyboard
            if pressed == "escape":
                self.cancel_prompt()
            return
        if pressed == "G":  # shift: the same save, in plain black and white
            self.begin_prompt(plain=True)
            return
        if pressed in ("left", "right"):
            step = ARROW_STEP if pressed == "right" else -ARROW_STEP
            self.rotate(self.turned + step)
            return
        for table, act in ((TOOLS, self.set_tool), (TOGGLES, self.toggle),
                           (ACTIONS, self.action)):
            for entry in table:
                if entry[2] == pressed:
                    act(entry[0])
                    return
        if pressed == "escape":
            self.picked.clear()
            self.message = "cancelled"
            self.changed()

    # ------------------------------------------------------------------ the tools

    def _fresh(self, at) -> Point:
        return self.construction.place_point(self.lift(*at), self.color)

    def _pick_point(self, at) -> Point:
        """The point clicked on, or a fresh one where the click landed."""
        return self.point_at(*at) or self._fresh(at)

    def _press_point(self, at) -> None:
        point = self._fresh(at)
        self._dragging = point
        self.message = f"point {point.label}"

    def _press_join(self, at, kind: str) -> None:
        point = self._pick_point(at)
        if not self.picked:
            self.picked.append(point)
            self.message = f"{kind} from {point.label} - now pick the second point"
            return
        line = self.construction.add_line(self.picked[0], point, kind, self.color)
        self.picked.clear()
        self.message = ("those are the same elliptic point - no unique line"
                        if line is None else self.describe(line))

    def _press_perpendicular(self, at) -> None:
        """Two clicks: one on a point, one on a line, in whichever order."""
        if not self.picked:
            target = self.point_at(*at) or self.line_at(*at) or self._fresh(at)
            self.picked.append(target)
            wanted = "a line to drop onto" if isinstance(target, Point) else "a point"
            self.message = f"from {self.name(target)} - now pick {wanted}"
            return

        held = self.picked[0]
        if isinstance(held, Point):
            base = self.line_at(*at)
            if base is None:
                self.message = "click on a line to drop the perpendicular onto"
                return
            point = held
        else:
            base = held
            point = self._pick_point(at)

        perpendicular = self.construction.add_perpendicular(point, base, self.color)
        self.picked.clear()
        if perpendicular is None:
            self.message = (f"{point.label} is the pole of {base.label} - "
                            "every line through it is perpendicular")
        else:
            self.message = self.describe(perpendicular)

    def _press_triangle(self, at) -> None:
        """Three clicks on points; the third closes the triangle."""
        point = self._pick_point(at)
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
        self.message = ("two of those are the same elliptic point - no triangle"
                        if triangle is None else self.describe(triangle))

    def _press_circle(self, at) -> None:
        """Two clicks: the centre, then any point the circle should pass through."""
        point = self._pick_point(at)
        if not self.picked:
            self.picked.append(point)
            self.message = f"circle about {point.label} - now pick a point on it"
            return
        circle = self.construction.add_circle(self.picked[0], point, self.color)
        self.picked.clear()
        self.message = ("those are the same elliptic point - no circle to draw"
                        if circle is None else self.describe(circle))

    def _press_midpoint(self, at) -> None:
        """Two clicks on points: the midpoint of the shortest path between them."""
        point = self._pick_point(at)
        if not self.picked:
            self.picked.append(point)
            self.message = f"midpoint from {point.label} - now pick the second point"
            return
        made = self.construction.add_midpoint(self.picked[0], point, self.color)
        self.picked.clear()
        self.message = ("those are the same elliptic point - nothing to halve"
                        if made is None else self.describe(made))

    def _press_meet(self, at) -> None:
        """Two clicks on lines: name the point where they cross."""
        line = self.line_at(*at)
        if line is None:
            self.message = "click on a line"
            return
        if not self.picked:
            self.picked.append(line)
            self.message = f"meet of {line.label} and - now pick the second line"
            return
        point = self.construction.add_meet(self.picked[0], line, self.color)
        self.picked.clear()
        self.message = ("that is the same line - it meets itself everywhere"
                        if point is None else self.describe(point))

    def _press_bisect(self, at) -> None:
        """Two clicks on lines: both bisectors of the angles they make."""
        line = self.line_at(*at)
        if line is None:
            self.message = "click on a line"
            return
        if not self.picked:
            self.picked.append(line)
            self.message = f"bisect between {line.label} and - now pick the second line"
            return
        made = self.construction.add_bisectors(self.picked[0], line, self.color)
        self.picked.clear()
        self.message = ("that is the same elliptic line - no angle to bisect"
                       if made is None else
                       f"bisectors {made[0].label} and {made[1].label} - one for "
                       "each pair of vertical angles, perpendicular to each other")

    def _press_dual(self, at) -> None:
        """One click: a point gives its polar line, a line gives its pole."""
        point = self.point_at(*at)
        if point is None and (line := self.line_at(*at)) is not None:
            pole = self.construction.add_pole(line, self.color)
            self.message = ("that line is undetermined" if pole is None
                            else self.describe(pole))
            return
        with self.construction.group():  # a fresh point and its polar undo together
            point = point or self._fresh(at)
            polar = self.construction.add_polar(point, self.color)
        self.message = ("that point is undetermined" if polar is None
                        else self.describe(polar))

    def _press_move(self, at) -> None:
        point = self.point_at(*at)
        if point is None:
            self.message = "nothing to grab here"
            return
        if not point.is_free:
            self.message = (f"{point.label} is the {point.source.describe()} - "
                            "move what it is built on instead")
            return
        self._dragging = point
        self.message = f"moving {point.label}"

    def _press_pivot(self, at) -> None:
        """One click: the point the Rotate slider turns about, made if need be."""
        self.set_pivot(self._pick_point(at))

    def _press_delete(self, at) -> None:
        target = self.point_at(*at) or self.line_at(*at) or self.circle_at(*at)
        if target is None:
            self.message = "nothing to delete here"
            return
        described = self.describe(target)
        self.construction.delete(target)
        self.message = f"deleted {described}"

    # ------------------------------------------------------------------ text

    @staticmethod
    def name(obj) -> str:
        return f"{obj.kind} {obj.label}"

    def describe(self, obj) -> str:
        if isinstance(obj, Triangle):
            return describe_triangle(obj)
        if isinstance(obj, Circle):
            r = obj.radius()
            if r is None:
                return f"circle {obj.label}"
            note = (f"   at pi/2 this is the polar of {obj.centre.label}"
                    if abs(r - geo.HALF_PI) < 1e-4 else "")
            return (f"circle {obj.label} about {obj.centre.label} through "
                    f"{obj.through.label}   radius {r:.4f} rad = "
                    f"{np.degrees(r):.2f}deg{note}")
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
        if obj.is_bisector:
            return (f"bisector {obj.label} of {obj.base.label} and {obj.other.label}   "
                    "equal angles with both, through their meet")
        return (f"line {obj.label} through {obj.p.label}{obj.q.label}   "
                f"normal ({normal[0]:+.3f}, {normal[1]:+.3f}, {normal[2]:+.3f})   {shape}")

    def _wanted(self) -> str:
        """What the half-finished tool is waiting for."""
        if self.tool == "perp":
            return "a line to drop onto" if isinstance(self.pending, Point) else "a point"
        if self.tool in ("meet", "bisect"):
            return "the second line"
        if self.tool == "triangle":
            return "the second vertex" if len(self.picked) == 1 else "the third vertex"
        if self.tool == "circle":
            return "a point on the circle"
        return "the second point"

    def status_text(self) -> str:
        name, hint = next((lbl, h) for k, lbl, _, h in TOOLS if k == self.tool)
        if self.picked:
            held = " ".join(self.name(obj) for obj in self.picked)
            hint = f"{held} selected - click {self._wanted()} (esc cancels)"
        counts = (f"{len(self.construction.points)} points   "
                  f"{len(self.construction.lines)} lines   "
                  f"{len(self.construction.intersections())} meets")
        if self.construction.circles:
            counts += f"   {len(self.construction.circles)} circles"
        if self.construction.triangles:
            counts += f"   {len(self.construction.triangles)} triangles"
        return f"{name.upper()}: {hint}\n{self.message}\n{counts}"

    # ------------------------------------------------------------------ run

    def show(self) -> None:
        """Open the window and hand control to Qt until it is closed."""
        from .ui import run

        run(self)

    def save(self, path: str, width: int = 1400, height: int = 900) -> str:
        """Render the current picture straight to an image file, no window needed."""
        from .ui import render

        return render(self, path, width, height)


def describe_triangle(triangle: Triangle) -> str:
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
