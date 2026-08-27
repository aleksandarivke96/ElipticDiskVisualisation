"""The disk: the elliptic plane seen flat, and the surface you build on."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QPainter
from PySide6.QtWidgets import QWidget

from .. import scene as sc
from . import paint

COL_DISK = "#3f4756"
COL_FACE = "#f7f8fa"
COL_PAPER = "#ffffff"
MARGIN = 1.17  # how much room to leave round the rim, in disk radii


class DiskCanvas(QWidget):
    """Draws the scene through the viewer's current projection, and takes clicks."""

    def __init__(self, viewer, parent=None):
        super().__init__(parent)
        self.viewer = viewer
        self.setMinimumSize(340, 340)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(False)

    # ------------------------------------------------------------------ geometry

    @property
    def radius(self) -> float:
        return min(self.width(), self.height()) / (2.0 * MARGIN)

    @property
    def centre(self) -> tuple[float, float]:
        return self.width() / 2.0, self.height() / 2.0

    def to_px(self, xy) -> np.ndarray:
        """Disk coordinates -> device pixels."""
        xy = np.atleast_2d(np.asarray(xy, dtype=float))
        cx, cy = self.centre
        out = np.column_stack([cx + xy[:, 0] * self.radius,
                               cy - xy[:, 1] * self.radius])
        return out

    def from_px(self, px: float, py: float) -> tuple[float, float]:
        cx, cy = self.centre
        r = self.radius
        return (px - cx) / r, (cy - py) / r

    # ------------------------------------------------------------------ painting

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt's name
        painter = paint.antialiased(QPainter(self))
        try:
            self._paint(painter)
        finally:
            painter.end()

    def _paint(self, painter: QPainter) -> None:
        viewer = self.viewer
        viewer.scale = self.radius  # so the pick radius stays honest at any size
        plain = viewer.flags["plain"]
        cx, cy = self.centre
        r = self.radius

        painter.fillRect(self.rect(), paint.colour(COL_PAPER))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(paint.colour(COL_PAPER if plain else COL_FACE)))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(paint.stroke(COL_DISK, 2.0, "dash"))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        painter.setPen(paint.stroke(COL_DISK, 1.0, alpha=0.5))
        painter.drawLine(QPointF(cx - 5, cy), QPointF(cx + 5, cy))
        painter.drawLine(QPointF(cx, cy - 5), QPointF(cx, cy + 5))

        draw_scene(painter, viewer.scene(), self._project, r)

    def _project(self, vectors) -> np.ndarray:
        return self.to_px(self.viewer.screen(vectors))

    # ------------------------------------------------------------------ input

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        position = event.position()
        self.viewer.press(*self.from_px(position.x(), position.y()))

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        position = event.position()
        self.viewer.motion(*self.from_px(position.x(), position.y()))

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self.viewer.release()


def draw_scene(painter: QPainter, scene: sc.Scene, project, radius: float,
               alpha: float = 1.0, paper: str = COL_PAPER) -> None:
    """Paint a whole scene, `project` mapping (N, 3) sphere points to pixels."""
    items = ([(c.layer, 0, c) for c in scene.curves]
             + [(m.layer, 1, m) for m in scene.marks]
             + [(t.layer, 2, t) for t in scene.texts])
    max_step = radius * 0.35

    for _, _, item in sorted(items, key=lambda entry: (entry[0], entry[1])):
        if isinstance(item, sc.Curve):
            paint.polyline(painter, project(item.points),
                           paint.stroke(item.color, item.width, item.style,
                                        item.alpha * alpha), max_step)
        elif isinstance(item, sc.Mark):
            x, y = project(np.atleast_2d(item.point))[0]
            paint.marker(painter, x, y, item.shape, item.color, item.size,
                         item.width, item.alpha * alpha, paper)
        else:
            here = np.asarray(item.point, dtype=float)
            if item.radial:  # push the label out past the rim
                flat = np.hypot(here[0], here[1])
                if flat > 1e-9:
                    here = here + np.array([here[0], here[1], 0.0]) * (item.radial / flat)
            x, y = project(np.atleast_2d(here))[0]
            paint.label(painter, x + item.offset[0] * radius,
                        y - item.offset[1] * radius, item.text, item.color,
                        item.size, item.italic, item.bold, alpha, item.centred)
