"""Painting primitives shared by the disk and the sphere.

Everything here works in *device coordinates*: the caller has already decided
where a point of the sphere lands on its widget, and this module only knows how
to put ink there.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen

WHITE = "#ffffff"
DASH_PATTERN = [5.0, 4.0]
DOT_PATTERN = [1.6, 3.2]


def colour(name: str, alpha: float = 1.0) -> QColor:
    c = QColor(name)
    if alpha < 1.0:
        c.setAlphaF(max(0.0, min(1.0, alpha)))
    return c


def stroke(color: str, width: float, style: str = "solid", alpha: float = 1.0) -> QPen:
    pen = QPen(colour(color, alpha))
    pen.setWidthF(max(0.1, width))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    if style == "dash":
        pen.setStyle(Qt.PenStyle.CustomDashLine)
        pen.setDashPattern([d / max(0.4, width) for d in DASH_PATTERN])
    elif style == "dot":
        pen.setStyle(Qt.PenStyle.CustomDashLine)
        pen.setDashPattern([d / max(0.4, width) for d in DOT_PATTERN])
    return pen


def path_of(points: np.ndarray, max_step: float | None = None) -> QPainterPath:
    """A polyline through device-space `points`, broken where it jumps.

    The break matters: a curve that runs out through the rim comes back in on the
    other side of the picture, and joining those two places up would draw a chord
    that is not part of anything.
    """
    path = QPainterPath()
    points = np.asarray(points, dtype=float)
    if len(points) < 2:
        return path
    started = False
    previous = None
    for x, y in points:
        if not np.isfinite(x) or not np.isfinite(y):
            started = False
            continue
        jumped = (max_step is not None and previous is not None
                  and abs(x - previous[0]) + abs(y - previous[1]) > max_step)
        if not started or jumped:
            path.moveTo(x, y)
            started = True
        else:
            path.lineTo(x, y)
        previous = (x, y)
    return path


def polyline(painter: QPainter, points, pen: QPen, max_step: float | None = None) -> None:
    path = path_of(points, max_step)
    if path.elementCount() < 2:
        return
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)


def star_path(x: float, y: float, radius: float, points: int = 5) -> QPainterPath:
    path = QPainterPath()
    for i in range(2 * points):
        r = radius if i % 2 == 0 else radius * 0.42
        angle = np.pi / 2 + i * np.pi / points
        spoke = QPointF(x + r * np.cos(angle), y - r * np.sin(angle))
        path.moveTo(spoke) if i == 0 else path.lineTo(spoke)
    path.closeSubpath()
    return path


def marker(painter: QPainter, x: float, y: float, shape: str, color: str,
           size: float, width: float = 1.5, alpha: float = 1.0,
           paper: str = WHITE) -> None:
    """One symbol, `size` pixels across, centred on (x, y)."""
    r = size / 2.0
    ink = colour(color, alpha)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if shape == "dot":
        painter.setPen(stroke(paper, width, alpha=alpha))
        painter.setBrush(QBrush(ink))
        painter.drawEllipse(QPointF(x, y), r, r)
    elif shape == "ring":
        painter.setPen(stroke(color, width, alpha=alpha))
        painter.drawEllipse(QPointF(x, y), r, r)
    elif shape == "diamond":
        painter.setPen(stroke(color, width, alpha=alpha))
        painter.setBrush(QBrush(colour(paper)))
        painter.drawPolygon([QPointF(x, y - r), QPointF(x + r, y),
                             QPointF(x, y + r), QPointF(x - r, y)])
    elif shape == "square":
        painter.setPen(stroke(paper, width, alpha=alpha))
        painter.setBrush(QBrush(ink))
        painter.drawRect(QRectF(x - r, y - r, 2 * r, 2 * r))
    elif shape == "star":
        painter.setBrush(QBrush(ink))
        painter.drawPath(star_path(x, y, r))
    elif shape == "cross":
        painter.setPen(stroke(color, width, alpha=alpha))
        painter.drawLine(QPointF(x - r, y - r), QPointF(x + r, y + r))
        painter.drawLine(QPointF(x - r, y + r), QPointF(x + r, y - r))
    else:  # pragma: no cover - a shape nobody asked for
        raise ValueError(f"unknown marker shape: {shape}")


def label(painter: QPainter, x: float, y: float, text: str, color: str,
          size: float, italic: bool = False, bold: bool = False,
          alpha: float = 1.0, centred: bool = False) -> None:
    """Text, possibly several lines, anchored at (x, y)."""
    font = QFont(painter.font())
    font.setPointSizeF(size)
    font.setItalic(italic)
    font.setBold(bold)
    painter.setFont(font)
    painter.setPen(stroke(color, 1.0, alpha=alpha))
    painter.setBrush(Qt.BrushStyle.NoBrush)

    metrics = painter.fontMetrics()
    lines = text.split("\n")
    step = metrics.height() * 1.25
    top = y - 0.5 * step * (len(lines) - 1) if centred else y
    for i, line in enumerate(lines):
        width = metrics.horizontalAdvance(line)
        painter.drawText(QPointF(x - width / 2 if centred else x,
                                 top + i * step + metrics.ascent() / 2 - 1),
                         line)


def antialiased(painter: QPainter) -> QPainter:
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    return painter
