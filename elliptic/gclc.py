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

from pathlib import Path

import numpy as np

from . import geometry as geo
from .model import Circle, Construction, Line, Point, Triangle

SIZE = 100.0          # dim SIZE SIZE; GCLC measures its picture in mm
MARGIN = 7.0          # room around the disk for labels
DECOR_SAMPLES = 25    # samples along a right-angle mark or an angle arc
MIN_STEP = 0.4        # mm; samples nearer than this to the last one are dropped
FAINT = 0.72          # how far to fade a colour that the viewer draws faintly
# the largest and flattest conics worth naming, in disk radii.  GCLC arc angles
# carry four decimals of a degree, and on a conic of radius R that quantisation
# moves a point by up to ~2e-6 R - invisible at R = 500, a tenth of the disk at
# R = 5e4; and an ellipse flatter than FLAT it does not usably render at all.
# Both are the nearly-degenerate bands - a stereographic circle whose section
# almost passes through the south pole, a line that is almost a diameter - and
# both curves sit within max(FLAT, 1/(2 FAR)) of the straight thing the exactly
# degenerate case would draw, so falling back is *more* faithful than the arc.
FAR = 500.0
FLAT = 1e-4

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

    def __init__(self, size: float = SIZE, margin: float = MARGIN, plain: bool = False,
                 projection: geo.Projection = geo.ORTHOGONAL):
        self.size = size
        self.radius = size / 2.0 - margin
        self.plain = plain  # no colour at all: black ink, construction lines dashed
        self.projection = projection
        self.lines: list[str] = []
        self._names = 0
        self._centres: dict[str, np.ndarray] = {"Ocentre": np.zeros(2)}
        self._axes: dict[str, np.ndarray] = {"Ocentre": np.zeros(2)}

    def screen(self, vectors) -> np.ndarray:
        """Points of the sphere -> where the current projection puts them."""
        return self.projection.project(np.asarray(vectors, dtype=float))

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
        xy = np.asarray(xy, dtype=float)
        self._centres[name] = xy
        self._axes[name] = xy
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

    def conic(self, label: str, shape) -> tuple[str, str, str] | None:
        """Name the curve a line or a circle projects to, by centre and axis ends.

        `shape` is what the projection said: (centre, major, minor), or None
        when the image is straight and the caller should draw it straight.
        None too when the conic is bigger than FAR or flatter than FLAT: so
        nearly degenerate that the piece inside the disk is straight to within
        the guard itself, while an arc command on it would scatter real errors
        or draw nothing - the caller's degenerate fallback is then the more
        faithful drawing.
        """
        if (shape is None or float(np.linalg.norm(shape[1])) > FAR
                or float(np.linalg.norm(shape[2])) < FLAT):
            return None
        centre, major, minor = shape
        middle = "Ocentre" if not np.any(centre) else self.point(f"{label}C", centre)
        return (middle,
                self.point(f"{label}X", centre + major),
                self.point(f"{label}Y", centre + minor))

    def whole_line(self, normal: np.ndarray, conic: tuple[str, str, str] | None,
                   dashed: bool = False) -> None:
        """The whole of an elliptic line, from one rim crossing round to the other."""
        dash = "dash" if dashed else ""
        if geo.is_boundary_line(normal):  # the equator is the rim itself
            self.raw(f"draw{dash}circle Ocentre Orim")
            return
        ends = geo.line_endpoints(normal)  # the rim is where both projections agree
        if conic is None:  # n_z = 0: a straight diameter, either way of looking
            self.raw(f"draw{dash}segment {self.spare_point(ends[0])} "
                     f"{self.spare_point(ends[1])}")
            return
        e1, e2, t0, t1 = geo.line_arc(normal)
        middle = self.screen(geo.arc_end_vector(e1, e2, 0.5 * (t0 + t1)))
        self.conic_arc(conic, self.screen(geo.arc_end_vector(e1, e2, t0)),
                       self.screen(geo.arc_end_vector(e1, e2, t1)), middle, dashed)

    def arc(self, normal: np.ndarray, conic: tuple[str, str, str] | None,
            start, end, through) -> None:
        """The piece of a line between two of its points, given in the disk."""
        if conic is None and geo.is_boundary_line(normal):
            sweep = _ccw_degrees(start, end)
            if _ccw_degrees(start, through) > sweep:
                start, end = end, start
                sweep = _ccw_degrees(start, end)
            self.raw(f"drawarc_p Ocentre {self.spare_point(start)} {sweep:.4f}")
            return
        if conic is None:  # a piece of a diameter is a straight segment
            self.raw(f"drawsegment {self.spare_point(start)} {self.spare_point(end)}")
            return
        self.conic_arc(conic, start, end, through)

    def conic_arc(self, names: tuple[str, str, str], start, end, through,
                  dashed: bool = False) -> None:
        """An arc of an already-named conic, between two points on it.

        `drawellipsearc2` sweeps counterclockwise from the first axis end, by
        the angle at the centre - so the arc runs that way or its mirror does,
        and `through` says which of the two is the one wanted.
        """
        centre = self._centres[names[0]]
        start, end = np.asarray(start, float) - centre, np.asarray(end, float) - centre
        through = np.asarray(through, dtype=float) - centre
        sweep = _ccw_degrees(start, end)
        if _ccw_degrees(start, through) > sweep:  # it goes round the other way
            start, end = end, start
            sweep = _ccw_degrees(start, end)
        if sweep < 1e-4:
            return
        offset = _ccw_degrees(self._axes[names[1]] - centre, start)
        dash = "dash" if dashed else ""
        self.raw(f"draw{dash}ellipsearc2 {names[0]} {names[1]} {names[2]} "
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
    sheet.comment(f"View: {sheet.projection.name} - {sheet.projection.summary}.")
    sheet.comment("Coordinates are the construction's own: the unit disk sits at")
    sheet.comment(f"radius {sheet.radius:.0f}mm about ({sheet.size / 2:.0f}, "
                  f"{sheet.size / 2:.0f}), which is what ang_origin and ang_unit say.")
    if sheet.plain:
        sheet.comment("Drawn plain: no colour, and the rest of each line dashed.")
    sheet.comment(f"{len(construction.points)} points, {len(construction.lines)} lines, "
                  f"{len(construction.circles)} circles, "
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

    sheet.comment(_describe(line, sheet.projection))
    conic = sheet.conic(line.label, sheet.projection.conic(normal))
    if not line.is_partial:
        sheet.color(line.color)
        sheet.thickness(0.5)
        sheet.whole_line(normal, conic)
        sheet.raw()
        return

    # the rest of the line, for context: paler where there is colour to fade,
    # dashed where there is not - which is how it would have been drawn by hand
    sheet.color(line.color, FAINT)
    sheet.thickness(0.25)
    sheet.whole_line(normal, conic, dashed=sheet.plain)
    sheet.color(line.color)         # the piece the tool actually made
    sheet.thickness(0.9)
    ends = line.endpoints()
    for e1, e2, t0, t1 in (geo.segment_arcs(*ends) if ends is not None else []):
        sheet.arc(normal, conic,
                  sheet.screen(geo.arc_end_vector(e1, e2, t0)),
                  sheet.screen(geo.arc_end_vector(e1, e2, t1)),
                  sheet.screen(geo.arc_end_vector(e1, e2, 0.5 * (t0 + t1))))
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
        sheet.polyline(sheet.screen(marker))
    sheet.raw(f"drawpoint {sheet.spare_point(sheet.screen(foot))}")


def _circle(sheet: Sheet, circle: Circle) -> None:
    """One or two arcs: a circle that dips below the equator folds up and
    re-enters the disk on the far side, exactly as a long segment does."""
    axis_radius = circle.axis_radius()
    if axis_radius is None:
        sheet.comment(f"circle {circle.label} is undetermined - nothing to draw")
        sheet.raw()
        return
    sheet.comment(_describe(circle, sheet.projection))
    sheet.color(circle.color)
    sheet.thickness(0.5)
    centre_vector, radius = axis_radius
    for index, (axis, e1, e2, t0, t1) in enumerate(geo.circle_arcs(centre_vector,
                                                                   radius)):
        # the folded piece gets its own conic, around the antipodal axis; the F
        # keeps its names clear of every line's, which are lowercase throughout
        label = circle.label if index == 0 else f"{circle.label}F"
        names = sheet.conic(label, sheet.projection.point_conic(axis, radius))
        if names is None:  # straight, edge-on, or too outsized to arc exactly
            sheet.polyline(sheet.screen(
                geo.circle_arc_vectors(axis, e1, e2, radius, t0, t1)))
            continue
        if t1 - t0 > 2.0 * np.pi - 1e-9:  # never leaves this side: closed
            sheet.raw(f"drawellipse {names[0]} {names[1]} {names[2]}")
            continue
        sheet.conic_arc(names,
                        sheet.screen(geo.circle_point(axis, e1, e2, radius, t0)),
                        sheet.screen(geo.circle_point(axis, e1, e2, radius, t1)),
                        sheet.screen(geo.circle_point(axis, e1, e2, radius,
                                                      0.5 * (t0 + t1))))
    sheet.raw()


def _triangle(sheet: Sheet, triangle: Triangle) -> None:
    """The sides are lines already; this is the measuring, as far as it travels."""
    sheet.comment(_describe(triangle, sheet.projection))
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
        # a circle projects to a conic of its own - so it is one arc too
        arc = geo.angle_arc(vertex, first, second, samples=DECOR_SAMPLES)
        if arc is None:
            continue
        drawn = sheet.screen(arc)
        names = sheet.conic(f"{triangle.label}{corner.label}a",
                            sheet.projection.point_conic(vertex, geo.ANGLE_RADIUS))
        if names is None:  # edge-on or outsized: a stroke
            sheet.polyline(drawn)
            continue
        sheet.conic_arc(names, drawn[0], drawn[-1], drawn[len(drawn) // 2])
    sheet.raw()


def _point(sheet: Sheet, point: Point) -> None:
    xy = point.xy
    if xy is None:
        sheet.comment(f"{point.kind} {point.label} has nowhere to be just now")
        return
    if not point.is_free:
        sheet.comment(f"{point.label} is the {point.source.describe()}")
    sheet.color(point.color)
    drawn = sheet.screen(point.vector)
    sheet.point(point.label, drawn)
    sheet.raw(f"{_corner(drawn)} {point.label}")


def _describe(obj, projection: geo.Projection = geo.ORTHOGONAL) -> str:
    """The one-line note that goes above an object, in the file's comments."""
    if isinstance(obj, Circle):
        radius = obj.radius()
        note = (", which makes it the polar line of its centre"
                if radius is not None and abs(radius - geo.HALF_PI) < 1e-4 else "")
        return (f"circle {obj.label} about {obj.centre.label} through "
                f"{obj.through.label}, radius {radius:.4f} rad{note}")
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
    shape = _shape(obj.normal, projection)
    if obj.is_perpendicular:
        return (f"perpendicular {obj.label} from {obj.p.label} to {obj.base.label}, "
                f"distance {obj.length():.4f} rad, {shape}")
    if obj.is_polar:
        return (f"polar {obj.label} of {obj.p.label}: everything a quarter turn "
                f"from it, {shape}")
    if obj.is_bisector:
        return (f"bisector {obj.label} of {obj.base.label} and {obj.other.label}: "
                f"equal angles with both, through their meet, {shape}")
    if obj.is_segment:
        return (f"segment {obj.label} = {obj.p.label}{obj.q.label}, "
                f"length {obj.length():.4f} rad, {shape}")
    return f"line {obj.label} through {obj.p.label} and {obj.q.label}, {shape}"


def _shape(normal: np.ndarray, projection: geo.Projection) -> str:
    if geo.is_boundary_line(normal):
        return "the equator, which is the rim circle itself"
    shape = projection.conic(normal)
    if shape is None:
        return "a diameter"
    _, major, minor = shape
    if abs(np.linalg.norm(major) - np.linalg.norm(minor)) < 1e-9:
        return f"an arc of a circle of radius {np.linalg.norm(major):.4f}"
    return f"half an ellipse with semi-minor axis {np.linalg.norm(minor):.4f}"


# ------------------------------------------------------------------ the export


def to_gclc(construction: Construction, size: float = SIZE, margin: float = MARGIN,
            title: str | None = None, plain: bool = False,
            projection: geo.Projection = geo.ORTHOGONAL) -> str:
    """The whole construction as the text of a GCLC file.

    `plain` draws it the way it would have been drawn on paper: black ink
    throughout, and the rest of a line dashed rather than faint.  `projection`
    picks the view - the same construction seen straight down or from the south
    pole, which is the difference between elliptical and circular arcs.
    """
    sheet = Sheet(size, margin, plain, projection)
    _header(sheet, construction, title)
    _disk(sheet)
    for line in construction.lines:
        _line(sheet, line)
    for circle in construction.circles:
        _circle(sheet, circle)
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
    if not Path(path).suffix:
        path += ".gcl"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(to_gclc(construction, **kwargs))
    return path
