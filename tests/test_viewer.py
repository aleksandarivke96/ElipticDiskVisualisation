"""Drives the viewer with synthetic events: `python3 -m tests.test_viewer`.

Everything here goes through the same canvas callbacks the real window uses, so
it exercises the tools rather than the model underneath them.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import numpy as np
from matplotlib.backend_bases import KeyEvent, MouseButton, MouseEvent

from elliptic import EllipticDiskViewer


def viewer_with(tool="point"):
    v = EllipticDiskViewer()
    v._set_tool(tool)
    return v


def press(v, x, y):
    _send(v, "button_press_event", x, y)


def drag(v, x, y):
    _send(v, "motion_notify_event", x, y)


def release(v, x, y):
    _send(v, "button_release_event", x, y)


def click(v, x, y):
    press(v, x, y)
    release(v, x, y)


def _send(v, name, x, y):
    px, py = v.ax.transData.transform((x, y))
    v.fig.canvas.callbacks.process(
        name, MouseEvent(name, v.fig.canvas, px, py, MouseButton.LEFT))


def key(v, k):
    v.fig.canvas.callbacks.process("key_press_event",
                                   KeyEvent("key_press_event", v.fig.canvas, k))


def test_point_tool_adds_as_many_as_you_like():
    v = viewer_with("point")
    for i in range(7):
        click(v, -0.6 + 0.15 * i, 0.2)
    assert len(v.construction.points) == 7
    assert [p.label for p in v.construction.points][:3] == ["A", "B", "C"]


def test_placing_a_point_lets_you_drag_it_straight_away():
    v = viewer_with("point")
    press(v, 0.1, 0.1)
    drag(v, 0.4, -0.2)
    release(v, 0.4, -0.2)
    assert np.allclose(v.construction.points[0].xy, [0.4, -0.2])


def test_line_tool_joins_two_clicks_on_empty_space():
    v = viewer_with("line")
    click(v, 0.3, 0.4)
    assert v.pending is not None and not v.construction.lines
    click(v, -0.5, 0.1)
    assert v.pending is None
    line = v.construction.lines[0]
    assert len(v.construction.points) == 2 and not line.is_segment
    assert abs(np.dot(line.normal, line.p.vector)) < 1e-12


def test_line_tool_snaps_onto_existing_points():
    v = viewer_with("point")
    click(v, 0.3, 0.4)
    click(v, -0.5, 0.1)
    v._set_tool("line")
    click(v, 0.302, 0.398)  # within the pick radius of A
    click(v, -0.5, 0.1)
    assert len(v.construction.points) == 2, "should reuse the points, not add new ones"
    assert v.construction.lines[0].p is v.construction.points[0]


def test_lines_are_independent_objects():
    v = viewer_with("line")
    for a, b in [((0.3, 0.4), (-0.5, 0.1)), ((0.6, -0.3), (-0.2, -0.6)),
                 ((0.0, 0.8), (0.7, 0.5))]:
        click(v, *a)
        click(v, *b)
    assert len(v.construction.lines) == 3
    assert [l.label for l in v.construction.lines] == ["a", "b", "c"]
    assert len(v.construction.intersections()) == 3  # every pair meets once


def test_segment_tool_marks_the_line_as_a_segment():
    v = viewer_with("segment")
    click(v, 0.6, 0.1)
    click(v, -0.5, 0.4)
    seg = v.construction.lines[0]
    assert seg.is_segment and seg.length() <= np.pi / 2 + 1e-12


def test_escape_cancels_a_half_finished_line():
    v = viewer_with("line")
    click(v, 0.3, 0.4)
    key(v, "escape")
    assert v.pending is None and not v.construction.lines


def test_move_tool_drags_a_point_and_the_line_follows():
    v = viewer_with("line")
    click(v, 0.3, 0.4)
    click(v, -0.5, 0.1)
    line = v.construction.lines[0]
    before = line.normal.copy()
    v._set_tool("move")
    press(v, 0.3, 0.4)
    drag(v, 0.1, -0.6)
    release(v, 0.1, -0.6)
    assert np.allclose(line.p.xy, [0.1, -0.6])
    assert not np.allclose(before, line.normal)
    assert abs(np.dot(line.normal, line.p.vector)) < 1e-12


def test_move_tool_ignores_empty_space():
    v = viewer_with("point")
    click(v, 0.3, 0.4)
    v._set_tool("move")
    press(v, -0.8, -0.8)
    drag(v, 0.0, 0.0)
    release(v, 0.0, 0.0)
    assert np.allclose(v.construction.points[0].xy, [0.3, 0.4])


def test_delete_tool_removes_a_point_and_its_lines():
    v = viewer_with("line")
    click(v, 0.3, 0.4)
    click(v, -0.5, 0.1)
    v._set_tool("delete")
    click(v, 0.3, 0.4)
    assert len(v.construction.points) == 1 and not v.construction.lines


def test_delete_tool_hits_a_line_without_touching_its_points():
    v = viewer_with("line")
    click(v, 0.5, 0.0)
    click(v, -0.5, 0.0)          # a diameter along y = 0
    v._set_tool("delete")
    click(v, 0.0, 0.0)           # on the line, far from either point
    assert not v.construction.lines and len(v.construction.points) == 2


def test_clicks_outside_the_disk_snap_to_the_rim():
    v = viewer_with("point")
    click(v, 1.1, 0.35)
    assert abs(np.linalg.norm(v.construction.points[0].xy) - 1.0) < 1e-12


def test_joining_a_rim_point_to_its_antipode_is_refused():
    v = viewer_with("line")
    click(v, 1.1, 0.0)     # snaps to (1, 0)
    click(v, -1.1, 0.0)    # snaps to (-1, 0) - the same elliptic point
    assert not v.construction.lines
    assert "same elliptic point" in v.message


def draw_a_line(v, a=(0.5, 0.35), b=(-0.45, 0.15)):
    """Leaves the viewer holding one plain line, tool unchanged afterwards."""
    tool = v.tool
    v._set_tool("line")
    click(v, *a)
    click(v, *b)
    v._set_tool(tool)
    return v.construction.lines[-1]


def spot_on(v, line, avoid=()):
    """A point genuinely on the drawn line, clear of the points and of `avoid`."""
    from elliptic import geometry as g

    samples = g.line_points(line.normal, 201)[10:-10]  # keep away from the rim
    others = [p.xy for p in v.construction.points]
    for other in avoid:
        others.extend(g.line_points(other.normal, 201))
    clearance = [min((np.linalg.norm(xy - o) for o in others), default=1.0)
                 for xy in samples]
    return tuple(samples[int(np.argmax(clearance))])


def test_perpendicular_tool_point_then_line():
    v = viewer_with("perp")
    base = draw_a_line(v)
    click(v, 0.1, -0.5)                    # a fresh point in empty space
    assert v.pending is not None and len(v.construction.lines) == 1
    click(v, *spot_on(v, base))            # on the line
    perp = v.construction.lines[-1]
    assert perp.is_perpendicular and perp.base is base and v.pending is None
    assert abs(np.dot(perp.normal, base.normal)) < 1e-12


def test_perpendicular_tool_line_then_point():
    v = viewer_with("perp")
    base = draw_a_line(v)
    click(v, *spot_on(v, base))            # the line first
    assert v.pending is base
    click(v, 0.1, -0.5)                    # then the point
    perp = v.construction.lines[-1]
    assert perp.is_perpendicular and perp.base is base
    assert np.allclose(perp.p.xy, [0.1, -0.5]), "the second click made the point"


def test_perpendicular_tool_reuses_an_existing_point():
    v = viewer_with("point")
    click(v, 0.1, -0.5)
    v._set_tool("perp")
    base = draw_a_line(v)
    click(v, 0.1, -0.5)
    click(v, *spot_on(v, base))
    assert len(v.construction.points) == 3, "should not duplicate the point"
    assert v.construction.lines[-1].p is v.construction.points[0]


def test_perpendicular_tool_waits_for_a_line():
    v = viewer_with("perp")
    draw_a_line(v)
    click(v, 0.1, -0.5)
    pending = v.pending
    click(v, -0.7, -0.7)                   # empty space, nowhere near the line
    assert v.pending is pending, "keeps waiting instead of dropping the selection"
    assert not any(l.is_perpendicular for l in v.construction.lines)
    assert "click on a line" in v.message


def test_perpendicular_tool_refuses_the_pole():
    from elliptic import geometry as g

    v = viewer_with("perp")
    base = draw_a_line(v)
    pole = g.polar_point(base.normal)
    click(v, *pole)
    click(v, *spot_on(v, base))
    assert not any(l.is_perpendicular for l in v.construction.lines)
    assert "pole" in v.message


def test_perpendicular_foot_and_right_angle_are_drawn():
    v = viewer_with("perp")
    base = draw_a_line(v)
    click(v, 0.1, -0.5)
    click(v, *spot_on(v, base))
    assert any(l.get_marker() == "s" for l in v.ax.lines), "foot marker missing"
    assert "perpendicular" in v.status.get_text() and "distance" in v.status.get_text()


def test_perpendicular_updates_when_the_base_is_dragged():
    v = viewer_with("perp")
    base = draw_a_line(v)
    click(v, 0.1, -0.5)
    click(v, *spot_on(v, base))
    perp = v.construction.lines[-1]
    before = perp.normal.copy()
    v._set_tool("move")
    press(v, 0.5, 0.35)
    drag(v, 0.7, -0.4)
    release(v, 0.7, -0.4)
    assert not np.allclose(before, perp.normal)
    assert abs(np.dot(perp.normal, base.normal)) < 1e-12, "right angle preserved"


def test_deleting_the_base_removes_the_perpendicular():
    v = viewer_with("perp")
    base = draw_a_line(v)
    click(v, 0.1, -0.5)
    click(v, *spot_on(v, base))
    perp = v.construction.lines[-1]
    assert len(v.construction.lines) == 2
    v._set_tool("delete")
    click(v, *spot_on(v, base, avoid=[perp]))  # on the base, clear of the perpendicular
    assert v.construction.lines == [], "the perpendicular cannot outlive its base"
    assert len(v.construction.points) == 3, "its points stay"


def test_triangle_tool_takes_three_clicks():
    v = viewer_with("triangle")
    click(v, 0.0, 0.0)
    click(v, 0.4, 0.0)
    assert len(v.picked) == 2 and not v.construction.triangles
    click(v, 0.0, 0.6)
    t = v.construction.triangles[0]
    assert v.picked == [] and t.label == "ABC"
    assert len(v.construction.lines) == 3 and all(s.is_segment for s in t.sides)
    assert "area" in v.message and "sum" in v.message
    assert abs(t.angles()[0] - np.pi / 2) < 1e-12


def test_triangle_tool_refuses_to_use_a_vertex_twice():
    v = viewer_with("triangle")
    click(v, 0.0, 0.0)
    click(v, 0.005, 0.0)  # inside the pick radius of the first
    assert len(v.picked) == 1 and "already a vertex" in v.message


def test_triangle_area_updates_while_a_vertex_is_dragged():
    v = viewer_with("triangle")
    for x, y in [(0.1, 0.1), (0.4, 0.0), (0.0, 0.5)]:
        click(v, x, y)
    t = v.construction.triangles[0]
    before = t.area()
    v._set_tool("move")
    press(v, 0.4, 0.0)
    drag(v, 0.7, -0.15)
    release(v, 0.7, -0.15)
    assert t.area() > before
    assert f"{t.area():.3f}" in "".join(text.get_text() for text in v.ax.texts)


def test_deleting_one_side_takes_the_triangle():
    v = viewer_with("triangle")
    for x, y in [(0.0, 0.0), (0.6, 0.0), (0.0, 0.6)]:
        click(v, x, y)
    side = v.construction.triangles[0].sides[0]
    drawn = v._paths(side)[0]
    v._set_tool("delete")
    click(v, *drawn[len(drawn) // 2])  # halfway along the side itself
    assert v.construction.triangles == [] and len(v.construction.lines) == 2
    assert len(v.construction.points) == 3


def test_meet_tool_names_a_crossing():
    v = viewer_with("meet")
    first, second = draw_a_line(v), draw_a_line(v, (0.2, 0.7), (-0.1, -0.8))
    click(v, *spot_on(v, first, avoid=[second]))
    assert v.pending is first
    click(v, *spot_on(v, second, avoid=[first]))
    meet = v.construction.points[-1]
    assert v.picked == [] and not meet.is_free and meet.kind == "meet"
    assert abs(np.dot(meet.vector, first.normal)) < 1e-12
    assert abs(np.dot(meet.vector, second.normal)) < 1e-12


def test_meet_tool_wants_lines_not_empty_space():
    v = viewer_with("meet")
    draw_a_line(v)
    click(v, -0.85, -0.5)
    assert v.picked == [] and "click on a line" in v.message


def test_a_named_meet_replaces_its_cross_marker():
    v = viewer_with("meet")
    first, second = draw_a_line(v), draw_a_line(v, (0.2, 0.7), (-0.1, -0.8))
    crosses = lambda: sum(l.get_marker() == "x" for l in v.ax.lines)
    assert crosses() == 1
    click(v, *spot_on(v, first, avoid=[second]))
    click(v, *spot_on(v, second, avoid=[first]))
    assert crosses() == 0, "the point says it better than the marker did"
    assert len(v.construction.intersections()) == 1, "the crossing is still there"


def test_dual_tool_gives_a_point_its_polar_and_a_line_its_pole():
    v = viewer_with("dual")
    click(v, 0.35, -0.45)                       # empty space: point and polar
    point, polar = v.construction.points[0], v.construction.lines[0]
    assert polar.is_polar and polar.p is point
    click(v, *spot_on(v, polar))                # the polar: back to the pole
    pole = v.construction.points[-1]
    assert not pole.is_free and np.allclose(pole.xy, point.xy, atol=1e-12)


def test_a_polar_and_its_point_undo_together():
    v = viewer_with("dual")
    click(v, 0.35, -0.45)
    key(v, "u")
    assert v.construction.points == [] and v.construction.lines == []


def test_derived_points_cannot_be_dragged():
    v = viewer_with("dual")
    click(v, 0.35, -0.45)
    click(v, *spot_on(v, v.construction.lines[0]))
    pole = v.construction.points[-1]
    where = pole.xy.copy()
    v._set_tool("move")
    press(v, *where)
    drag(v, 0.0, 0.0)
    release(v, 0.0, 0.0)
    assert np.allclose(pole.xy, where) and "built on" in v.message


def test_a_derived_point_that_loses_its_lines_stops_being_drawn():
    v = viewer_with("meet")
    first, second = draw_a_line(v), draw_a_line(v, (0.2, 0.7), (-0.1, -0.8))
    click(v, *spot_on(v, first, avoid=[second]))
    click(v, *spot_on(v, second, avoid=[first]))
    diamonds = lambda: sum(l.get_marker() == "D" for l in v.ax.lines)
    assert diamonds() == 1
    second.q.move_to(*first.p.xy)   # the two lines fall together
    second.p.move_to(*first.q.xy)
    v._redraw()
    assert v.construction.points[-1].xy is None and diamonds() == 0


def test_tool_and_flag_shortcuts():
    v = viewer_with("point")
    for shortcut, tool in [("2", "line"), ("3", "segment"), ("4", "perp"),
                           ("5", "triangle"), ("6", "meet"), ("7", "dual"),
                           ("8", "move"), ("9", "delete"), ("1", "point")]:
        key(v, shortcut)
        assert v.tool == tool
    for shortcut, flag in [("l", "labels"), ("p", "poles"), ("x", "meets"),
                           ("e", "rim"), ("b", "plain")]:
        before = v.flags[flag]
        key(v, shortcut)
        assert v.flags[flag] is not before


def test_undo_and_clear_shortcuts():
    v = viewer_with("line")
    click(v, 0.3, 0.4)
    click(v, -0.5, 0.1)
    key(v, "u")
    assert not v.construction.lines and len(v.construction.points) == 2
    key(v, "c")
    assert not v.construction.points


def test_colour_choice_applies_to_new_objects():
    v = viewer_with("point")
    v._set_color("#123456")
    click(v, 0.2, 0.2)
    v._set_tool("line")
    click(v, 0.2, 0.2)
    click(v, -0.4, 0.3)
    assert v.construction.points[0].color == "#123456"
    assert v.construction.lines[0].color == "#123456"


def test_redraw_does_not_leak_artists():
    v = viewer_with("line")
    click(v, 0.3, 0.4)
    click(v, -0.5, 0.1)
    counts = []
    for _ in range(6):
        v._redraw()
        counts.append(len(v.ax.lines) + len(v.ax.texts))
    assert len(set(counts)) == 1, f"artist count drifting: {counts}"


def test_toggles_change_what_is_drawn():
    v = viewer_with("line")
    click(v, 0.3, 0.4)
    click(v, -0.5, 0.1)
    full = len(v.ax.lines) + len(v.ax.texts)
    for flag in ("labels", "poles", "meets", "rim"):
        v.flags[flag] = False
    v._redraw()
    assert len(v.ax.lines) + len(v.ax.texts) < full
    v.flags["poles"] = True
    v._redraw()
    assert any(l.get_marker() == "*" for l in v.ax.lines)


def test_status_text_reports_the_construction():
    v = viewer_with("segment")
    click(v, 0.6, 0.1)
    click(v, -0.5, 0.4)
    text = v.status.get_text()
    assert "SEGMENT" in text and "2 points   1 lines" in text
    v._set_tool("perp")
    assert "PERPENDICULAR" in v.status.get_text()
    assert "length" in text and "rad" in text


def test_the_gclc_button_opens_a_box_and_writes_the_file():
    import os
    import tempfile

    v = viewer_with("triangle")
    for x, y in [(0.0, 0.0), (0.5, 0.0), (0.0, 0.5)]:
        click(v, x, y)
    key(v, "g")
    assert v._prompting, "the filename box is up"
    assert "esc cancels" in v.status.get_text()
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "from_the_button")
        v._prompt[0].set_val(path)          # as if typed, then enter
        assert not v._prompting, "submitting puts the box away"
        written = path + ".gcl"
        assert os.path.exists(written) and "wrote" in v.message
        with open(written, encoding="utf-8") as handle:
            text = handle.read()
        assert "dim 100 100" in text and "triangle ABC" in text


def test_reopening_the_box_does_not_write_anything_by_itself():
    """Filling the box in counts as a submit, so it must happen while it is shut."""
    import os
    import tempfile

    v = viewer_with("point")
    with tempfile.TemporaryDirectory() as folder:
        cwd = os.getcwd()
        os.chdir(folder)
        try:
            key(v, "g")
            v._prompt[0].set_val("first")     # save once under another name
            assert os.path.exists("first.gcl")
            key(v, "g")                       # and open it again
            assert v._prompting and os.listdir(folder) == ["first.gcl"]
        finally:
            os.chdir(cwd)


def test_the_plain_toggle_takes_the_colour_out_of_the_picture():
    from elliptic.model import PALETTE

    v = viewer_with("triangle")
    for x, y in [(0.0, 0.0), (0.5, 0.0), (0.0, 0.5)]:
        click(v, x, y)
    drawn = lambda: {line.get_color() for line in v.ax.lines}
    assert drawn() & set(PALETTE), "colourful to start with"

    key(v, "b")
    assert not drawn() & set(PALETTE), "and black once it is plain"
    assert v.ax.patches[0].get_facecolor()[:3] == (1.0, 1.0, 1.0), "on white paper"

    key(v, "b")
    assert drawn() & set(PALETTE), "and the colour comes back"


def test_saving_follows_what_the_picture_looks_like():
    v = viewer_with("point")
    click(v, 0.2, 0.2)
    key(v, "g")
    assert v._plain_export is False
    key(v, "escape")

    key(v, "b")          # plain on: the same save is now plain
    key(v, "g")
    assert v._plain_export is True

    def save(v=v):
        v._prompt[0].set_val("bw")

    assert in_an_empty_folder(save) == ["bw.gcl"]


def test_shift_g_saves_the_plain_black_and_white_version():
    v = viewer_with("triangle")
    for x, y in [(0.0, 0.0), (0.5, 0.0), (0.0, 0.5)]:
        click(v, x, y)
    key(v, "G")
    assert v._prompting and "plain" in v.status.get_text()

    written = {}

    def save(v=v):
        key(v, "G")
        v._prompt[0].set_val("bw")

    def read(v=v):
        save()
        written["text"] = open("bw.gcl", encoding="utf-8").read()

    assert in_an_empty_folder(read) == ["bw.gcl"]
    assert "color" not in written["text"] and "drawdashellipsearc" in written["text"]
    assert "plain GCLC" in v.message

    key(v, "g")  # and plain does not stick: the next save is in colour again
    assert v._prompting and v._plain_export is False


def test_typing_a_filename_does_not_drive_the_tools():
    v = viewer_with("point")
    key(v, "g")
    for typed in ("1", "5", "c", "u", "l"):   # tool, action and toggle shortcuts
        key(v, typed)
    assert v.tool == "point" and v.flags["labels"] is True
    assert v.construction.points == [] and v._prompting


def test_escape_closes_the_filename_box():
    v = viewer_with("point")
    key(v, "g")
    key(v, "escape")
    assert not v._prompting and "cancelled" in v.message
    key(v, "5")
    assert v.tool == "triangle", "and the keyboard is back to the tools"


def in_an_empty_folder(work):
    """Run `work` somewhere disposable, and hand back what it left behind."""
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        cwd = os.getcwd()
        os.chdir(folder)
        try:
            work()
            return sorted(os.listdir(folder))
        finally:
            os.chdir(cwd)


def test_cancelling_writes_no_file():
    """Letting the box go counts as a submit to matplotlib; it must not save."""
    for cancel in ("escape", "click"):
        v = viewer_with("point")

        def give_up(v=v, cancel=cancel):
            key(v, "g")
            if cancel == "escape":
                key(v, "escape")
            else:
                click(v, 0.3, 0.3)

        assert in_an_empty_folder(give_up) == [], f"{cancel} left a file behind"
        assert not v._prompting and "cancelled" in v.message


def test_saving_still_writes_when_you_mean_it():
    v = viewer_with("point")
    click(v, 0.2, 0.2)

    def save(v=v):
        key(v, "g")
        v._prompt[0].set_val("wanted")

    assert in_an_empty_folder(save) == ["wanted.gcl"]
    assert "wrote" in v.message


def test_clicking_the_disk_puts_the_filename_box_away():
    v = viewer_with("point")
    key(v, "g")
    click(v, 0.3, 0.3)
    assert not v._prompting
    assert v.construction.points == [], "that click dismissed, it did not draw"


def test_a_full_session_renders():
    """Every tool in turn, then the toggles, then draw the whole figure."""
    v = viewer_with("point")
    for x, y in [(0.35, 0.45), (-0.6, 0.2), (0.1, -0.7), (0.8, -0.3)]:
        click(v, x, y)
    v._set_tool("line")
    click(v, 0.35, 0.45); click(v, -0.6, 0.2)
    click(v, 0.1, -0.7); click(v, 0.8, -0.3)
    v._set_tool("segment")
    click(v, -0.6, 0.2); click(v, 0.8, -0.3)
    v._set_tool("triangle")
    click(v, 0.35, 0.45); click(v, -0.6, 0.2); click(v, 0.1, -0.7)
    v._set_tool("meet")
    click(v, *spot_on(v, v.construction.lines[0], avoid=[v.construction.lines[1]]))
    click(v, *spot_on(v, v.construction.lines[1], avoid=[v.construction.lines[0]]))
    v._set_tool("dual")
    click(v, 0.8, -0.3)
    v._set_tool("move")
    press(v, 0.35, 0.45); drag(v, 0.2, 0.6); release(v, 0.2, 0.6)
    v._set_tool("delete")
    click(v, 0.1, -0.7)
    for flag in ("poles", "labels", "meets", "rim"):
        key(v, {"poles": "p", "labels": "l", "meets": "x", "rim": "e"}[flag])
    v.fig.canvas.draw()
    assert v.construction.triangles == [], "its vertex went with the deleted point"
    assert all(p.is_free for p in v.construction.points), "so did the meet"
    assert len(v.construction.points) == 3 and len(v.construction.lines) == 4


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} checks passed")
