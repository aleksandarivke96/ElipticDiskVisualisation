"""The PySide6 front end: `python3 -m tests.test_ui`.

Runs on the offscreen platform, so it needs no display.  The tools themselves
are `tests.test_viewer`'s job; this is about the window, the two canvases and
the camera that turns the sphere.
"""

from __future__ import annotations

import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import numpy as np
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent

from elliptic import EllipticDiskViewer
from elliptic import geometry as geo
from elliptic.ui import DiskCanvas, MainWindow, SphereCanvas, app, render
from elliptic.ui.sphere import camera, split_at_silhouette

app()  # one QApplication for the whole module


def a_construction(viewer=None):
    """A figure with a bit of everything in it."""
    v = viewer or EllipticDiskViewer()
    v.set_tool("triangle")
    for x, y in [(0.05, 0.1), (0.55, -0.15), (-0.25, 0.55)]:
        v.press(x, y)
        v.release()
    v.set_tool("perp")
    v.press(-0.65, -0.45)
    v.release()
    side = v.construction.lines[0]
    path = v.paths(side)[0]
    v.press(*path[len(path) // 2])
    v.release()
    v.set_tool("dual")
    v.press(0.05, 0.1)
    v.release()
    return v


def mouse(kind, x, y):
    button = Qt.MouseButton.LeftButton
    return QMouseEvent(kind, QPointF(x, y), QPointF(x, y), button, button,
                       Qt.KeyboardModifier.NoModifier)


def typed(text: str, qt_key=Qt.Key.Key_unknown):
    return QKeyEvent(QEvent.Type.KeyPress, qt_key, Qt.KeyboardModifier.NoModifier, text)


# ---------------------------------------------------------------- the camera

def test_the_camera_basis_is_orthonormal_and_right_handed():
    for azimuth in np.linspace(-np.pi, np.pi, 9):
        for elevation in np.radians([-88, -40, 0, 25, 88]):
            right, up, towards = camera(azimuth, elevation)
            for one in (right, up, towards):
                assert abs(np.linalg.norm(one) - 1.0) < 1e-12
            assert abs(right @ up) < 1e-12
            assert abs(right @ towards) < 1e-12
            assert abs(up @ towards) < 1e-12
            assert np.allclose(np.cross(right, up), towards, atol=1e-12)


def test_the_camera_keeps_the_horizon_level():
    """`right` is horizontal, so the sphere never rolls: up on screen is up."""
    for azimuth in np.linspace(0, 2 * np.pi, 7):
        right, up, _ = camera(azimuth, np.radians(30.0))
        assert abs(right[2]) < 1e-12
        assert up[2] > 0.0


def test_splitting_at_the_silhouette_meets_exactly_on_it():
    _, _, towards = camera(0.7, 0.4)
    circle = np.column_stack([np.cos(t := np.linspace(0, 2 * np.pi, 361)),
                              np.sin(t), np.zeros_like(t)])
    pieces = split_at_silhouette(circle, towards)
    assert len(pieces) >= 2, "a great circle goes round the back"
    assert {front for _, front in pieces} == {True, False}
    for piece, front in pieces:
        depth = piece @ towards
        assert (depth >= -1e-12).all() if front else (depth <= 1e-12).all()
        for end in (piece[0], piece[-1]):
            on_edge = abs(end @ towards) < 1e-9
            at_start = np.allclose(end, circle[0]) or np.allclose(end, circle[-1])
            assert on_edge or at_start, "a piece ends on the silhouette or at the end"
    total = sum(len(piece) for piece, _ in pieces)
    assert total >= len(circle), "no sample was dropped"


def test_a_curve_entirely_in_front_is_not_split():
    _, _, towards = camera(0.0, 0.0)  # looking along +x, so the front is x > 0
    arc = np.column_stack([np.full(5, 0.9), np.linspace(-0.2, 0.2, 5), np.zeros(5)])
    arc /= np.linalg.norm(arc, axis=1)[:, None]
    pieces = split_at_silhouette(arc, towards)
    assert len(pieces) == 1 and pieces[0][1] is True
    assert len(pieces[0][0]) == len(arc)


def test_the_cap_outline_is_the_upper_hemisphere():
    """Every point inside it is a sight line that meets the half we model."""
    canvas = SphereCanvas(EllipticDiskViewer())
    for elevation in np.radians([-70, -20, 0, 18, 61]):
        canvas.elevation = elevation
        outline = canvas.cap_outline()
        squash = -np.sin(elevation)
        for x, y in outline:
            assert x * x + y * y <= 1.0 + 1e-9, "inside the silhouette circle"
            top = np.sqrt(max(0.0, 1.0 - x * x))
            assert -1e-9 <= y - squash * top or abs(y - top) < 1e-9
        # the boundary really is where the sight line grazes the equator
        for x, y in outline[len(outline) // 2:]:
            height = y * np.cos(elevation) + np.sqrt(
                max(0.0, 1.0 - x * x - y * y)) * np.sin(elevation)
            assert abs(height) < 1e-6, "the lower edge of the cap sits on z = 0"


def test_turning_the_sphere_moves_the_picture_but_not_the_construction():
    v = a_construction()
    canvas = SphereCanvas(v)
    canvas.resize(500, 500)
    before_az, before_el = canvas.azimuth, canvas.elevation
    where = [p.xy.copy() for p in v.construction.points if p.xy is not None]

    canvas.mousePressEvent(mouse(QEvent.Type.MouseButtonPress, 250, 250))
    canvas.mouseMoveEvent(mouse(QEvent.Type.MouseMove, 330, 210))
    canvas.mouseReleaseEvent(mouse(QEvent.Type.MouseButtonRelease, 330, 210))

    assert canvas.azimuth != before_az and canvas.elevation != before_el
    now = [p.xy for p in v.construction.points if p.xy is not None]
    assert all(np.allclose(one, other) for one, other in zip(where, now)), \
        "dragging the sphere turns the camera, it does not edit anything"

    canvas.wheelEvent(wheel(240))
    assert canvas.zoom > 1.0
    canvas.reset()
    assert (canvas.azimuth, canvas.elevation, canvas.zoom) == (before_az, before_el, 1.0)


def wheel(delta: int):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QWheelEvent

    return QWheelEvent(QPointF(10, 10), QPointF(10, 10), QPoint(0, 0),
                       QPoint(0, delta), Qt.MouseButton.NoButton,
                       Qt.KeyboardModifier.NoModifier,
                       Qt.ScrollPhase.NoScrollPhase, False)


def test_the_elevation_never_goes_over_the_pole():
    canvas = SphereCanvas(EllipticDiskViewer())
    canvas.resize(400, 400)
    canvas.mousePressEvent(mouse(QEvent.Type.MouseButtonPress, 200, 200))
    for _ in range(40):
        canvas.mouseMoveEvent(mouse(QEvent.Type.MouseMove, 200, 900))
    assert canvas.elevation <= np.radians(88.0) + 1e-9
    for _ in range(80):
        canvas.mouseMoveEvent(mouse(QEvent.Type.MouseMove, 200, -900))
    assert canvas.elevation >= np.radians(-88.0) - 1e-9


# ---------------------------------------------------------------- the disk canvas

def test_pixels_and_disk_coordinates_are_inverse():
    canvas = DiskCanvas(EllipticDiskViewer())
    canvas.resize(800, 640)
    for xy in [(0.0, 0.0), (0.4, -0.7), (-0.95, 0.1), (1.0, 0.0)]:
        px, py = canvas.to_px(xy)[0]
        assert np.allclose(canvas.from_px(px, py), xy, atol=1e-9)
    cx, cy = canvas.centre
    assert np.allclose(canvas.to_px((0.0, 0.0))[0], [cx, cy])
    assert canvas.to_px((0.0, 1.0))[0][1] < cy, "y is up in the disk, down on screen"


def test_a_click_on_the_canvas_lands_where_it_looks():
    v = EllipticDiskViewer()
    canvas = DiskCanvas(v)
    canvas.resize(700, 700)
    px, py = canvas.to_px((0.35, -0.42))[0]
    canvas.mousePressEvent(mouse(QEvent.Type.MouseButtonPress, px, py))
    canvas.mouseReleaseEvent(mouse(QEvent.Type.MouseButtonRelease, px, py))
    point = v.construction.points[0]
    assert np.allclose(v.screen(point.vector), [0.35, -0.42], atol=1e-9)


def test_painting_teaches_the_viewer_how_big_a_pixel_is():
    v = EllipticDiskViewer()
    canvas = DiskCanvas(v)
    canvas.resize(600, 600)
    canvas.grab()
    assert abs(v.scale - canvas.radius) < 1e-9
    canvas.resize(1200, 1200)
    canvas.grab()
    assert abs(v.scale - canvas.radius) < 1e-9 and v.scale > 400


# ---------------------------------------------------------------- painting

def test_both_canvases_paint_a_full_construction():
    v = a_construction()
    for canvas in (DiskCanvas(v), SphereCanvas(v)):
        canvas.resize(560, 560)
        image = canvas.grab().toImage()
        assert not image.isNull() and image.width() == 560
        assert ink_used(image) > 200, "something actually got drawn"


def test_every_combination_of_the_show_toggles_paints():
    v = a_construction()
    disk, sphere = DiskCanvas(v), SphereCanvas(v)
    disk.resize(420, 420)
    sphere.resize(420, 420)
    for bits in range(1 << 5):
        for i, flag in enumerate(("labels", "poles", "meets", "plain", "antipodes")):
            v.flags[flag] = bool(bits & (1 << i))
        assert not disk.grab().toImage().isNull()
        assert not sphere.grab().toImage().isNull()


def test_the_sphere_pane_draws_more_when_the_extras_are_on():
    v = a_construction()
    sphere = SphereCanvas(v)
    sphere.resize(520, 520)
    v.flags["rays"] = False
    v.flags["antipodes"] = False
    plain = ink_used(sphere.grab().toImage())
    v.flags["rays"] = True
    with_rays = ink_used(sphere.grab().toImage())
    v.flags["antipodes"] = True
    with_both = ink_used(sphere.grab().toImage())
    assert plain < with_rays < with_both


def test_the_two_projections_land_points_in_different_places():
    v = a_construction()
    sphere = SphereCanvas(v)
    point = v.construction.points[0].vector
    straight_down = geo.ORTHOGONAL.landing(point)
    from_the_pole = geo.STEREOGRAPHIC.landing(point)
    assert straight_down[2] == 0.0 and from_the_pole[2] == 0.0
    assert not np.allclose(straight_down, from_the_pole)
    assert not np.allclose(sphere.to_px(straight_down), sphere.to_px(from_the_pole))


def ink_used(image) -> int:
    """How many pixels are not the background, as a rough 'was anything drawn'.

    The converted image has to stay alive while its buffer is read: let it go and
    the memoryview is pointing at freed memory.
    """
    from PySide6.QtGui import QImage

    held = image.convertToFormat(QImage.Format.Format_RGBA8888)
    data = np.frombuffer(memoryview(held.constBits()), dtype=np.uint8)
    data = data.reshape(held.height(), held.bytesPerLine() // 4, 4)
    return int((data[:, :held.width(), :3] < 235).any(axis=-1).sum())


# ---------------------------------------------------------------- the window

def test_the_window_builds_and_mirrors_the_viewer():
    v = a_construction()
    window = MainWindow(v)
    assert window.buttons["triangle"].isChecked() is False
    v.set_tool("triangle")
    assert window.buttons["triangle"].isChecked() is True
    assert window.buttons["flag:labels"].isChecked() is True
    v.toggle("labels")
    assert window.buttons["flag:labels"].isChecked() is False
    assert "TRIANGLE" in window.status.text()
    window.close()


def test_the_palette_buttons_drive_the_tools():
    v = EllipticDiskViewer()
    window = MainWindow(v)
    assert v.projection is geo.STEREOGRAPHIC
    window.buttons["meet"].click()
    assert v.tool == "meet"
    window.buttons["flag:conformal"].click()
    assert v.projection is geo.ORTHOGONAL
    window.buttons["color:#1a9e6a"].click()
    assert v.color == "#1a9e6a"
    window.buttons["clear"].click()
    assert v.construction.points == []
    window.close()


def test_the_sphere_pane_can_be_put_away():
    v = EllipticDiskViewer()
    window = MainWindow(v)
    window.show()
    assert window.sphere.isVisible()
    window.keyPressEvent(typed("s"))
    assert not v.flags["sphere"] and not window.sphere.isVisible()
    window.keyPressEvent(typed("s"))
    assert window.sphere.isVisible()
    window.close()


def test_keys_reach_the_viewer_through_the_window():
    v = EllipticDiskViewer()
    window = MainWindow(v)
    window.keyPressEvent(typed("5"))
    assert v.tool == "triangle"
    window.keyPressEvent(typed("o"))
    assert v.flags["conformal"] is False
    window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape,
                                   Qt.KeyboardModifier.NoModifier, "\x1b"))
    assert "cancelled" in v.message
    window.close()


def test_the_save_box_follows_the_viewer():
    import tempfile

    v = EllipticDiskViewer()
    v.set_tool("point")
    v.press(0.2, 0.2)
    v.release()
    window = MainWindow(v)
    window.show()
    assert not window.prompt.isVisible()

    window.keyPressEvent(typed("g"))
    assert v.prompting and window.prompt.isVisible()
    assert window.prompt.caption.text() == "save GCLC to"

    with tempfile.TemporaryDirectory() as folder:
        window.prompt.field.setText(os.path.join(folder, "typed"))
        window.prompt.field.returnPressed.emit()
        assert not v.prompting and not window.prompt.isVisible()
        assert os.path.exists(os.path.join(folder, "typed.gcl"))
    window.close()


def test_the_save_box_says_when_it_will_be_plain():
    v = EllipticDiskViewer()
    window = MainWindow(v)
    window.show()
    window.keyPressEvent(typed("G"))
    assert window.prompt.isVisible()
    assert window.prompt.caption.text() == "save plain GCLC to"
    window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape,
                                   Qt.KeyboardModifier.NoModifier, "\x1b"))
    assert not window.prompt.isVisible()
    window.close()


