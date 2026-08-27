"""The PySide6 front end: two canvases, a palette, and a way to get an image out."""

from __future__ import annotations

import os
import sys

from .disk import DiskCanvas
from .sphere import SphereCanvas
from .window import MainWindow

__all__ = ["DiskCanvas", "SphereCanvas", "MainWindow", "app", "run", "render"]


def app():
    """The one QApplication, made if it is not there yet."""
    from PySide6.QtWidgets import QApplication

    existing = QApplication.instance()
    if existing is not None:
        return existing
    if not any(os.environ.get(name) for name in ("DISPLAY", "WAYLAND_DISPLAY")):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication(sys.argv[:1])


def run(viewer) -> None:
    """Open the window and stay there until it is closed."""
    application = app()
    window = MainWindow(viewer)
    viewer.window = window
    window.show()
    application.exec()


def render(viewer, path: str, width: int = 1400, height: int = 900) -> str:
    """Draw the current picture into an image file, with or without a screen."""
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor, QImage, QPainter

    app()
    panes = [DiskCanvas(viewer)]
    if viewer.flags["sphere"]:
        panes.append(SphereCanvas(viewer))
    each = width // len(panes)

    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    try:
        for i, pane in enumerate(panes):
            pane.resize(each, height)
            painter.drawPixmap(QPointF(i * each, 0), pane.grab())
    finally:
        painter.end()
    for pane in panes:
        pane.deleteLater()

    if not image.save(path):
        raise OSError(f"could not write {path}")
    return path
