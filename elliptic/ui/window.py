"""The window: a tool palette, the disk, the sphere, and a line telling you where you are."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QMainWindow, QPushButton, QScrollArea, QSizePolicy,
                               QSplitter, QVBoxLayout, QWidget)

from ..model import PALETTE
from ..viewer import ACTIONS, DEFAULT_EXPORT, TOGGLES, TOOLS
from .disk import DiskCanvas
from .sphere import SphereCanvas

COL_INK = "#1f2430"
COL_MUTED = "#6b7280"
COL_EDGE = "#c4cad4"
COL_PANEL = "#eef0f4"
COL_PANEL_ON = "#c9d8ee"

TITLE = "Elliptic geometry - closed disk model"
BLURB = ("Closed disk model of the elliptic plane   -   "
         "opposite boundary points are the same point")

BUTTON_STYLE = f"""
QPushButton {{
    background: {COL_PANEL};
    border: 1px solid {COL_EDGE};
    border-radius: 3px;
    padding: 4px 6px;
    text-align: left;
    color: {COL_INK};
}}
QPushButton:hover  {{ background: #dde3ec; }}
QPushButton:checked {{ background: {COL_PANEL_ON}; font-weight: bold; }}
"""


class MainWindow(QMainWindow):
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self.setWindowTitle(TITLE)
        self.resize(1420, 900)

        self.disk = DiskCanvas(viewer)
        self.sphere = SphereCanvas(viewer)
        self.buttons: dict[str, QPushButton] = {}

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 6)
        layout.setSpacing(10)
        layout.addWidget(self._palette())
        layout.addWidget(self._stage(), 1)
        self.setCentralWidget(central)

        self.prompt = SavePrompt(viewer, self.disk)
        self.prompt.hide()

        viewer.on_change.append(self.refresh)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.refresh()

    # ------------------------------------------------------------------ building

    def _stage(self) -> QWidget:
        holder = QWidget()
        column = QVBoxLayout(holder)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)

        caption = QLabel(BLURB)
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption.setStyleSheet(f"color: {COL_INK}; font-size: 12px;")
        column.addWidget(caption)

        self.split = QSplitter(Qt.Orientation.Horizontal)
        self.split.addWidget(self.disk)
        self.split.addWidget(self.sphere)
        self.split.setSizes([760, 560])
        self.split.setChildrenCollapsible(False)
        column.addWidget(self.split, 1)

        self.status = QLabel("")
        self.status.setFont(QFont("monospace", 9))
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet(f"color: {COL_INK};")
        self.status.setMinimumHeight(52)
        column.addWidget(self.status)
        return holder

    def _palette(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(206)
        column = QVBoxLayout(panel)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(3)

        self._heading(column, "TOOLS")
        for key, text, shortcut, _ in TOOLS:
            self._button(column, key, f"{text}   [{shortcut}]", True,
                         lambda k=key: self.viewer.set_tool(k))
        self._heading(column, "SHOW")
        for key, text, shortcut in TOGGLES:
            self._button(column, f"flag:{key}", f"{text}   [{shortcut}]", True,
                         lambda k=key: self.viewer.toggle(k))
        self._heading(column, "COLOUR")
        column.addWidget(self._swatches())
        self._heading(column, "EDIT")
        for key, text, shortcut in ACTIONS:
            self._button(column, key, f"{text}   [{shortcut}]", False,
                         lambda k=key: self.viewer.action(k))
        column.addStretch(1)

        area = QScrollArea()
        area.setWidget(panel)
        area.setWidgetResizable(True)
        area.setFixedWidth(224)
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        return area

    def _heading(self, column, text: str) -> None:
        label = QLabel(text)
        label.setStyleSheet(f"color: {COL_MUTED}; font-size: 9px; font-weight: bold;")
        label.setContentsMargins(2, 8, 0, 2)
        column.addWidget(label)

    def _button(self, column, key: str, text: str, checkable: bool, action) -> None:
        button = QPushButton(text)
        button.setCheckable(checkable)
        button.setStyleSheet(BUTTON_STYLE)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.clicked.connect(lambda *_: action())
        column.addWidget(button)
        self.buttons[key] = button

    def _swatches(self) -> QWidget:
        holder = QWidget()
        grid = QGridLayout(holder)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)
        for i, color in enumerate([None] + PALETTE):
            button = QPushButton("auto" if color is None else "")
            button.setFixedSize(34, 24)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.clicked.connect(lambda *_, c=color: self.viewer.set_color(c))
            self.buttons[f"color:{color}"] = button
            grid.addWidget(button, *divmod(i, 5))
        return holder

    # ------------------------------------------------------------------ refresh

    def refresh(self) -> None:
        viewer = self.viewer
        for key, *_ in TOOLS:
            self.buttons[key].setChecked(key == viewer.tool)
        for key, *_ in TOGGLES:
            self.buttons[f"flag:{key}"].setChecked(bool(viewer.flags[key]))
        for color in [None] + PALETTE:
            chosen = color == viewer.color
            self.buttons[f"color:{color}"].setStyleSheet(
                f"background: {color or '#ffffff'};"
                f"border: {'2px solid ' + COL_INK if chosen else '1px solid ' + COL_EDGE};"
                f"border-radius: 3px; font-size: 8px; color: {COL_MUTED};")

        self.sphere.setVisible(bool(viewer.flags["sphere"]))
        self.status.setText(viewer.status_text())
        self.prompt.follow()
        self.disk.update()
        self.sphere.update()

    # ------------------------------------------------------------------ keyboard

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt's name
        if event.key() == Qt.Key.Key_Escape:
            self.viewer.key("escape")
            return
        text = event.text()
        if text and not text.isspace():
            self.viewer.key(text)
            return
        super().keyPressEvent(event)


class SavePrompt(QFrame):
    """The little box asking where the GCLC file should go, floated over the disk."""

    def __init__(self, viewer, over: QWidget):
        super().__init__(over)
        self.viewer = viewer
        self.over = over
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("QFrame { background: #ffffff; border: 1px solid #9aa4b4;"
                           " border-radius: 4px; }")
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 8, 10, 8)
        self.caption = QLabel("save GCLC to")
        self.caption.setStyleSheet("border: none; color: #1f2430;")
        self.field = QLineEdit(DEFAULT_EXPORT)
        self.field.setMinimumWidth(230)
        self.field.returnPressed.connect(self._submit)
        row.addWidget(self.caption)
        row.addWidget(self.field)

    def _submit(self) -> None:
        self.viewer.submit_prompt(self.field.text().strip() or DEFAULT_EXPORT)
        self.window().setFocus()

    def follow(self) -> None:
        """Show or hide, matching the viewer, and sit in the middle of the disk."""
        if not self.viewer.prompting:
            if self.isVisible():
                self.hide()
                self.window().setFocus()
            return
        self.caption.setText("save plain GCLC to" if self.viewer.plain_export
                             else "save GCLC to")
        if not self.isVisible():
            self.field.setText(DEFAULT_EXPORT)
            self.show()
        self.adjustSize()
        self.move(max(0, (self.over.width() - self.width()) // 2),
                  max(0, (self.over.height() - self.height()) // 2 - 30))
        self.raise_()
        self.field.setFocus()
        self.field.selectAll()
