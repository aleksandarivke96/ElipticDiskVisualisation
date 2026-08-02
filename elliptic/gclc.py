"""Export a construction to GCLC.

GCLC - "Geometry Constructions -> LaTeX Converter" - is Predrag Janicic's
language and tool for describing geometric constructions (University of
Belgrade).  A `.gcl` file is compiled to a picture:

    gclc drawing.gcl              -> a LaTeX picture
    gclc -svg drawing.gcl         -> SVG        (also -tikz, -pst, -eps)

The curves come out as curves.  A great circle projects to an *ellipse* about
the centre of the disk - semi-major axis 1, semi-minor axis |n_z| - and an
elliptic line is exactly half of it, so each line is one `drawellipsearc` and
each segment one `drawellipsearc2`, rather than a few hundred little straight
pieces.  Two degenerate cases are not ellipses and say so themselves: n_z = 0
is a diameter, drawn straight, and the equator is the rim circle itself.

Everything is written in the model's own coordinates.  GCLC's Cartesian layer
(`ang_origin`, `ang_unit`, `ang_point`) puts the unit disk on the page, so the
numbers in the file are the numbers in the construction, not millimetres.

GCLC has no transparency, so what the viewer draws faintly is written here as a
paler shade of the same colour.  The measurements that have no GCLC home - a
triangle's angles and its area - are written into the comments, where they
travel with the file anyway.
"""

from __future__ import annotations

import numpy as np

from . import geometry as geo
from .model import Construction, Line, Point, Triangle

SIZE = 100.0          # dim SIZE SIZE; GCLC measures its picture in mm
MARGIN = 7.0          # room around the disk for labels
DECOR_SAMPLES = 25    # samples along a right-angle mark or an angle arc
MIN_STEP = 0.4        # mm; samples nearer than this to the last one are dropped
FAINT = 0.72          # how far to fade a colour that the viewer draws faintly

RIM_COLOR = "#3f4756"


def _rgb(color: str, fade: float = 0.0) -> str:
    """`#1a9e6a` -> `26 158 106`, faded towards white, which is how GCLC wants it."""
    color = color.lstrip("#")
    channels = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    return " ".join(str(round(v + (255 - v) * fade)) for v in channels)


def _corner(xy) -> str:
    """Which way to hang a label so it points away from the middle of the disk."""
    return f"cmark_{'r' if xy[0] >= 0 else 'l'}{'t' if xy[1] >= 0 else 'b'}"


def _ccw_degrees(start, end) -> float:
    """How far counterclockwise `end` lies from `start`, seen from the centre."""
    turn = np.degrees(np.arctan2(end[1], end[0]) - np.arctan2(start[1], start[0]))
    return float(turn % 360.0)


