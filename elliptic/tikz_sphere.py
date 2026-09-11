r"""Export the current sphere view as editable native TikZ in a .txt snippet.

The camera projects the sphere onto the page, with rear curves faded through a
translucent ball and the disk construction drawn in the equatorial plane. Only
``\usepackage{tikz}`` is needed; there are no raster images or extra libraries.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from . import geometry as geo
from . import scene as sc
from . import sphere
from .model import Construction
from .tikz import MARGIN, SIZE, Sheet, _escape, _xy

SAMPLES = 181
PX_MM = 0.18  # physical sizes stay legible independently of the sphere zoom
DEFAULT_FLAGS = {"labels": True, "poles": False, "meets": True, "rim": True,
                 "plain": False, "rays": True, "antipodes": False}


def _label(text: str) -> str:
    """Escape literal labels, translating mathematical Unicode for pdfLaTeX."""
    symbols = {"°": r"\ensuremath{{}^{\circ}}", "π": r"\ensuremath{\pi}",
               "△": r"\ensuremath{\triangle}", "Δ": r"\ensuremath{\Delta}",
               "α": r"\ensuremath{\alpha}", "β": r"\ensuremath{\beta}",
               "γ": r"\ensuremath{\gamma}", "θ": r"\ensuremath{\theta}",
               "φ": r"\ensuremath{\phi}", "λ": r"\ensuremath{\lambda}",
               "Σ": r"\ensuremath{\Sigma}", "∑": r"\ensuremath{\sum}",
               "×": r"\ensuremath{\times}", "·": r"\ensuremath{\cdot}",
               "−": "-", "–": "--", "—": "---",
               "≈": r"\ensuremath{\approx}", "≤": r"\ensuremath{\leq}",
               "≥": r"\ensuremath{\geq}", "∞": r"\ensuremath{\infty}",
               "′": r"\ensuremath{\prime}", "″": r"\ensuremath{\prime\prime}"}
    return r"\\".join("".join(symbols.get(char, _escape(char)) for char in line)
                         for line in text.splitlines())


class SphereSheet(Sheet):
    def __init__(self, size, margin, plain, projection, azimuth, elevation, zoom):
        super().__init__(size, margin, plain, projection)
        if not np.isfinite([azimuth, elevation, zoom]).all() or zoom <= 0:
            raise ValueError("camera angles must be finite and zoom must be positive")
        self.radius = self.radius / sphere.MARGIN * zoom
        self.right, self.up, self.towards = sphere.camera(azimuth, elevation)
        self.elevation = elevation

    def color(self, color: str) -> str:
        if not self.plain:
            return super().color(color)
        if color == sc.PLAIN_INK:
            return "black"
        # Keep the shaded ball and contextual wires gray in a plain export.
        rgb = np.array([int(color[i:i + 2], 16) for i in (1, 3, 5)]) / 255
        darkness = int(round(100 * (1 - float(rgb @ [0.2126, 0.7152, 0.0722]))))
        return "black" if darkness == 100 else "white" if darkness == 0 else f"black!{darkness}"

    def project(self, points) -> np.ndarray:
        points = np.atleast_2d(np.asarray(points, dtype=float))
        return np.column_stack([points @ self.right, points @ self.up])

    def stroke(self, color, width, style=sc.SOLID, alpha=1.0) -> str:
        options = [f"draw={self.color(color)}", f"line width={width * PX_MM:.4f}mm",
                   f"draw opacity={alpha:.4f}"]
        if style == sc.DASH:
            options.append(f"dash pattern=on {5 * PX_MM:.3f}mm off {4 * PX_MM:.3f}mm")
        elif style == sc.DOT:
            options.append(f"dash pattern=on {1.6 * PX_MM:.3f}mm off {3.2 * PX_MM:.3f}mm")
        return ", ".join(options)

    def path(self, points, color, width, style=sc.SOLID, alpha=1.0,
             max_step=None) -> None:
        """Draw finite runs; a folded disk path must not gain a spurious chord."""
        points = np.asarray(points, dtype=float)
        run = []
        pen = self.stroke(color, width, style, alpha)
        for point in points:
            if not np.isfinite(point).all():
                self.polyline(run, pen)
                run = []
                continue
            if run and max_step is not None and np.abs(point - run[-1]).sum() > max_step:
                self.polyline(run, pen)
                run = []
            run.append(point)
        self.polyline(run, pen)

    def wire(self, points, front, color, width, alpha) -> None:
        for piece, is_front in sphere.split_at_silhouette(points, self.towards):
            if is_front == front:
                self.path(self.project(piece), color, width, alpha=alpha)

    def graticule(self, front: bool) -> None:
        self.comment("front graticule" if front else "back graticule")
        strength = 1.0 if front else 0.55
        wire = "#3f4756" if self.plain else sphere.COL_WIRE
        for longitude in np.linspace(0.0, np.pi, 6, endpoint=False):
            self.wire(sphere.great_circle([-np.sin(longitude), np.cos(longitude), 0.0]),
                      front, wire, 0.7, 0.30 * strength)
        for height in (0.5, 0.866):
            for sign, alpha in ((1.0, 0.34), (-1.0, 0.14)):
                self.wire(sphere.parallel(sign * height), front, wire, 0.7, alpha * strength)
        self.wire(sphere.great_circle([0.0, 0.0, 1.0]), front,
                  sphere.COL_EQUATOR, 1.8, 1.0 if front else 0.35)

    def curves(self, scene: sc.Scene, front: bool) -> None:
        self.comment("front construction" if front else "back construction")
        for curve in sorted(scene.curves, key=lambda c: c.layer):
            for piece, is_front in sphere.split_at_silhouette(curve.points, self.towards):
                if is_front == front:
                    self.path(self.project(piece), curve.color, curve.width, curve.style,
                              curve.alpha * (1.0 if front else sphere.BACK))

    def ball(self) -> None:
        self.comment("sphere")
        middle, outer = self.color("#dfe6ef"), self.color("#93a3b8")
        edge = self.stroke("#6d7889", 1.1, alpha=0.55)
        self.raw(r"\pgfdeclareradialshading{ellipticSphere}{\pgfpoint{-10bp}{12bp}}{" +
                 f"color(0bp)=(white); color(27.5bp)=({middle}); color(50bp)=({outer})" + "}")
        self.raw(r"\shade[shading=ellipticSphere, opacity=0.58] "
                 "(0,0) circle[radius=1];")
        self.raw(f"\\draw[{edge}] (0,0) circle[radius=1];")
        self.comment("upper hemisphere")
        cap = self.color("#e8b34a")
        self.raw(f"\\fill[fill={cap}, fill opacity=0.11] " +
                 " -- ".join(map(_xy, sphere.cap_outline(self.elevation))) + " -- cycle;")

    def plate(self, scene: sc.Scene) -> None:
        self.comment("equatorial disk")
        outline = self.project(sphere.great_circle([0.0, 0.0, 1.0], 160))
        color = self.color(sphere.COL_PLATE)
        self.raw(f"\\fill[fill={color}, fill opacity=0.10] " +
                 " -- ".join(map(_xy, outline)) + " -- cycle;")
        self.path(outline, sphere.COL_PLATE, 1.2, sc.DASH, 0.7)
        self.comment("flattened construction")
        for curve in scene.curves:
            landed = np.column_stack([self.projection.project(curve.points),
                                      np.zeros(len(curve.points))])
            self.path(self.project(landed), curve.color, max(0.8, curve.width * 0.6),
                      curve.style, curve.alpha * sphere.PLATE, max_step=0.5)
        for mark in scene.marks:
            if mark.shape in ("dot", "diamond"):
                self.marker(self.project(self.projection.landing(mark.point))[0],
                            "ring", mark.color, mark.size * 0.7, 1.2, 0.7)

    def rays(self, scene: sc.Scene) -> None:
        self.comment("projectors")
        for mark in scene.marks:
            if mark.shape in ("dot", "diamond"):
                self.path(self.project(self.projection.ray(mark.point)),
                          sphere.COL_RAY, 1.0, sc.DOT, 0.75)

    def antipodes(self, scene: sc.Scene) -> None:
        self.comment("antipodes")
        for curve in scene.curves:
            for piece, front in sphere.split_at_silhouette(-curve.points, self.towards):
                self.path(self.project(piece), curve.color, curve.width * 0.7,
                          sc.DASH, 0.35 if front else 0.15)
        for mark in scene.marks:
            if mark.shape in ("dot", "diamond"):
                here = np.asarray(mark.point, dtype=float)
                self.path(self.project([here, -here]), sphere.COL_RAY, 0.9, sc.DOT, 0.5)
                self.marker(self.project(-here)[0], "ring", mark.color,
                            mark.size * 0.8, 1.2, 0.5)

    def marker(self, xy, shape, color, size, width, alpha) -> None:
        self.comment(f"{shape} marker")
        ink = self.color(color)
        r = size * PX_MM / (2 * self.radius)
        pen = self.stroke(color, width, alpha=alpha)
        white_pen = self.stroke(sphere.COL_PAPER, width, alpha=alpha)
        x, y = xy
        if shape == "dot":
            self.raw(f"\\draw[{white_pen}, fill={ink}, fill opacity={alpha:.4f}] "
                     f"{_xy(xy)} circle[radius={r:.7f}];")
        elif shape == "ring":
            self.raw(f"\\draw[{pen}] {_xy(xy)} circle[radius={r:.7f}];")
        elif shape == "diamond":
            corners = [(x, y + r), (x + r, y), (x, y - r), (x - r, y)]
            self.raw(f"\\draw[{pen}, fill=white] " +
                     " -- ".join(map(_xy, corners)) + " -- cycle;")
        elif shape == "square":
            self.raw(f"\\draw[{white_pen}, fill={ink}, fill opacity={alpha:.4f}] "
                     f"{_xy((x - r, y - r))} rectangle {_xy((x + r, y + r))};")
        elif shape == "star":
            angles = np.pi / 2 + np.arange(10) * np.pi / 5
            radii = np.where(np.arange(10) % 2 == 0, r, r * 0.42)
            points = xy + radii[:, None] * np.column_stack([np.cos(angles), np.sin(angles)])
            self.raw(f"\\fill[fill={ink}, fill opacity={alpha:.4f}] " +
                     " -- ".join(map(_xy, points)) + " -- cycle;")
        elif shape == "cross":
            for sign in (-1, 1):
                self.polyline([(x - r, y - sign * r), (x + r, y + sign * r)], pen)
        else:
            raise ValueError(f"unknown marker shape: {shape}")

    def marks(self, scene: sc.Scene) -> None:
        self.comment("point markers")
        for i, mark in enumerate(sorted(scene.marks, key=lambda m: m.layer)):
            xy = self.project(mark.point)[0]
            front = float(mark.point @ self.towards) >= 0
            self.raw(f"\\coordinate (sphereMark{i}) at {_xy(xy)};")
            self.marker(xy, mark.shape, mark.color, mark.size, mark.width,
                        mark.alpha * (1.0 if front else sphere.BACK))
        self.comment("front labels")
        for text in sorted(scene.texts, key=lambda t: t.layer):
            here = np.asarray(text.point, dtype=float)
            if float(here @ self.towards) < 0:
                continue
            if text.radial:
                flat = float(np.hypot(here[0], here[1]))
                if flat > 1e-9:
                    here = here + np.array([here[0], here[1], 0.0]) * (text.radial / flat)
            xy = self.project(here)[0] + text.offset
            color = self.color(text.color)
            size = text.size * 0.92 * 0.75
            font = rf"\fontsize{{{size:.2f}pt}}{{{size * 1.4:.2f}pt}}\selectfont"
            font += r"\itshape" if text.italic else ""
            font += r"\bfseries" if text.bold else ""
            anchor, align = ("center", "center") if text.centred else ("west", "left")
            self.raw(f"\\node[text={color}, anchor={anchor}, align={align}, inner sep=0pt, "
                     f"font={{{font}}}] at {_xy(xy)} {{{_label(text.text)}}};")


def to_tikz(construction: Construction, size: float = SIZE, margin: float = MARGIN,
            title: str | None = None, plain: bool = False,
            projection: geo.Projection = geo.ORTHOGONAL, flags: dict | None = None,
            azimuth: float = sphere.HOME[0], elevation: float = sphere.HOME[1],
            zoom: float = sphere.HOME[2]) -> str:
    """Return the 3-D view as a TikZ picture; camera angles are in radians.

    ``flags`` accepts the viewer's labels, poles, meets, rim, rays, antipodes and
    plain settings. Explicit ``plain=True`` also enables monochrome rendering.
    """
    options = dict(DEFAULT_FLAGS)
    options.update(flags or {})
    options["plain"] = bool(plain or options["plain"])
    sheet = SphereSheet(size, margin, options["plain"], projection, azimuth, elevation, zoom)
    scene = sc.build(construction, options, samples=SAMPLES)
    sheet.comment(title or "Elliptic geometry, 3-D sphere view")
    sheet.comment(r"Requires \usepackage{tikz}; paste this picture or \input{sphere.txt}.")
    sheet.comment(f"View: {projection.name} - {projection.summary}.")
    sheet.comment(f"Camera: azimuth={azimuth:.7f} rad, elevation={elevation:.7f} rad, "
                  f"zoom={zoom:.7f}")
    sheet.comment("Native vector paths in an orthographic camera; rear curves are translucent.")
    sheet.raw(f"\\begin{{tikzpicture}}[x={sheet.radius:.7f}mm, y={sheet.radius:.7f}mm, "
              r"line cap=round, line join=round, font=\footnotesize]")
    bound = size / (2 * sheet.radius)
    rectangle = f"{_xy((-bound, -bound))} rectangle {_xy((bound, bound))}"
    sheet.raw(f"\\path[use as bounding box] {rectangle};")
    sheet.raw(r"\begin{scope}")
    sheet.raw(f"\\clip {rectangle};")
    sheet.graticule(front=False)
    sheet.curves(scene, front=False)
    sheet.ball()
    sheet.plate(scene)
    if options["rays"]:
        sheet.rays(scene)
    if options["antipodes"]:
        sheet.antipodes(scene)
    sheet.graticule(front=True)
    sheet.curves(scene, front=True)
    sheet.marks(scene)
    sheet.raw(r"\end{scope}")
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
    target.write_text(to_tikz(construction, **kwargs), encoding="utf-8")
    return str(target)
