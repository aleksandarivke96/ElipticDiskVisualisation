"""The construction being drawn: points, the lines built on them, and triangles.

Nothing here stores a position or a normal vector.  Every object keeps
references to the objects it was built from and re-derives itself on demand, so
dragging one free point ripples through the whole construction.  Points come in
two sorts: *free* ones, which carry a position and can be moved, and *derived*
ones, which carry a `source` - the meet of two lines, or the pole of one - and
follow whatever they were built from.  A derived object can be undefined (a
meet needs two distinct lines), which is what the `None`s below are about.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from string import ascii_lowercase, ascii_uppercase

import numpy as np

from . import geometry as geo

PALETTE = [
    "#1a9e6a",  # green
    "#8a4fd0",  # violet
    "#2f7bd6",  # blue
    "#e8543f",  # red
    "#d99a00",  # amber
    "#0f9aa8",  # teal
    "#c2417f",  # magenta
    "#5b6472",  # slate
]

LINE = "line"
SEGMENT = "segment"
PERPENDICULAR = "perpendicular"
POLAR = "polar"


def _next_label(used: set[str], alphabet: str) -> str:
    """A, B, ... Z, A1, B1, ... - the first one not already taken."""
    i = 0
    while True:
        label = alphabet[i % len(alphabet)]
        cycle = i // len(alphabet)
        if cycle:
            label += str(cycle)
        if label not in used:
            return label
        i += 1


@dataclass(eq=False)
class Meet:
    """A point pinned to where two lines cross."""

    first: "Line"
    second: "Line"
    kind = "meet"

    def vector(self) -> np.ndarray | None:
        n1, n2 = self.first.normal, self.second.normal
        if n1 is None or n2 is None:
            return None
        return geo.meet_vector(n1, n2)

    def depends_on(self, obj) -> bool:
        return obj is self.first or obj is self.second

    def describe(self) -> str:
        return f"{self.first.label} x {self.second.label}"


@dataclass(eq=False)
class Pole:
    """A point pinned to the pole of a line - its dual."""

    line: "Line"
    kind = "pole"

    def vector(self) -> np.ndarray | None:
        normal = self.line.normal
        return None if normal is None else geo.pole_vector(normal)

    def depends_on(self, obj) -> bool:
        return obj is self.line

    def describe(self) -> str:
        return f"pole of {self.line.label}"


@dataclass(eq=False)  # identity, not value: two dots at the same spot are still
class Point:          # two different points
    """A free point carrying a position, or a derived one carrying a `source`."""

    label: str
    color: str
    _xy: np.ndarray | None = None
    source: Meet | Pole | None = None

    @property
    def is_free(self) -> bool:
        return self.source is None

    @property
    def kind(self) -> str:
        return "point" if self.source is None else self.source.kind

    @property
    def vector(self) -> np.ndarray | None:
        """Position lifted to the upper hemisphere; None if undetermined."""
        if self.source is None:
            return geo.lift(*self._xy)
        return self.source.vector()

    @property
    def xy(self) -> np.ndarray | None:
        """Position in the disk; None while a derived point has nowhere to be."""
        if self.source is None:
            return self._xy
        vector = self.source.vector()
        return None if vector is None else vector[:2].copy()

    def move_to(self, x: float, y: float) -> None:
        """Reposition a free point.  Derived points ignore this - move their
        sources instead."""
        if self.source is None:
            self._xy = np.array(geo.clamp_to_disk(x, y))

    def depends_on(self, obj) -> bool:
        return self.source is not None and self.source.depends_on(obj)


@dataclass(eq=False)
class Line:
    """A line through two points; or, when `base` is set, the perpendicular
    dropped from `p` onto `base`; or, for kind POLAR, the polar of `p`. Either
    way the normal is derived on demand, so everything follows when a point
    moves."""

    p: Point
    q: Point | None
    kind: str
    label: str
    color: str
    base: "Line | None" = None

    @property
    def normal(self) -> np.ndarray | None:
        """Unit normal of the great circle, or None where it is undetermined."""
        vector = self.p.vector
        if vector is None:
            return None
        if self.kind == POLAR:
            return geo.polar_normal(vector)
        if self.base is not None:
            base_normal = self.base.normal
            if base_normal is None:
                return None
            return geo.perpendicular_normal(vector, base_normal)
        other = self.q.vector
        return None if other is None else geo.line_normal(vector, other)

    @property
    def is_segment(self) -> bool:
        return self.kind == SEGMENT

    @property
    def is_perpendicular(self) -> bool:
        return self.kind == PERPENDICULAR

    @property
    def is_polar(self) -> bool:
        return self.kind == POLAR

    @property
    def is_partial(self) -> bool:
        """Drawn as a highlighted piece of the whole line."""
        return self.kind in (SEGMENT, PERPENDICULAR)

    @property
    def foot(self) -> np.ndarray | None:
        """Where a perpendicular lands on its base, as a unit vector."""
        vector = self.p.vector
        if self.base is None or vector is None:
            return None
        base_normal = self.base.normal
        if base_normal is None:
            return None
        return geo.foot_of_perpendicular(vector, base_normal)

    def depends_on(self, obj) -> bool:
        return obj is self.p or obj is self.q or obj is self.base

    def length(self) -> float | None:
        """Segment length, or the point-to-line distance for a perpendicular.

        None for a whole line, which has no ends, and wherever the line itself
        is undetermined.
        """
        vector = self.p.vector
        if vector is None or self.kind == POLAR:
            return None
        if self.base is not None:
            base_normal = self.base.normal
            return None if base_normal is None else geo.distance_to_line(vector, base_normal)
        other = self.q.vector
        return None if other is None else geo.distance(vector, other)

    def endpoints(self) -> tuple[np.ndarray, np.ndarray] | None:
        """The two ends of the highlighted piece, as unit vectors."""
        vector = self.p.vector
        if vector is None or self.kind == POLAR:
            return None
        if self.base is not None:
            foot = self.foot
            return None if foot is None else (vector, foot)
        other = self.q.vector
        return None if other is None else (vector, other)


@dataclass(eq=False)
class Triangle:
    """Three points, the three segments between them, and what they measure.

    The sides are ordinary segments in the construction - you can drop a
    perpendicular onto one - and the triangle itself is the measurement laid
    over them: three angles, and the area they imply.
    """

    a: Point
    b: Point
    c: Point
    sides: tuple[Line, Line, Line]
    color: str
    kind = "triangle"

    @property
    def label(self) -> str:
        return "".join(vertex.label for vertex in self.vertices)

    @property
    def vertices(self) -> tuple[Point, Point, Point]:
        return (self.a, self.b, self.c)

    def vectors(self) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
        lifted = [vertex.vector for vertex in self.vertices]
        return None if any(v is None for v in lifted) else tuple(lifted)

    def angles(self) -> tuple[float, float, float] | None:
        """The interior angle at each vertex, in radians."""
        lifted = self.vectors()
        return None if lifted is None else geo.triangle_angles(*lifted)

    def bounds_a_disk(self) -> bool:
        """False when the sides close up the long way round, through the rim."""
        lifted = self.vectors()
        return lifted is not None and geo.bounds_a_disk(*lifted)

    def area(self) -> float | None:
        """The angular excess, which *is* the area - None if it does not apply."""
        lifted = self.vectors()
        return None if lifted is None else geo.triangle_area(*lifted)

    def centre(self) -> np.ndarray | None:
        lifted = self.vectors()
        return None if lifted is None else geo.triangle_centre(*lifted)

    def depends_on(self, obj) -> bool:
        return any(obj is side for side in self.sides)


Object = Point | Line | Triangle


@dataclass
class Construction:
    points: list[Point] = field(default_factory=list)
    lines: list[Line] = field(default_factory=list)
    triangles: list[Triangle] = field(default_factory=list)
    # one entry per user action, so a tool that makes four objects undoes as one
    _created: list[list[Object]] = field(default_factory=list)
    _grouping: bool = False

    @property
    def objects(self) -> list[Object]:
        return [*self.points, *self.lines, *self.triangles]

    # ------------------------------------------------------------- building

    def add_point(self, x: float, y: float, color: str | None = None) -> Point:
        return self._register(Point(self._point_label(), self._point_color(color),
                                    _xy=np.array(geo.clamp_to_disk(x, y))),
                              self.points)

    def add_line(self, p: Point, q: Point, kind: str = LINE,
                 color: str | None = None) -> Line | None:
        """Join two points. None if they are one and the same elliptic point."""
        if p is q or p.vector is None or q.vector is None:
            return None
        if geo.line_normal(p.vector, q.vector) is None:
            return None
        return self._register(Line(p, q, kind, self._line_label(),
                                   self._line_color(color)), self.lines)

    def add_perpendicular(self, p: Point, base: Line,
                          color: str | None = None) -> Line | None:
        """Drop a perpendicular from a point onto a line.

        None when the point is the pole of that line, where every line through
        it is perpendicular and there is nothing unique to draw.
        """
        base_normal = base.normal
        if base_normal is None or p.vector is None:
            return None
        if geo.perpendicular_normal(p.vector, base_normal) is None:
            return None
        return self._register(Line(p, None, PERPENDICULAR, self._line_label(),
                                   self._line_color(color), base=base), self.lines)

    def add_polar(self, p: Point, color: str | None = None) -> Line | None:
        """The polar of a point: the line every point of which is pi/2 away."""
        if p.vector is None:
            return None
        return self._register(Line(p, None, POLAR, self._line_label(),
                                   self._line_color(color)), self.lines)

    def add_pole(self, line: Line, color: str | None = None) -> Point | None:
        """The pole of a line, as a point that follows it."""
        if line.normal is None:
            return None
        return self._register(Point(self._point_label(), self._point_color(color),
                                    source=Pole(line)), self.points)

    def add_meet(self, first: Line, second: Line, color: str | None = None) -> Point | None:
        """Name the point where two lines cross. None if they are the same line."""
        if first is second:
            return None
        source = Meet(first, second)
        if source.vector() is None:
            return None
        return self._register(Point(self._point_label(), self._point_color(color),
                                    source=source), self.points)

    def add_triangle(self, a: Point, b: Point, c: Point,
                     color: str | None = None) -> Triangle | None:
        """Three vertices, three segments and the measurements over them.

        None unless all three are distinct elliptic points; the sides are
        ordinary segments, and the triangle goes when any of them does.
        """
        pairs = ((a, b), (b, c), (c, a))
        if any(p is q or p.vector is None or q.vector is None for p, q in pairs):
            return None
        if any(geo.line_normal(p.vector, q.vector) is None for p, q in pairs):
            return None
        color = self._line_color(color)  # one colour: the three sides are one figure
        with self.group():
            sides = tuple(self.add_line(p, q, SEGMENT, color) for p, q in pairs)
            return self._register(Triangle(a, b, c, sides, color), self.triangles)

    # ------------------------------------------------------------- bookkeeping

    def _point_label(self) -> str:
        return _next_label({p.label for p in self.points}, ascii_uppercase)

    def _line_label(self) -> str:
        return _next_label({l.label for l in self.lines}, ascii_lowercase)

    def _point_color(self, color: str | None = None) -> str:
        return color or PALETTE[len(self.points) % len(PALETTE)]

    def _line_color(self, color: str | None = None) -> str:
        return color or PALETTE[(len(self.lines) + 2) % len(PALETTE)]

    def _register(self, obj, into: list):
        into.append(obj)
        if not self._grouping or not self._created:
            self._created.append([])
        self._created[-1].append(obj)
        return obj

    @contextmanager
    def group(self):
        """Everything made in here counts as one action for undo."""
        if self._grouping:  # already inside one; let the outer group own it
            yield
            return
        self._created.append([])
        self._grouping = True
        try:
            yield
        finally:
            self._grouping = False
            if self._created and not self._created[-1]:
                self._created.pop()

    # ------------------------------------------------------------- removing

    def dependents(self, obj: Object) -> list[Object]:
        """`obj` plus everything that would be left dangling without it."""
        doomed: list[Object] = [obj]
        growing = True
        while growing:
            growing = False
            for item in self.objects:
                if any(item is d for d in doomed):
                    continue
                if any(item.depends_on(d) for d in doomed):
                    doomed.append(item)
                    growing = True
        return doomed

    def delete(self, obj: Object) -> None:
        """Remove an object, along with anything built on top of it."""
        doomed = self.dependents(obj)
        keep = lambda item: not any(item is d for d in doomed)
        self.points = [p for p in self.points if keep(p)]
        self.lines = [l for l in self.lines if keep(l)]
        self.triangles = [t for t in self.triangles if keep(t)]
        self._created = [survivors for survivors in
                         ([o for o in step if keep(o)] for step in self._created)
                         if survivors]

    def undo(self) -> Object | None:
        """Remove the most recent action, however many objects it made."""
        if not self._created:
            return None
        step = self._created[-1]
        obj = step[-1]
        for item in list(step):
            self.delete(item)
        return obj

    def clear(self) -> None:
        self.points.clear()
        self.lines.clear()
        self.triangles.clear()
        self._created.clear()

    # ------------------------------------------------------------- derived

    def intersections(self, tol: float = 1e-6) -> list[tuple[np.ndarray, Line, Line]]:
        """Where the lines meet. In elliptic geometry every pair meets exactly once."""
        found: list[tuple[np.ndarray, Line, Line]] = []
        for i, first in enumerate(self.lines):
            n1 = first.normal
            if n1 is None:
                continue
            for second in self.lines[i + 1:]:
                n2 = second.normal
                if n2 is None:
                    continue
                meet = geo.meet_vector(n1, n2)
                if meet is None:  # the same line twice
                    continue
                if any(geo.distance(meet, geo.lift(*seen)) < tol for seen, _, _ in found):
                    continue
                found.append((meet[:2].copy(), first, second))
        return found
