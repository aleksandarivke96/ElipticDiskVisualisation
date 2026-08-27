"""The sphere the disk is a picture of.

The disk is the upper hemisphere flattened out, and this pane un-flattens it:
the same construction, drawn on the ball it actually lives on, with the disk
lying in the equatorial plane underneath it and dotted sight lines showing which
point of the sphere became which point of the disk.  Drag a point on the left
and watch the great circle swing round on the right.

The camera is orthographic, which makes hidden-surface removal exact and free -
a point `v` of the unit sphere is in front exactly when `v . d > 0`, where `d`
points from the centre towards the camera.  Curves are cut on that boundary, and
the back of each one is drawn through a translucent ball.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QPainter, QPainterPath, QRadialGradient
from PySide6.QtWidgets import QWidget

from .. import geometry as geo
from .. import scene as sc
from . import paint

COL_WIRE = "#9aa4b4"
COL_EQUATOR = "#3f4756"
COL_PLATE = "#6f7c90"
COL_RAY = "#8a93a3"
COL_PAPER = "#ffffff"
COL_HINT = "#98a0ac"

MARGIN = 1.28
BACK = 0.30       # how much of a curve survives being behind the ball
PLATE = 0.32      # and how much of the flattened copy in the disk plane survives
HOME = (np.radians(-62.0), np.radians(35.0), 1.0)  # azimuth, elevation, zoom


def camera(azimuth: float, elevation: float):
    """Right, up and towards-the-camera unit vectors of an orthographic camera."""
    ce, se = np.cos(elevation), np.sin(elevation)
    towards = np.array([ce * np.cos(azimuth), ce * np.sin(azimuth), se])
    right = np.cross([0.0, 0.0, 1.0], towards)
    length = float(np.linalg.norm(right))
    right = np.array([1.0, 0.0, 0.0]) if length < 1e-9 else right / length
    return right, np.cross(towards, right), towards


def split_at_silhouette(points: np.ndarray, towards: np.ndarray):
    """Cut a curve where it goes round the back, as (piece, in front) pairs.

    The crossing point is interpolated rather than snapped to the nearest sample,
    so the front piece and the back piece meet exactly on the silhouette.
    """
    points = np.asarray(points, dtype=float)
    if len(points) == 0:
        return []
    depth = points @ towards
    pieces, run, front = [], [points[0]], bool(depth[0] >= 0)
    for i in range(1, len(points)):
        if (depth[i] >= 0) == front:
            run.append(points[i])
            continue
        gap = depth[i - 1] - depth[i]
        t = 0.0 if abs(gap) < 1e-15 else depth[i - 1] / gap
        edge = points[i - 1] + t * (points[i] - points[i - 1])
        run.append(edge)
        pieces.append((np.array(run), front))
        run, front = [edge, points[i]], not front
    pieces.append((np.array(run), front))
    return [(piece, is_front) for piece, is_front in pieces if len(piece) > 1]


def great_circle(normal, samples: int = 180) -> np.ndarray:
    e1, e2 = geo.plane_basis(np.asarray(normal, dtype=float))
    t = np.linspace(0.0, 2.0 * np.pi, samples)
    return np.cos(t)[:, None] * e1 + np.sin(t)[:, None] * e2


def parallel(height: float, samples: int = 120) -> np.ndarray:
    r = float(np.sqrt(max(0.0, 1.0 - height * height)))
    t = np.linspace(0.0, 2.0 * np.pi, samples)
    return np.column_stack([r * np.cos(t), r * np.sin(t), np.full_like(t, height)])


class SphereCanvas(QWidget):
    """An orbitable view of the sphere, the disk beneath it, and the rays between."""

    def __init__(self, viewer, parent=None):
        super().__init__(parent)
        self.viewer = viewer
        self.azimuth, self.elevation, self.zoom = HOME
        self._grabbed = None
        self.setMinimumSize(300, 300)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    # ------------------------------------------------------------------ geometry

    @property
    def radius(self) -> float:
        return min(self.width(), self.height()) / (2.0 * MARGIN) * self.zoom

    @property
    def centre(self) -> tuple[float, float]:
        return self.width() / 2.0, self.height() / 2.0

    def basis(self):
        return camera(self.azimuth, self.elevation)

    def to_px(self, points) -> np.ndarray:
        """Points of space -> device pixels, orthographically."""
        right, up, _ = self.basis()
        points = np.atleast_2d(np.asarray(points, dtype=float))
        cx, cy = self.centre
        r = self.radius
        return np.column_stack([cx + (points @ right) * r, cy - (points @ up) * r])

    def reset(self) -> None:
        self.azimuth, self.elevation, self.zoom = HOME
        self.update()

    # ------------------------------------------------------------------ painting

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt's name
        painter = paint.antialiased(QPainter(self))
        try:
            self._paint(painter)
        finally:
            painter.end()

    def _paint(self, painter: QPainter) -> None:
        viewer = self.viewer
        _, _, towards = self.basis()
        scene = viewer.scene()
        plain = viewer.flags["plain"]
        wire = "#3f4756" if plain else COL_WIRE

        painter.fillRect(self.rect(), paint.colour(COL_PAPER))
        self._graticule(painter, towards, wire, front=False)
        self._curves(painter, scene, towards, front=False)
        self._ball(painter)
        self._cap(painter)
        self._plate(painter, towards, plain)
        self._flattened(painter, scene)
        if viewer.flags["rays"]:
            self._rays(painter, scene)
        if viewer.flags["antipodes"]:
            self._antipodes(painter, scene, towards)
        self._graticule(painter, towards, wire, front=True)
        self._curves(painter, scene, towards, front=True)
        self._marks(painter, scene, towards)
        self._hint(painter)

    def _ball(self, painter: QPainter) -> None:
        cx, cy = self.centre
        r = self.radius
        gradient = QRadialGradient(cx - 0.35 * r, cy - 0.40 * r, 1.7 * r)
        gradient.setColorAt(0.0, paint.colour("#ffffff", 0.82))
        gradient.setColorAt(0.55, paint.colour("#dfe6ef", 0.55))
        gradient.setColorAt(1.0, paint.colour("#93a3b8", 0.45))
        painter.setPen(paint.stroke("#6d7889", 1.1, alpha=0.55))
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(QPointF(cx, cy), r, r)

    def cap_outline(self, samples: int = 121) -> np.ndarray:
        """The silhouette of the upper hemisphere, in screen units.

        A sight line through screen point (X, Y) meets the sphere at height
        `Y cos(el) + t sin(el)` with `t = +-sqrt(1 - X^2 - Y^2)`, so some point of
        it is in the upper half exactly when `Y >= -sin(el) sqrt(1 - X^2)`.  The
        region is therefore bounded above by the top of the silhouette circle and
        below by half of the projected equator - whichever half, the same formula
        gives it, so this works with the camera under the equator too.
        """
        t = np.linspace(0.0, np.pi, samples)
        squash = -np.sin(self.elevation)
        top = np.column_stack([np.cos(t), np.sin(t)])
        bottom = np.column_stack([np.cos(t[::-1]), squash * np.sin(t[::-1])])
        return np.vstack([top, bottom])

    def _cap(self, painter: QPainter) -> None:
        """Tint the half of the ball that the disk is a picture of."""
        cx, cy = self.centre
        r = self.radius
        path = QPainterPath()
        path.addPolygon([QPointF(cx + x * r, cy - y * r) for x, y in self.cap_outline()])
        path.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(paint.colour("#e8b34a", 0.11)))
        painter.drawPath(path)

    def _graticule(self, painter: QPainter, towards, wire: str, front: bool) -> None:
        """Meridians, parallels and the equator; the top half a little stronger."""
        strength = 1.0 if front else 0.55
        for longitude in np.linspace(0.0, np.pi, 6, endpoint=False):
            circle = great_circle([-np.sin(longitude), np.cos(longitude), 0.0])
            self._wire(painter, circle, towards, front, wire, 0.7, 0.30 * strength)
        for height in (0.5, 0.866):
            for sign, alpha in ((1.0, 0.34), (-1.0, 0.14)):
                self._wire(painter, parallel(sign * height), towards, front,
                           wire, 0.7, alpha * strength)
        self._wire(painter, great_circle([0.0, 0.0, 1.0]), towards, front,
                   COL_EQUATOR, 1.8, (1.0 if front else 0.35))

    def _wire(self, painter, points, towards, front, color, width, alpha) -> None:
        for piece, is_front in split_at_silhouette(points, towards):
            if is_front == front:
                paint.polyline(painter, self.to_px(piece),
                               paint.stroke(color, width, alpha=alpha))

    def _plate(self, painter: QPainter, towards, plain: bool) -> None:
        """The disk itself, lying in the equatorial plane."""
        rim = great_circle([0.0, 0.0, 1.0], 160)
        outline = self.to_px(rim)
        path = QPainterPath()
        path.addPolygon([QPointF(x, y) for x, y in outline])
        path.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(paint.colour(COL_PLATE, 0.10)))
        painter.drawPath(path)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        paint.polyline(painter, outline, paint.stroke(COL_PLATE, 1.2, "dash", 0.7))

    def _curves(self, painter: QPainter, scene: sc.Scene, towards, front: bool) -> None:
        for curve in sorted(scene.curves, key=lambda c: c.layer):
            for piece, is_front in split_at_silhouette(curve.points, towards):
                if is_front != front:
                    continue
                alpha = curve.alpha * (1.0 if front else BACK)
                paint.polyline(painter, self.to_px(piece),
                               paint.stroke(curve.color, curve.width, curve.style, alpha))

    def _flattened(self, painter: QPainter, scene: sc.Scene) -> None:
        """The same construction where it lands: the picture the disk pane shows."""
        projection = self.viewer.projection
        for curve in scene.curves:
            landed = np.column_stack([projection.project(curve.points),
                                      np.zeros(len(curve.points))])
            paint.polyline(painter, self.to_px(landed),
                           paint.stroke(curve.color, max(0.8, curve.width * 0.6),
                                        curve.style, curve.alpha * PLATE),
                           self.radius * 0.5)
        for mark in scene.marks:
            if mark.shape not in ("dot", "diamond"):
                continue
            x, y = self.to_px(projection.landing(mark.point))[0]
            paint.marker(painter, x, y, "ring", mark.color, mark.size * 0.7, 1.2, 0.7)

    def _rays(self, painter: QPainter, scene: sc.Scene) -> None:
        """The sight lines the projection works along."""
        projection = self.viewer.projection
        pen = paint.stroke(COL_RAY, 1.0, "dot", 0.75)
        for mark in scene.marks:
            if mark.shape not in ("dot", "diamond"):
                continue
            paint.polyline(painter, self.to_px(projection.ray(mark.point)), pen)

    def _antipodes(self, painter: QPainter, scene: sc.Scene, towards) -> None:
        """The other representative of every point: the identification, drawn."""
        for curve in scene.curves:
            for piece, is_front in split_at_silhouette(-curve.points, towards):
                paint.polyline(painter, self.to_px(piece),
                               paint.stroke(curve.color, curve.width * 0.7,
                                            "dash", 0.35 if is_front else 0.15))
        pen = paint.stroke(COL_RAY, 0.9, "dot", 0.5)
        for mark in scene.marks:
            if mark.shape not in ("dot", "diamond"):
                continue
            here = np.asarray(mark.point, dtype=float)
            paint.polyline(painter, self.to_px(np.array([here, -here])), pen)
            x, y = self.to_px(-here)[0]
            paint.marker(painter, x, y, "ring", mark.color, mark.size * 0.8, 1.2, 0.5)

    def _marks(self, painter: QPainter, scene: sc.Scene, towards) -> None:
        for mark in sorted(scene.marks, key=lambda m: m.layer):
            here = np.asarray(mark.point, dtype=float)
            front = float(here @ towards) >= 0.0
            x, y = self.to_px(here)[0]
            paint.marker(painter, x, y, mark.shape, mark.color, mark.size,
                         mark.width, mark.alpha * (1.0 if front else BACK))
        for text in sorted(scene.texts, key=lambda t: t.layer):
            here = np.asarray(text.point, dtype=float)
            if float(here @ towards) < 0.0:
                continue  # round the back, where it would read backwards anyway
            if text.radial:
                flat = float(np.hypot(here[0], here[1]))
                if flat > 1e-9:
                    here = here + np.array([here[0], here[1], 0.0]) * (text.radial / flat)
            x, y = self.to_px(here)[0]
            paint.label(painter, x + text.offset[0] * self.radius,
                        y - text.offset[1] * self.radius, text.text, text.color,
                        text.size * 0.92, text.italic, text.bold, 1.0, text.centred)

    def _hint(self, painter: QPainter) -> None:
        projection = self.viewer.projection
        paint.label(painter, 10, 16,
                    f"drag to turn, wheel to zoom, double-click to reset\n"
                    f"{projection.name}: {projection.summary}",
                    COL_HINT, 8.0, italic=True)

    # ------------------------------------------------------------------ input

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._grabbed = event.position()
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._grabbed is None:
            return
        position = event.position()
        self.azimuth -= (position.x() - self._grabbed.x()) * 0.008
        self.elevation = float(np.clip(
            self.elevation + (position.y() - self._grabbed.y()) * 0.008,
            np.radians(-88.0), np.radians(88.0)))
        self._grabbed = position
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._grabbed = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self.reset()

    def wheelEvent(self, event) -> None:  # noqa: N802
        steps = event.angleDelta().y() / 120.0
        self.zoom = float(np.clip(self.zoom * (1.12 ** steps), 0.45, 3.2))
        self.update()