class Sheet:
    """The GCLC file being written, and the disk-to-picture mapping."""

    def __init__(self, size: float = SIZE, margin: float = MARGIN, plain: bool = False):
        self.size = size
        self.radius = size / 2.0 - margin
        self.plain = plain  # no colour at all: black ink, construction lines dashed
        self.lines: list[str] = []
        self._names = 0

    # --------------------------------------------------------------- writing

    def raw(self, text: str = "") -> None:
        self.lines.append(text)

    def comment(self, text: str = "") -> None:
        self.raw(f"% {text}" if text else "%")

    def color(self, color: str, fade: float = 0.0) -> None:
        if self.plain:  # say nothing and gclc keeps drawing in black
            return
        self.raw(f"color {_rgb(color, fade)}")

    def thickness(self, width: float) -> None:
        self.raw(f"linethickness {width:.2f}")

    def text(self) -> str:
        return "\n".join(self.lines).rstrip() + "\n"

    # --------------------------------------------------------------- points

    def place(self, xy) -> tuple[float, float]:
        """Disk coordinates -> picture coordinates in mm, which is what
        `ang_origin` and `ang_unit` tell GCLC to do with an `ang_point`."""
        half = self.size / 2.0
        return (half + self.radius * float(xy[0]), half + self.radius * float(xy[1]))

    def point(self, name: str, xy) -> str:
        self.raw(f"ang_point {name} {float(xy[0]):.5f} {float(xy[1]):.5f}")
        return name

    def spare_point(self, xy) -> str:
        """A point that only exists to be an argument, under a name of its own."""
        self._names += 1
        return self.point(f"k{self._names}", xy)

    def polyline(self, path, dashed: bool = False) -> None:
        """A short curve with no formula behind it, as a chain of segments."""
        kept = _thin([tuple(xy) for xy in np.asarray(path, dtype=float)],
                     MIN_STEP / self.radius)
        if len(kept) < 2:
            return
        names = [self.spare_point(xy) for xy in kept]
        draw = "drawdashsegment" if dashed else "drawsegment"
        for start, end in zip(names, names[1:]):
            self.raw(f"{draw} {start} {end}")

    # --------------------------------------------------------------- curves

    def ellipse(self, label: str, normal: np.ndarray) -> tuple[str, str] | None:
        """Name the ellipse a line projects to, by its two axis ends.

        None for the two lines that are not ellipses - the rim circle and a
        diameter - which the drawing commands below then handle straight.
        """
        axes = geo.line_ellipse(normal)
        if axes is None:
            return None
        rim, minor = axes
        return (self.point(f"{label}End", rim), self.point(f"{label}Min", minor))

    def whole_line(self, normal: np.ndarray, ellipse: tuple[str, str] | None,
                   dashed: bool = False) -> None:
        """The whole of an elliptic line: half an ellipse, or a degenerate case."""
        dash = "dash" if dashed else ""
        if ellipse is not None:
            self.raw(f"draw{dash}ellipsearc Ocentre {ellipse[0]} {ellipse[1]} 180")
        elif geo.is_boundary_line(normal):
            self.raw(f"draw{dash}circle Ocentre Orim")  # the equator is the rim itself
        else:
            ends = geo.line_endpoints(normal)  # n_z = 0: a straight diameter
            self.raw(f"draw{dash}segment {self.spare_point(ends[0])} "
                     f"{self.spare_point(ends[1])}")

    def arc(self, normal: np.ndarray, ellipse: tuple[str, str] | None,
            start, end) -> None:
        """The piece of a line between two of its points."""
        if ellipse is None and geo.is_boundary_line(normal):
            sweep = _ccw_degrees(start, end)
            self.raw(f"drawarc_p Ocentre {self.spare_point(start)} {sweep:.4f}")
            return
        if ellipse is None:  # a piece of a diameter is a straight segment
            self.raw(f"drawsegment {self.spare_point(start)} {self.spare_point(end)}")
            return
        self.ellipse_arc((0.0, 0.0), geo.line_ellipse(normal)[0], ellipse, start, end)

    def ellipse_arc(self, centre, axis, names: tuple[str, str], start, end) -> None:
        """An arc of an already-named ellipse, between two points on it.

        `drawellipsearc2` sweeps counterclockwise from the first axis end, by
        the angle at the centre - so either the arc runs that way or its mirror
        does, and the offset and the sweep are angles measured from the centre.
        """
        centre = np.asarray(centre, dtype=float)
        start, end = np.asarray(start, float) - centre, np.asarray(end, float) - centre
        if _ccw_degrees(start, end) > 180.0:
            start, end = end, start
        offset, sweep = _ccw_degrees(np.asarray(axis, float) - centre, start), \
            _ccw_degrees(start, end)
        if sweep < 1e-4:
            return
        middle = "Ocentre" if not np.any(centre) else self.spare_point(centre)
        self.raw(f"drawellipsearc2 {middle} {names[0]} {names[1]} "
                 f"{offset:.4f} {sweep:.4f}")


def _thin(path: list[tuple[float, float]], min_step: float) -> list[tuple[float, float]]:
    """Drop samples that land on top of the last one they were drawn from."""
    if len(path) < 3:
        return list(path)
    kept = [path[0]]
    for point in path[1:-1]:
        if np.hypot(point[0] - kept[-1][0], point[1] - kept[-1][1]) >= min_step:
            kept.append(point)
    kept.append(path[-1])
    return kept


# ------------------------------------------------------------------ the pieces


