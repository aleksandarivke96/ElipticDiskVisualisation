"""What a construction looks like, before anything decides how to draw it.

A `Scene` is a flat list of primitives positioned by *points of the sphere* -
a `(3,)` unit vector, or an `(N, 3)` array of them for a curve.  Nothing in here
knows about the disk, the page or the screen.

That is the whole point.  The disk view pushes every vector through a
`geo.Projection`; the sphere view pushes the same vectors through a camera; both
therefore draw the same construction, and a feature added once shows up in both.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import geometry as geo
from .model import Construction, Line, Point, Triangle

PLAIN_INK = "#111111"
PLAIN_FAINT = "#8a8f98"
COL_MEET = "#111827"

SOLID, DASH, DOT = "solid", "dash", "dot"


@dataclass
class Curve:
    """A polyline on the sphere."""

    points: np.ndarray            # (N, 3)
    color: str
    width: float = 1.5            # pixels
    style: str = SOLID
    alpha: float = 1.0
    layer: int = 3


@dataclass
class Mark:
    """A single point of the sphere, drawn as a symbol."""

    point: np.ndarray             # (3,)
    shape: str                    # dot | diamond | ring | star | square | cross
    color: str
    size: float = 9.0             # pixels across
    width: float = 1.5
    alpha: float = 1.0
    layer: int = 6


@dataclass
class Text:
    """A label hung on a point of the sphere."""

    point: np.ndarray             # (3,)
    text: str
    color: str
    size: float = 10.0
    italic: bool = False
    bold: bool = False
    offset: tuple[float, float] = (0.0, 0.0)  # view units, x right and y up
    radial: float = 0.0                       # extra push away from the centre
    centred: bool = True
    layer: int = 7


@dataclass
class Scene:
    curves: list[Curve] = field(default_factory=list)
    marks: list[Mark] = field(default_factory=list)
    texts: list[Text] = field(default_factory=list)

    def add(self, item) -> None:
        {Curve: self.curves, Mark: self.marks, Text: self.texts}[type(item)].append(item)

    def __len__(self) -> int:
        return len(self.curves) + len(self.marks) + len(self.texts)


def line_curves(line: Line, samples: int = 512) -> list[np.ndarray]:
    """The drawn part of a line, on the sphere, as one or two `(N, 3)` arrays.

    A whole line is one half-turn of its great circle.  A segment or a
    perpendicular is the arc between its ends, which arrives in two pieces when
    the shortest route leaves the disk through the rim.
    """
    normal = line.normal
    if normal is None:
        return []
    if not line.is_partial:
        return [geo.line_vectors(normal, samples)]
    ends = line.endpoints()
    if ends is None:
        return []
    return geo.segment_vector_paths(*ends, samples)


def build(construction: Construction, flags: dict, picked=(), samples: int = 512) -> Scene:
    """Everything the current construction wants drawn, in sphere coordinates."""
    return _Builder(construction, flags, list(picked), samples).run()


class _Builder:
    def __init__(self, construction, flags, picked, samples):
        self.construction = construction
        self.flags = flags
        self.picked = picked
        self.samples = samples
        self.plain = bool(flags.get("plain"))
        self.scene = Scene()

    def run(self) -> Scene:
        for line in self.construction.lines:
            self.line(line)
        for triangle in self.construction.triangles:
            self.triangle(triangle)
        if self.flags.get("meets"):
            self.meets()
        for point in self.construction.points:
            self.point(point)
        return self.scene

    # ------------------------------------------------------------------ helpers

    def ink(self, color: str) -> str:
        """An object's colour, or black when the picture is being drawn plain."""
        return PLAIN_INK if self.plain else color

    def held(self, obj) -> bool:
        return any(obj is other for other in self.picked)

    def add(self, item):
        self.scene.add(item)
        return item

    # ------------------------------------------------------------------ lines

    def line(self, line: Line) -> None:
        normal = line.normal
        if normal is None:
            return
        ink = self.ink(line.color)
        paths = line_curves(line, self.samples)

        if self.held(line):  # a halo round the line waiting for its partner
            for path in paths:
                self.add(Curve(path, ink, width=9.0, alpha=0.25, layer=2))

        if self.plain:  # weight carries what colour otherwise would
            width = 2.6 if line.is_partial else 1.3
        else:
            width = 3.4 if line.is_partial else 2.0
        for path in paths:
            self.add(Curve(path, ink, width=width, layer=3))

        if line.is_partial:  # the rest of the line: faint, or dashed when plain
            whole = geo.line_vectors(normal, self.samples)
            self.add(Curve(whole,
                           PLAIN_FAINT if self.plain else line.color,
                           width=0.9 if self.plain else 1.1,
                           style=DASH if self.plain else SOLID,
                           alpha=1.0 if self.plain else 0.28, layer=2))

        if line.is_perpendicular:
            self.foot(line, normal)

        ends = geo.line_endpoints(normal)
        if ends is not None:
            rim = np.array([[ends[0][0], ends[0][1], 0.0],
                            [ends[1][0], ends[1][1], 0.0]])
            if self.flags.get("rim"):
                for end in rim:
                    self.add(Mark(end, "ring", ink, size=9.0, width=1.6, layer=4))
                self.add(Curve(rim, ink, width=0.9, style=DOT, alpha=0.4, layer=1))
            if self.flags.get("labels"):
                self.add(Text(rim[0], line.label, ink, size=10.0, italic=True,
                              radial=0.09))

        if self.flags.get("poles"):
            self.add(Mark(geo.pole_vector(normal), "star", ink,
                          size=14.0, alpha=0.9, layer=4))

    def foot(self, line: Line, normal: np.ndarray) -> None:
        """The landing point, plus a right-angle mark as the projection sees it."""
        foot = line.foot
        base_normal = line.base.normal if line.base is not None else None
        if foot is None or base_normal is None:
            return
        ink = self.ink(line.color)
        self.add(Mark(foot, "square", ink, size=7.0, layer=5))
        marker = geo.right_angle_marker(foot, base_normal, normal)
        if marker is not None:
            self.add(Curve(marker, ink, width=1.4, alpha=0.9, layer=4))

    # ------------------------------------------------------------------ triangles

    def triangle(self, triangle: Triangle) -> None:
        """The sides are ordinary lines and draw themselves; this is the measuring."""
        vectors = triangle.vectors()
        if vectors is None:
            return
        a, b, c = vectors
        ink = self.ink(triangle.color)
        for vertex, first, second in ((a, b, c), (b, c, a), (c, a, b)):
            arc = geo.angle_arc(vertex, first, second)
            if arc is not None:
                self.add(Curve(arc, ink, width=1.0 if self.plain else 1.4,
                               alpha=0.85, layer=4))
        centre = triangle.centre()
        if centre is None or not self.flags.get("labels"):
            return
        self.add(Text(centre, triangle_text(triangle), ink, size=8.5, layer=7))

    # ------------------------------------------------------------------ the rest

    def meets(self) -> None:
        """Crossings that no point of the construction already names."""
        named = [p.vector for p in self.construction.points if p.vector is not None]
        for _, first, second in self.construction.intersections():
            v = geo.meet_vector(first.normal, second.normal)
            if v is None or any(geo.distance(v, other) < 1e-6 for other in named):
                continue
            self.add(Mark(v, "cross", COL_MEET, size=9.0, width=1.8,
                          alpha=0.85, layer=5))

    def point(self, point: Point) -> None:
        vector = point.vector
        if vector is None:  # a meet of two lines that have fallen together
            return
        ink = self.ink(point.color)
        if point.is_free:
            self.add(Mark(vector, "dot", ink, size=7.0 if self.plain else 10.0,
                          width=0.6 if self.plain else 1.2, layer=6))
        else:  # derived: hollow, to say it is not yours to drag
            self.add(Mark(vector, "diamond", ink, size=7.0 if self.plain else 9.0,
                          width=1.4 if self.plain else 2.0, layer=6))
        if self.held(point):
            self.add(Mark(vector, "ring", ink, size=21.0, width=2.0, layer=6))
        if self.flags.get("labels"):
            self.add(Text(vector, point.label, ink, size=11.0,
                          italic=self.plain, bold=not self.plain,
                          offset=(0.040, 0.030), centred=False))


def triangle_text(triangle: Triangle) -> str:
    """The little readout hung in the middle of a triangle."""
    angles = triangle.angles()
    if angles is None:
        return triangle.label
    area = triangle.area()
    excess = "sides loop through the rim" if area is None else f"area {area:.3f}"
    return f"{triangle.label}\nangles {np.degrees(sum(angles)):.1f}deg\n{excess}"