# ---------------------------------------------------------------- images

def test_rendering_writes_an_image_of_both_panes():
    import tempfile

    v = a_construction()
    with tempfile.TemporaryDirectory() as folder:
        both = render(v, os.path.join(folder, "both.png"), 1200, 600)
        assert os.path.getsize(both) > 5000
        v.flags["sphere"] = False
        one = render(v, os.path.join(folder, "one.png"), 1200, 600)
        assert os.path.getsize(one) > 5000
        assert ink_used(image_at(both)) > ink_used(image_at(one)), \
            "the sphere pane is worth something"


def image_at(path):
    from PySide6.QtGui import QImage

    image = QImage(path)
    assert not image.isNull()
    return image.convertToFormat(QImage.Format.Format_ARGB32)


def test_saving_from_the_viewer_needs_no_window():
    import tempfile

    v = a_construction()
    with tempfile.TemporaryDirectory() as folder:
        path = v.save(os.path.join(folder, "shot.png"), 900, 500)
        assert os.path.exists(path) and image_at(path).width() == 900


def test_the_slider_turns_the_construction_about_the_pivot():
    v = EllipticDiskViewer()
    v.set_tool("point")
    v.press(0.5, 0.0)
    v.release()
    v.press(-0.2, 0.3)
    v.release()
    window = MainWindow(v)
    assert "about the centre" in window.rotate_caption.text()
    before = v.construction.points[1].vector.copy()

    window.rotate_slider.setValue(90)    # about the disk's centre: the z axis
    expected = geo.rotation(np.array([0.0, 0.0, 1.0]), np.radians(90.0)) @ before
    assert np.linalg.norm(v.construction.points[1].vector - expected) < 1e-6
    assert "+90" in window.rotate_caption.text()

    window.rotate_slider.setValue(0)
    assert np.linalg.norm(v.construction.points[1].vector - before) < 1e-6

    v.set_pivot(v.construction.points[0])   # now about A: A must not move
    held = v.construction.points[0].vector.copy()
    assert window.rotate_slider.value() == 0
    assert "about A" in window.rotate_caption.text()
    window.rotate_slider.setValue(45)
    assert np.linalg.norm(v.construction.points[0].vector - held) < 1e-9
    window.close()


def test_arrow_keys_rotate_and_the_slider_follows():
    v = EllipticDiskViewer()
    v.set_tool("point")
    v.press(0.3, 0.2)
    v.release()
    window = MainWindow(v)
    for _ in range(4):
        window.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Right,
                                       Qt.KeyboardModifier.NoModifier, ""))
    assert abs(v.turned - 12.0) < 1e-9
    assert window.rotate_slider.value() == 12, "the slider shows what the keys did"
    assert "isometry" in v.message
    window.close()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} checks passed")