def _header(sheet: Sheet, construction: Construction, title: str | None) -> None:
    sheet.comment("-" * 68)
    sheet.comment(title or "Elliptic geometry, closed disk model")
    sheet.comment()
    sheet.comment("Written for GCLC, Predrag Janicic, University of Belgrade:")
    sheet.comment("    gclc  thisfile.gcl        -> LaTeX picture")
    sheet.comment("    gclc -svg thisfile.gcl    -> SVG")
    sheet.comment()
    sheet.comment("The elliptic plane is the sphere with antipodal points identified;")
    sheet.comment("its upper half projects onto the closed unit disk, so opposite")
    sheet.comment("points of the boundary circle are one and the same point.  A line")
    sheet.comment("is a great circle, and a great circle projects to an ellipse about")
    sheet.comment("the centre with semi-axes 1 and |n_z| - so each line below is half")
    sheet.comment("an ellipse, drawn as one arc rather than sampled.")
    sheet.comment()
    sheet.comment("Coordinates are the construction's own: the unit disk sits at")
    sheet.comment(f"radius {sheet.radius:.0f}mm about ({sheet.size / 2:.0f}, "
                  f"{sheet.size / 2:.0f}), which is what ang_origin and ang_unit say.")
    if sheet.plain:
        sheet.comment("Drawn plain: no colour, and the rest of each line dashed.")
    sheet.comment(f"{len(construction.points)} points, {len(construction.lines)} lines, "
                  f"{len(construction.triangles)} triangles")
    sheet.comment("-" * 68)
    sheet.raw()
    sheet.raw(f"dim {sheet.size:.0f} {sheet.size:.0f}")
    sheet.raw()
    sheet.raw(f"ang_picture 0 0 {sheet.size:.0f} {sheet.size:.0f}")
    sheet.raw(f"ang_origin {sheet.size / 2:.0f} {sheet.size / 2:.0f}")
    sheet.raw(f"ang_unit {sheet.radius:.0f}")
    sheet.raw()


def _disk(sheet: Sheet) -> None:
    """The rim, dashed - as in the viewer, where the dashes are the reminder
    that opposite boundary points are one and the same point."""
    sheet.comment("the disk; opposite boundary points are the same point")
    sheet.color(RIM_COLOR)
    sheet.thickness(0.5)
    # not `O` and `R`: the construction's own points are labelled A, B, ... Z
    sheet.point("Ocentre", (0.0, 0.0))
    sheet.point("Orim", (1.0, 0.0))
    sheet.raw("drawdashcircle Ocentre Orim")
    sheet.raw()


def _line(sheet: Sheet, line: Line) -> None:
    normal = line.normal
    if normal is None:
        sheet.comment(f"{line.kind} {line.label} is undetermined - nothing to draw")
        sheet.raw()
        return

    sheet.comment(_describe(line))
    ellipse = sheet.ellipse(line.label, normal)
    if not line.is_partial:
        sheet.color(line.color)
        sheet.thickness(0.5)
        sheet.whole_line(normal, ellipse)
        sheet.raw()
        return

    # the rest of the line, for context: paler where there is colour to fade,
    # dashed where there is not - which is how it would have been drawn by hand
    sheet.color(line.color, FAINT)
    sheet.thickness(0.25)
    sheet.whole_line(normal, ellipse, dashed=sheet.plain)
    sheet.color(line.color)         # the piece the tool actually made
    sheet.thickness(0.9)
    ends = line.endpoints()
    for e1, e2, t0, t1 in (geo.segment_arcs(*ends) if ends is not None else []):
        sheet.arc(normal, ellipse, geo.arc_end(e1, e2, t0), geo.arc_end(e1, e2, t1))
    if line.is_perpendicular:
        _foot(sheet, line, normal)
    sheet.raw()


def _foot(sheet: Sheet, line: Line, normal: np.ndarray) -> None:
    """Where a perpendicular lands, and the right angle it lands at."""
    foot = line.foot
    base_normal = line.base.normal if line.base is not None else None
    if foot is None or base_normal is None:
        return
    sheet.thickness(0.4)
    marker = geo.right_angle_marker(foot, base_normal, normal)
    if marker is not None:
        sheet.polyline(marker)
    sheet.raw(f"drawpoint {sheet.spare_point(foot[:2])}")


