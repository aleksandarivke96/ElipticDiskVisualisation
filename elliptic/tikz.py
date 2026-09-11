r"""Export the disk construction as a TikZ picture, saved in a .txt file.

The result can be pasted into a LaTeX document using ``\usepackage{tikz}``,
or included with ``\input{construction.txt}``. No GCLC executable is needed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from . import geometry as geo
from .model import Circle, Construction, Line, Point, Triangle

SIZE = 100.0
MARGIN = 7.0
RIM_COLOR = "#3f4756"
SAMPLES = 257
# Keep arc dimensions comfortably inside TeX's fixed-point dimension range.
# Very large or flat conics use their projected samples instead.
MAX_ARC_MM = 1000.0
FLAT = 1e-4


def _xy(point) -> str:
    return f"({float(point[0]):.7f},{float(point[1]):.7f})"


def _escape(text: str) -> str:
    replacements = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}",
                    "_": r"\_", "%": r"\%", "&": r"\&", "#": r"\#",
                    "$": r"\$", "^": r"\textasciicircum{}",
                    "~": r"\textasciitilde{}"}
    return "".join(replacements.get(char, char) for char in text)


class Sheet:
    """TikZ commands in unit-disk coordinates, with physical pen widths."""

    def __init__(self, size: float, margin: float, plain: bool,
                 projection: geo.Projection):
        if not np.isfinite(size) or not np.isfinite(margin) or not 0 <= margin < size / 2:
            raise ValueError("size must be positive and margin less than half the size")
        self.size = size
        self.radius = size / 2 - margin
        self.plain = plain
        self.projection = projection
        self.lines: list[str] = []
        self.colors: dict[str, str] = {}

    def raw(self, text: str = "") -> None:
        self.lines.append(text)

    def comment(self, text: str) -> None:
        for line in text.splitlines():
            self.raw(f"% {line}")

    def color(self, color: str) -> str:
        if self.plain:
            return "black"
        value = color.lstrip("#").upper()
        if value not in self.colors:
            name = f"ellipticColor{len(self.colors)}"
            self.colors[value] = name
            self.raw(f"\\definecolor{{{name}}}{{HTML}}{{{value}}}")
        return self.colors[value]

    def style(self, color: str, width: float = 0.5, faint: bool = False) -> str:
        options = [f"draw={self.color(color)}", f"line width={width:.2f}mm"]
        if faint:
            options.append("dashed" if self.plain else "draw opacity=0.28")
        return ", ".join(options)

    def polyline(self, path, style: str) -> None:
        if len(path) >= 2:
            self.raw(f"\\draw[{style}] " + " -- ".join(map(_xy, path)) + ";")

    def curve(self, shape, vectors, style: str, closed: bool = False) -> None:
        """Draw a conic arc through the projected start, middle and end.

        TikZ angles are ellipse parameters, not angles of rays from its centre.
        Resolve points along the two axes before measuring the angles. Rotating
        the path around the origin lets its start stay inside the disk even
        when the conic's centre lies far outside it.
        """
        path = self.projection.project(vectors)
        if shape is None:
            self.polyline(path, style)
            return
        centre, major, minor = shape
        a, b = float(np.linalg.norm(major)), float(np.linalg.norm(minor))
        if b < FLAT or max(a, b) * self.radius > MAX_ARC_MM:
            self.polyline(path, style)
            return
        x_axis = major / a
        y_axis = np.array([-x_axis[1], x_axis[0]])
        axes = np.column_stack([x_axis, y_axis])
        angle = float(np.degrees(np.arctan2(x_axis[1], x_axis[0])))
        local = (path[[0, len(path) // 2, -1]] - centre) @ axes / [a, b]
        start, middle, end = np.degrees(np.arctan2(local[:, 1], local[:, 0]))
        sweep = float((end - start) % 360)
        if closed:
            sweep = 360.0
        elif float((middle - start) % 360) > sweep + 1e-7:
            sweep -= 360.0
        if abs(sweep) < 1e-8:
            return
        local_start = path[0] @ axes
        self.raw(f"\\draw[{style}, rotate={angle:.7f}] {_xy(local_start)} "
                 f"arc[start angle={start:.7f}, delta angle={sweep:.7f}, "
                 f"x radius={a:.7f}, y radius={b:.7f}]" +
                 (" -- cycle;" if closed else ";"))

    def whole_line(self, normal, style: str) -> None:
        if geo.is_boundary_line(normal):
            self.raw(f"\\draw[{style}] (0,0) circle[radius=1];")
        elif self.projection.conic(normal) is None:
            self.polyline(geo.line_endpoints(normal), style)
        else:
            self.curve(self.projection.conic(normal),
                       geo.line_vectors(normal, SAMPLES), style)


def _line(sheet: Sheet, line: Line) -> None:
    sheet.comment(f"{line.kind} {line.label}")
    normal = line.normal
    if normal is None:
        sheet.comment("undetermined - nothing to draw")
        return
    if not line.is_partial:
        sheet.whole_line(normal, sheet.style(line.color))
        return
    sheet.whole_line(normal, sheet.style(line.color, 0.25, faint=True))
    shape = sheet.projection.conic(normal)
    if geo.is_boundary_line(normal):
        shape = (np.zeros(2), np.array([1., 0.]), np.array([0., 1.]))
    ends = line.endpoints()
    for arc in geo.segment_arcs(*ends) if ends is not None else []:
        sheet.curve(shape, geo.arc_vectors(*arc, samples=SAMPLES),
                    sheet.style(line.color, 0.9))
    if not line.is_perpendicular:
        return
    foot = line.foot
    base = line.base.normal if line.base is not None else None
    if foot is None or base is None:
        return
    marker = geo.right_angle_marker(foot, base, normal)
    if marker is not None:
        sheet.polyline(sheet.projection.project(marker), sheet.style(line.color, 0.4))
    sheet.raw(f"\\fill[fill={sheet.color(line.color)}] "
              f"{_xy(sheet.projection.project(foot))} circle[radius=0.6mm];")


def _circle(sheet: Sheet, circle: Circle) -> None:
    sheet.comment(f"circle {circle.label} about {circle.centre.label} "
                  f"through {circle.through.label}")
    axis_radius = circle.axis_radius()
    if axis_radius is None:
        sheet.comment("undetermined - nothing to draw")
        return
    centre, radius = axis_radius
    sheet.comment(f"radius {radius:.7f} rad")
    for axis, e1, e2, start, end in geo.circle_arcs(centre, radius):
        sheet.curve(sheet.projection.point_conic(axis, radius),
                    geo.circle_arc_vectors(axis, e1, e2, radius, start, end, SAMPLES),
                    sheet.style(circle.color), closed=end - start > 2 * np.pi - 1e-9)


def _triangle(sheet: Sheet, triangle: Triangle) -> None:
    sheet.comment(f"triangle {triangle.label}")
    angles = triangle.angles()
    if angles is not None:
        sheet.comment("angles " + ", ".join(f"{np.degrees(a):.4f}" for a in angles)
                      + " deg")
        area = triangle.area()
        sheet.comment(f"area {area:.7f} = the excess over pi (Girard)" if area is not None
                      else "its sides close up through the rim, so it bounds no disk")
    vectors = triangle.vectors()
    if vectors is None:
        return
    a, b, c = vectors
    for vertex, first, second in ((a, b, c), (b, c, a), (c, a, b)):
        arc = geo.angle_arc(vertex, first, second, samples=25)
        if arc is not None:
            sheet.curve(sheet.projection.point_conic(vertex, geo.ANGLE_RADIUS),
                        arc, sheet.style(triangle.color, 0.3))


def _point(sheet: Sheet, point: Point, index: int) -> None:
    vector = point.vector
    if vector is None:
        sheet.comment(f"{point.kind} {point.label} is undetermined - nothing to draw")
        return
    xy = sheet.projection.project(vector)
    color = sheet.color(point.color)
    # The model supplies A, B, ..., A1, ...; retain readable coordinate names.
    name = point.label if point.label.isascii() and point.label.isalnum() else f"point{index}"
    sheet.raw(f"\\coordinate ({name}) at {_xy(xy)};")
    sheet.raw(f"\\draw[draw={color}, fill=white, line width=0.3mm] "
              f"({name}) circle[radius=0.8mm];")
    anchor = ("south" if xy[1] >= 0 else "north") + " " + ("west" if xy[0] >= 0 else "east")
    sheet.raw(f"\\node[text={color}, anchor={anchor}, inner sep=2pt] "
              f"at ({name}) " + r"{\textit{" + _escape(point.label) + "}};")


def to_tikz(construction: Construction, size: float = SIZE, margin: float = MARGIN,
            title: str | None = None, plain: bool = False,
            projection: geo.Projection = geo.ORTHOGONAL) -> str:
    """Return an embeddable TikZ picture in the selected projection and style."""
    sheet = Sheet(size, margin, plain, projection)
    sheet.comment(title or "Elliptic geometry, closed disk model")
    sheet.comment(r"Requires \usepackage{tikz}; paste this picture or \input{construction.txt}.")
    sheet.comment(f"View: {projection.name} - {projection.summary}.")
    sheet.comment(f"{len(construction.points)} points, {len(construction.lines)} lines, "
                  f"{len(construction.circles)} circles, {len(construction.triangles)} triangles")
    sheet.raw(f"\\begin{{tikzpicture}}[x={sheet.radius:.7f}mm, y={sheet.radius:.7f}mm, "
              r"line cap=round, line join=round, font=\footnotesize]")
    bound = size / (2 * sheet.radius)
    sheet.raw(f"\\path[use as bounding box] {_xy((-bound, -bound))} "
              f"rectangle {_xy((bound, bound))};")
    sheet.comment("the disk; opposite boundary points are the same point")
    sheet.raw(f"\\draw[{sheet.style(RIM_COLOR)}, dashed] (0,0) circle[radius=1];")
    for line in construction.lines:
        _line(sheet, line)
    for circle in construction.circles:
        _circle(sheet, circle)
    for triangle in construction.triangles:
        _triangle(sheet, triangle)
    for index, point in enumerate(construction.points):
        _point(sheet, point, index)
    sheet.raw(r"\end{tikzpicture}")
    return "\n".join(sheet.lines) + "\n"


def export(construction: Construction, path: str | Path, **kwargs) -> str:
    """Write a UTF-8 TikZ snippet, appending .txt when no suffix is supplied."""
    name = str(path).strip()
    if not name:
        raise ValueError("a file name is needed")
    target = Path(name)
    if not target.suffix:
        target = target.with_suffix(".txt")
    text = to_tikz(construction, **kwargs)
    target.write_text(text, encoding="utf-8")
    return str(target)