def _triangle(sheet: Sheet, triangle: Triangle) -> None:
    """The sides are lines already; this is the measuring, as far as it travels."""
    sheet.comment(_describe(triangle))
    vectors = triangle.vectors()
    if vectors is None:
        sheet.raw()
        return
    sheet.color(triangle.color)
    sheet.thickness(0.3)
    a, b, c = vectors
    for vertex, corner, first, second in zip(vectors, triangle.vertices,
                                             (b, c, a), (c, a, b)):
        # the mark is an arc of the circle at ANGLE_RADIUS about the vertex, and
        # that circle projects to an ellipse of its own - so it is one arc too
        arc = geo.angle_arc(vertex, first, second, samples=DECOR_SAMPLES)
        if arc is None:
            continue
        centre, major, minor = geo.small_circle_ellipse(vertex, geo.ANGLE_RADIUS)
        if np.linalg.norm(minor) < 1e-4:  # the circle is seen edge-on: a stroke
            sheet.polyline(arc)
            continue
        names = (sheet.point(f"{triangle.label}{corner.label}ax", centre + major),
                 sheet.point(f"{triangle.label}{corner.label}ay", centre + minor))
        sheet.ellipse_arc(centre, centre + major, names, arc[0], arc[-1])
    sheet.raw()


def _point(sheet: Sheet, point: Point) -> None:
    xy = point.xy
    if xy is None:
        sheet.comment(f"{point.kind} {point.label} has nowhere to be just now")
        return
    if not point.is_free:
        sheet.comment(f"{point.label} is the {point.source.describe()}")
    sheet.color(point.color)
    sheet.point(point.label, xy)
    sheet.raw(f"{_corner(xy)} {point.label}")


def _describe(obj) -> str:
    """The one-line note that goes above an object, in the file's comments."""
    if isinstance(obj, Triangle):
        angles = obj.angles()
        if angles is None:
            return f"triangle {obj.label}"
        degrees = " ".join(f"{np.degrees(angle):.2f}" for angle in angles)
        area = obj.area()
        excess = (f"area {area:.4f} = the excess over pi (Girard)" if area is not None
                  else "its sides close up through the rim, so it bounds no disk")
        return (f"triangle {obj.label}: angles {degrees} deg, "
                f"sum {np.degrees(sum(angles)):.2f} deg, {excess}")
    shape = _shape(obj.normal)
    if obj.is_perpendicular:
        return (f"perpendicular {obj.label} from {obj.p.label} to {obj.base.label}, "
                f"distance {obj.length():.4f} rad, {shape}")
    if obj.is_polar:
        return (f"polar {obj.label} of {obj.p.label}: everything a quarter turn "
                f"from it, {shape}")
    if obj.is_segment:
        return (f"segment {obj.label} = {obj.p.label}{obj.q.label}, "
                f"length {obj.length():.4f} rad, {shape}")
    return f"line {obj.label} through {obj.p.label} and {obj.q.label}, {shape}"


def _shape(normal: np.ndarray) -> str:
    if geo.is_boundary_line(normal):
        return "the equator, which is the rim circle itself"
    if geo.line_ellipse(normal) is None:
        return "a diameter"
    return f"half an ellipse with semi-minor axis {abs(float(normal[2])):.4f}"


# ------------------------------------------------------------------ the export


def to_gclc(construction: Construction, size: float = SIZE, margin: float = MARGIN,
            title: str | None = None, plain: bool = False) -> str:
    """The whole construction as the text of a GCLC file.

    `plain` draws it the way it would have been drawn on paper: black ink
    throughout, and the rest of a line dashed rather than faint.
    """
    sheet = Sheet(size, margin, plain)
    _header(sheet, construction, title)
    _disk(sheet)
    for line in construction.lines:
        _line(sheet, line)
    for triangle in construction.triangles:
        _triangle(sheet, triangle)
    if construction.points:
        sheet.comment("the points, with their labels")
        sheet.thickness(0.5)
        for point in construction.points:
            _point(sheet, point)
    return sheet.text()


def export(construction: Construction, path: str, **kwargs) -> str:
    """Write the construction to `path`, adding a .gcl suffix if it has none."""
    path = str(path).strip()
    if not path:
        raise ValueError("a file name is needed")
    if "." not in path.rsplit("/", 1)[-1]:
        path += ".gcl"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(to_gclc(construction, **kwargs))
    return path
