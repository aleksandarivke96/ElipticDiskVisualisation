"""Drives the tools with synthetic clicks: `python3 -m tests.test_viewer`.

The viewer is toolkit-free - it takes clicks in disk coordinates and hands back
a scene - so these go straight at it, no window and no Qt involved.  What the
window does with the result is `tests.test_ui`'s problem.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from elliptic import EllipticDiskViewer
from elliptic import geometry as geo
from elliptic import scene as sc


def viewer_with(tool="point"):
    """The older tool checks use the orthogonal chart's raw model coordinates.

    Application startup is tested separately in the reference-circle check.
    """
    v = EllipticDiskViewer()
    v.flags["conformal"] = False
    v.set_tool(tool)
    return v


def press(v, x, y):
    v.press(x, y)


def drag(v, x, y):
    v.motion(x, y)


def release(v, x=None, y=None):
    v.release()


def click(v, x, y):
    v.press(x, y)
    v.release()


def key(v, k):
    v.key(k)


def marks(v, shape):
    return [m for m in v.scene().marks if m.shape == shape]


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
    release(v)
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
    v.set_tool("line")
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
    v.set_tool("move")
    press(v, 0.3, 0.4)
    drag(v, 0.1, -0.6)
    release(v)
    assert np.allclose(line.p.xy, [0.1, -0.6])
    assert not np.allclose(before, line.normal)
    assert abs(np.dot(line.normal, line.p.vector)) < 1e-12


def test_move_tool_ignores_empty_space():
    v = viewer_with("point")
    click(v, 0.3, 0.4)
    v.set_tool("move")
    press(v, -0.8, -0.8)
    drag(v, 0.0, 0.0)
    release(v)
    assert np.allclose(v.construction.points[0].xy, [0.3, 0.4])


def test_delete_tool_removes_a_point_and_its_lines():
    v = viewer_with("line")
    click(v, 0.3, 0.4)
    click(v, -0.5, 0.1)
    v.set_tool("delete")
    click(v, 0.3, 0.4)
    assert len(v.construction.points) == 1 and not v.construction.lines


def test_delete_tool_hits_a_line_without_touching_its_points():
    v = viewer_with("line")
    click(v, 0.5, 0.0)
    click(v, -0.5, 0.0)          # a diameter along y = 0
    v.set_tool("delete")
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
    v.set_tool("line")
    click(v, *a)
    click(v, *b)
    v.set_tool(tool)
    return v.construction.lines[-1]


def spot_on(v, line, avoid=()):
    """A point genuinely on the drawn line, clear of the points and of `avoid`."""
    samples = np.vstack(v.paths(line))[10:-10]  # keep away from the rim
    others = [p.xy for p in v.construction.points]
    for other in avoid:
        others.extend(np.vstack(v.paths(other)))
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
    v.set_tool("perp")
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
    v = viewer_with("perp")
    base = draw_a_line(v)
    pole = geo.polar_point(base.normal)
    click(v, *pole)
    click(v, *spot_on(v, base))
    assert not any(l.is_perpendicular for l in v.construction.lines)
    assert "pole" in v.message


def test_perpendicular_foot_and_right_angle_are_drawn():
    v = viewer_with("perp")
    base = draw_a_line(v)
    click(v, 0.1, -0.5)
    click(v, *spot_on(v, base))
    assert marks(v, "square"), "foot marker missing"
    assert "perpendicular" in v.status_text() and "distance" in v.status_text()


def test_perpendicular_updates_when_the_base_is_dragged():
    v = viewer_with("perp")
    base = draw_a_line(v)
    click(v, 0.1, -0.5)
    click(v, *spot_on(v, base))
    perp = v.construction.lines[-1]
    before = perp.normal.copy()
    v.set_tool("move")
    press(v, 0.5, 0.35)
    drag(v, 0.7, -0.4)
    release(v)
    assert not np.allclose(before, perp.normal)
    assert abs(np.dot(perp.normal, base.normal)) < 1e-12, "right angle preserved"


def test_deleting_the_base_removes_the_perpendicular():
    v = viewer_with("perp")
    base = draw_a_line(v)
    click(v, 0.1, -0.5)
    click(v, *spot_on(v, base))
    perp = v.construction.lines[-1]
    assert len(v.construction.lines) == 2
    v.set_tool("delete")
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
    v.set_tool("move")
    press(v, 0.4, 0.0)
    drag(v, 0.7, -0.15)
    release(v)
    assert t.area() > before
    assert f"{t.area():.3f}" in "".join(text.text for text in v.scene().texts)


def test_deleting_one_side_takes_the_triangle():
    v = viewer_with("triangle")
    for x, y in [(0.0, 0.0), (0.6, 0.0), (0.0, 0.6)]:
        click(v, x, y)
    side = v.construction.triangles[0].sides[0]
    drawn = v.paths(side)[0]
    v.set_tool("delete")
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
    assert len(marks(v, "cross")) == 1
    click(v, *spot_on(v, first, avoid=[second]))
    click(v, *spot_on(v, second, avoid=[first]))
    assert marks(v, "cross") == [], "the point says it better than the marker did"
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
    v.set_tool("move")
    press(v, *where)
    drag(v, 0.0, 0.0)
    release(v)
    assert np.allclose(pole.xy, where) and "built on" in v.message


def test_a_derived_point_that_loses_its_lines_stops_being_drawn():
    v = viewer_with("meet")
    first, second = draw_a_line(v), draw_a_line(v, (0.2, 0.7), (-0.1, -0.8))
    click(v, *spot_on(v, first, avoid=[second]))
    click(v, *spot_on(v, second, avoid=[first]))
    assert len(marks(v, "diamond")) == 1
    second.q.move_to(*first.p.xy)   # the two lines fall together
    second.p.move_to(*first.q.xy)
    assert v.construction.points[-1].xy is None and marks(v, "diamond") == []


def test_tool_and_flag_shortcuts():
    v = viewer_with("point")
    for shortcut, tool in [("2", "line"), ("3", "segment"), ("4", "perp"),
                           ("5", "triangle"), ("6", "meet"), ("7", "dual"),
                           ("8", "move"), ("9", "delete"), ("1", "point")]:
        key(v, shortcut)
        assert v.tool == tool
    for shortcut, flag in [("l", "labels"), ("p", "poles"), ("x", "meets"),
                           ("e", "rim"), ("b", "plain"), ("o", "conformal"),
                           ("s", "sphere"), ("r", "rays"), ("a", "antipodes")]:
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
    v.set_color("#123456")
    click(v, 0.2, 0.2)
    v.set_tool("line")
    click(v, 0.2, 0.2)
    click(v, -0.4, 0.3)
    assert v.construction.points[0].color == "#123456"
    assert v.construction.lines[0].color == "#123456"


def test_the_scene_is_rebuilt_not_accumulated():
    v = viewer_with("line")
    click(v, 0.3, 0.4)
    click(v, -0.5, 0.1)
    counts = [len(v.scene()) for _ in range(6)]
    assert len(set(counts)) == 1, f"scene size drifting: {counts}"


def test_toggles_change_what_is_drawn():
    v = viewer_with("line")
    click(v, 0.3, 0.4)
    click(v, -0.5, 0.1)
    full = len(v.scene())
    for flag in ("labels", "poles", "meets", "rim"):
        v.flags[flag] = False
    assert len(v.scene()) < full
    v.flags["poles"] = True
    assert marks(v, "star"), "a pole for every line"


def test_status_text_reports_the_construction():
    v = viewer_with("segment")
    click(v, 0.6, 0.1)
    click(v, -0.5, 0.4)
    text = v.status_text()
    assert "SEGMENT" in text and "2 points   1 lines" in text
    assert "length" in text and "rad" in text
    v.set_tool("perp")
    assert "PERPENDICULAR" in v.status_text()


def test_the_gclc_prompt_writes_the_file():
    import os
    import tempfile

    v = viewer_with("triangle")
    for x, y in [(0.0, 0.0), (0.5, 0.0), (0.0, 0.5)]:
        click(v, x, y)
    key(v, "g")
    assert v.prompting, "the filename box is up"
    assert "esc cancels" in v.status_text()
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "from_the_button")
        v.submit_prompt(path)
        assert not v.prompting, "submitting puts the box away"
        written = path + ".gcl"
        assert os.path.exists(written) and "wrote" in v.message
        with open(written, encoding="utf-8") as handle:
            text = handle.read()
        assert "dim 100 100" in text and "triangle ABC" in text


def test_a_submit_with_no_box_up_writes_nothing():
    """Whatever the window does with its line edit, only an open box saves."""
    v = viewer_with("point")
    click(v, 0.2, 0.2)

    def stray(v=v):
        assert v.submit_prompt("stray") is None

    assert in_an_empty_folder(stray) == []


def test_the_conformal_toggle_redraws_the_same_construction_elsewhere():
    v = viewer_with("line")
    click(v, 0.5, 0.35)
    click(v, -0.45, 0.15)
    line, a = v.construction.lines[0], v.construction.points[0]
    flat = np.vstack(v.paths(line))
    assert v.projection is geo.ORTHOGONAL

    key(v, "o")
    assert v.projection is geo.STEREOGRAPHIC
    curved = np.vstack(v.paths(line))
    assert not np.allclose(flat[len(flat) // 2], curved[len(curved) // 2]), "moved"
    # the model did not move: only where it is drawn changed
    assert np.allclose(a.xy, [0.5, 0.35]), "the point keeps its place"
    for xy in curved:
        assert abs(np.dot(geo.STEREOGRAPHIC.lift(*xy), line.normal)) < 1e-6
        assert np.linalg.norm(xy) <= 1.0 + 1e-9

    key(v, "o")
    assert np.allclose(np.vstack(v.paths(line)), flat), "and back again"


def test_the_scene_itself_does_not_depend_on_the_projection():
    """The sphere pane draws the same vectors whichever way the disk is flattened."""
    v = viewer_with("triangle")
    for x, y in [(0.1, 0.1), (0.5, -0.1), (-0.2, 0.55)]:
        click(v, x, y)
    before = [c.points.copy() for c in v.scene().curves]
    key(v, "o")
    after = [c.points for c in v.scene().curves]
    assert len(before) == len(after)
    for one, other in zip(before, after):
        assert np.allclose(one, other)


def test_clicking_and_dragging_work_in_the_conformal_view():
    v = viewer_with("point")
    key(v, "o")
    click(v, 0.4, -0.2)
    a = v.construction.points[0]
    # the point sits under the cursor when drawn the way it was clicked
    assert np.allclose(v.projection.project(a.vector), [0.4, -0.2], atol=1e-9)
    assert not np.allclose(a.xy, [0.4, -0.2]), "and it is not just the raw coordinates"

    v.set_tool("move")
    press(v, 0.4, -0.2)          # picking it up means finding it on screen
    drag(v, -0.1, 0.55)
    release(v)
    assert np.allclose(v.projection.project(a.vector), [-0.1, 0.55], atol=1e-9)

    key(v, "o")                  # the same point, seen straight down again
    assert np.allclose(geo.ORTHOGONAL.project(a.vector), a.xy, atol=1e-12)


def test_the_conformal_view_is_what_gets_exported():
    v = viewer_with("segment")
    click(v, 0.5, 0.35)
    click(v, -0.45, 0.15)
    key(v, "o")

    written = {}

    def save(v=v):
        key(v, "g")
        v.submit_prompt("curved")
        written["text"] = open("curved.gcl", encoding="utf-8").read()

    assert in_an_empty_folder(save) == ["curved.gcl"]
    assert "View: stereographic" in written["text"]
    assert "arc of a circle" in written["text"]


def test_the_plain_toggle_takes_the_colour_out_of_the_picture():
    from elliptic.model import PALETTE

    v = viewer_with("triangle")
    for x, y in [(0.0, 0.0), (0.5, 0.0), (0.0, 0.5)]:
        click(v, x, y)
    drawn = lambda: {c.color for c in v.scene().curves} | {m.color for m in v.scene().marks}
    assert drawn() & set(PALETTE), "colourful to start with"

    key(v, "b")
    assert not drawn() & set(PALETTE), "and black once it is plain"
    assert sc.PLAIN_INK in drawn()

    key(v, "b")
    assert drawn() & set(PALETTE), "and the colour comes back"


def test_saving_follows_what_the_picture_looks_like():
    v = viewer_with("point")
    click(v, 0.2, 0.2)
    key(v, "g")
    assert v.plain_export is False
    key(v, "escape")

    key(v, "b")          # plain on: the same save is now plain
    key(v, "g")
    assert v.plain_export is True

    def save(v=v):
        v.submit_prompt("bw")

    assert in_an_empty_folder(save) == ["bw.gcl"]


def test_shift_g_saves_the_plain_black_and_white_version():
    v = viewer_with("triangle")
    for x, y in [(0.0, 0.0), (0.5, 0.0), (0.0, 0.5)]:
        click(v, x, y)
    key(v, "G")
    assert v.prompting and "plain" in v.status_text()

    written = {}

    def read(v=v):
        key(v, "G")
        v.submit_prompt("bw")
        written["text"] = open("bw.gcl", encoding="utf-8").read()

    assert in_an_empty_folder(read) == ["bw.gcl"]
    assert "color" not in written["text"] and "drawdashellipsearc" in written["text"]
    assert "plain GCLC" in v.message

    key(v, "g")  # and plain does not stick: the next save is in colour again
    assert v.prompting and v.plain_export is False


def test_typing_a_filename_does_not_drive_the_tools():
    v = viewer_with("point")
    key(v, "g")
    for typed in ("1", "5", "c", "u", "l"):   # tool, action and toggle shortcuts
        key(v, typed)
    assert v.tool == "point" and v.flags["labels"] is True
    assert v.construction.points == [] and v.prompting


def test_escape_closes_the_filename_box():
    v = viewer_with("point")
    key(v, "g")
    key(v, "escape")
    assert not v.prompting and "cancelled" in v.message
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
    for cancel in ("escape", "click"):
        v = viewer_with("point")

        def give_up(v=v, cancel=cancel):
            key(v, "g")
            if cancel == "escape":
                key(v, "escape")
            else:
                click(v, 0.3, 0.3)

        assert in_an_empty_folder(give_up) == [], f"{cancel} left a file behind"
        assert not v.prompting and "cancelled" in v.message


def test_saving_still_writes_when_you_mean_it():
    v = viewer_with("point")
    click(v, 0.2, 0.2)

    def save(v=v):
        key(v, "g")
        v.submit_prompt("wanted")

    assert in_an_empty_folder(save) == ["wanted.gcl"]
    assert "wrote" in v.message


def test_clicking_the_disk_puts_the_filename_box_away():
    v = viewer_with("point")
    key(v, "g")
    click(v, 0.3, 0.3)
    assert not v.prompting
    assert v.construction.points == [], "that click dismissed, it did not draw"


def test_the_pick_radius_follows_the_canvas_size():
    """13 px is 13 px whether the window is small or filling the screen."""
    v = viewer_with("point")
    click(v, 0.0, 0.0)
    v.scale = 100.0                       # a small canvas: 13 px is a long way
    assert v.point_at(0.10, 0.0) is not None
    v.scale = 1000.0                      # a big one: the same click misses
    assert v.point_at(0.10, 0.0) is None


def test_a_full_session_builds_a_scene():
    """Every tool in turn, then the toggles, then look at what would be drawn."""
    v = viewer_with("point")
    for x, y in [(0.35, 0.45), (-0.6, 0.2), (0.1, -0.7), (0.8, -0.3)]:
        click(v, x, y)
    v.set_tool("line")
    click(v, 0.35, 0.45); click(v, -0.6, 0.2)
    click(v, 0.1, -0.7); click(v, 0.8, -0.3)
    v.set_tool("segment")
    click(v, -0.6, 0.2); click(v, 0.8, -0.3)
    v.set_tool("triangle")
    click(v, 0.35, 0.45); click(v, -0.6, 0.2); click(v, 0.1, -0.7)
    v.set_tool("meet")
    click(v, *spot_on(v, v.construction.lines[0], avoid=[v.construction.lines[1]]))
    click(v, *spot_on(v, v.construction.lines[1], avoid=[v.construction.lines[0]]))
    v.set_tool("dual")
    click(v, 0.8, -0.3)
    v.set_tool("move")
    press(v, 0.35, 0.45); drag(v, 0.2, 0.6); release(v)
    v.set_tool("delete")
    click(v, 0.1, -0.7)
    for shortcut in ("p", "l", "x", "e", "a", "r"):
        key(v, shortcut)
    assert v.construction.triangles == [], "its vertex went with the deleted point"
    assert all(p.is_free for p in v.construction.points), "so did the meet"
    assert len(v.construction.points) == 3 and len(v.construction.lines) == 4

    scene = v.scene()
    assert scene.curves and scene.marks
    for curve in scene.curves:
        assert curve.points.ndim == 2 and curve.points.shape[1] == 3
        assert np.allclose(np.linalg.norm(curve.points, axis=1), 1.0, atol=1e-9), \
            "every drawn curve lives on the unit sphere"


# ---------------------------------------------------------------- the circle tool


def test_the_default_view_matches_the_two_arc_reference_circle():
    """The textbook p/q placement is two circular clines, not one ellipse."""
    v = EllipticDiskViewer(samples=1024)
    assert v.projection is geo.STEREOGRAPHIC
    v.set_tool("circle")
    click(v, 0.85, 0.0)
    click(v, 0.50, 0.30)

    circle = v.construction.circles[0]
    assert np.allclose(v.screen(circle.centre.vector), [0.85, 0.0])
    assert np.allclose(v.screen(circle.through.vector), [0.50, 0.30])
    paths = v.circle_paths(circle)
    assert len(paths) == 2, "the far part re-enters at the opposite rim"

    arcs = geo.circle_arcs(*circle.axis_radius())
    carriers = [geo.STEREOGRAPHIC.point_conic(axis, circle.radius())
                for axis, *_ in arcs]
    centres = [shape[0] for shape in carriers]
    radii = [np.linalg.norm(shape[1]) for shape in carriers]
    assert np.allclose(centres, [[1.01019956, 0.0], [-1.50731159, 0.0]], atol=1e-7)
    assert np.allclose(radii, [0.59186450, 0.88311682], atol=1e-7)
    assert np.allclose(paths[0][[0, -1]],
                       [[0.82666813, 0.56268979], [0.82666813, -0.56268979]],
                       atol=1e-7)
    assert np.allclose(paths[1][[0, -1]],
                       [[-0.82666813, 0.56268979], [-0.82666813, -0.56268979]],
                       atol=1e-7)


def test_command_line_points_use_the_selected_view_coordinates():
    from main import build

    args = SimpleNamespace(points=[0.85, 0.0, 0.50, 0.30],
                           lines=None, segments=None, triangles=None, perps=None,
                           polars=None, bisects=None, midpoints=None,
                           meets=None, circles=[0, 1])
    for conformal in (True, False):
        v = EllipticDiskViewer()
        v.flags["conformal"] = conformal
        build(v, args)
        shown = [v.screen(point.vector) for point in v.construction.points]
        assert np.allclose(shown, [[0.85, 0.0], [0.50, 0.30]])
    assert len(v.construction.circles) == 1


def test_circle_tool_joins_two_clicks():
    v = viewer_with("circle")
    click(v, 0.1, 0.1)
    assert v.pending is not None and not v.construction.circles
    click(v, 0.5, 0.2)
    assert v.pending is None
    circle = v.construction.circles[0]
    assert len(v.construction.points) == 2
    assert circle.centre.label == "A" and circle.through.label == "B"
    assert "radius" in v.message


def test_circle_tool_snaps_onto_existing_points():
    v = viewer_with("point")
    click(v, 0.2, 0.3)
    click(v, -0.4, 0.1)
    v.set_tool("circle")
    click(v, 0.202, 0.298)   # within the pick radius of A
    click(v, -0.398, 0.102)  # and of B
    assert len(v.construction.points) == 2, "no new points were made"
    circle = v.construction.circles[0]
    assert circle.centre is v.construction.points[0]
    assert circle.through is v.construction.points[1]


def test_circle_tool_refuses_the_same_point_twice():
    v = viewer_with("circle")
    click(v, 0.2, 0.3)
    click(v, 0.2, 0.3)  # snaps onto the held point: no circle to draw
    assert not v.construction.circles and v.pending is None
    assert "same elliptic point" in v.message


def test_the_key_0_arms_the_circle_tool():
    v = viewer_with("point")
    key(v, "0")
    assert v.tool == "circle"


def test_a_circle_reaches_the_scene_and_both_projections():
    v = viewer_with("circle")
    click(v, 0.15, 0.05)
    click(v, 0.45, 0.05)
    circle = v.construction.circles[0]
    layer3 = [c for c in v.scene().curves if c.layer == 3]
    assert any(len(c.points) > 50 for c in layer3), "the circle is a drawn curve"
    for conformal in (False, True):
        v.flags["conformal"] = conformal
        for path in v.circle_paths(circle):
            assert np.all(np.linalg.norm(path, axis=1) < 1 + 1e-9), "in the disk"


def test_a_circle_through_the_rim_draws_as_two_pieces():
    v = viewer_with("circle")
    click(v, 0.85, 0.0)
    click(v, 0.35, 0.0)
    circle = v.construction.circles[0]
    assert len(v.circle_paths(circle)) == 2
    pieces = [c for c in v.scene().curves if c.layer == 3 and len(c.points) > 50]
    assert len(pieces) == 2, "the fold shows up in the scene too"


def test_delete_tool_removes_a_circle_but_not_its_points():
    v = viewer_with("circle")
    click(v, 0.1, 0.1)
    click(v, 0.5, 0.1)
    v.set_tool("delete")
    circle = v.construction.circles[0]
    spots = v.circle_paths(circle)[0]  # on the curve, far from either point
    others = np.array([p.xy for p in v.construction.points])
    away = spots[np.argmax(np.linalg.norm(spots[:, None] - others, axis=2).min(axis=1))]
    click(v, float(away[0]), float(away[1]))
    assert not v.construction.circles
    assert len(v.construction.points) == 2, "the points survive their circle"


def test_deleting_the_centre_takes_the_circle_with_it():
    v = viewer_with("circle")
    click(v, 0.1, 0.1)
    click(v, 0.5, 0.1)
    v.set_tool("delete")
    click(v, 0.1, 0.1)
    assert not v.construction.circles and len(v.construction.points) == 1


def test_dragging_the_centre_carries_the_circle():
    v = viewer_with("circle")
    click(v, 0.1, 0.1)
    click(v, 0.4, 0.1)
    radius = v.construction.circles[0].radius()
    v.set_tool("move")
    press(v, 0.1, 0.1)
    drag(v, -0.2, 0.25)
    release(v)
    circle = v.construction.circles[0]
    assert np.allclose(circle.centre.xy, [-0.2, 0.25])
    assert abs(circle.radius() - radius) > 1e-3, "the through point stayed put"
    assert abs(circle.radius() - geo.distance(circle.centre.vector,
                                              circle.through.vector)) < 1e-12


def test_a_circle_through_a_pole_at_half_pi_says_it_is_the_polar():
    v = viewer_with("line")
    click(v, 0.3, 0.0)
    click(v, 0.0, 0.3)
    line = v.construction.lines[0]
    v.set_tool("dual")
    middle = v.paths(line)[0][256]  # on the curve, away from either point
    click(v, float(middle[0]), float(middle[1]))  # a line clicked gives its pole
    pole = v.construction.points[-1]
    assert not pole.is_free
    v.set_tool("circle")
    click(v, *map(float, v.screen(pole.vector)))       # centre: the pole
    click(v, 0.3, 0.0)                                  # through a point of the line
    assert "polar" in v.message, "radius pi/2 is called out for what it is"


def test_undo_takes_the_circle_back():
    v = viewer_with("circle")
    click(v, 0.1, 0.1)
    click(v, 0.5, 0.1)
    v.action("undo")
    assert not v.construction.circles
    assert len(v.construction.points) == 2, "the clicked points are their own actions"


def test_the_status_line_counts_circles():
    v = viewer_with("circle")
    click(v, 0.1, 0.1)
    click(v, 0.5, 0.1)
    assert "1 circles" in v.status_text()


# ---------------------------------------------------------------- rotation

def rotating_rig():
    """A triangle, a pole of one side, and the rig's numbers written down."""
    v = EllipticDiskViewer()
    v.set_tool("triangle")
    for x, y in [(0.05, 0.08), (0.3, -0.05), (-0.15, 0.25)]:
        v.press(x, y)
        v.release()
    v.set_tool("dual")
    side = v.construction.lines[0]
    path = v.paths(side)[0]
    v.press(*path[len(path) // 2])  # on the line, away from its ends: its pole
    v.release()
    c = v.construction
    assert any(not p.is_free for p in c.points), "the rig owns a derived point"
    return v, c, {
        "vectors": [p.vector.copy() for p in c.points],
        "area": c.triangles[0].area(),
        "lengths": [line.length() for line in c.lines if line.is_segment],
        "history": len(c._created),
    }


def same_elliptic_point(a, b) -> bool:
    return abs(abs(float(np.dot(a, b))) - 1.0) < 1e-9


def test_rotating_is_an_isometry_about_any_pivot():
    """The whole figure turns; no distance, angle or area budges."""
    v, c, before = rotating_rig()
    v.rotate(37.0)                       # about the centre of the disk
    v.set_pivot(c.points[1])
    v.rotate(-64.0)                      # then about a vertex
    after = [p.vector for p in c.points]
    for i in range(len(after)):
        for j in range(i):
            assert abs(geo.distance(after[i], after[j])
                       - geo.distance(before["vectors"][i], before["vectors"][j])) < 1e-9
    assert abs(c.triangles[0].area() - before["area"]) < 1e-9
    for line, length in zip([l for l in c.lines if l.is_segment], before["lengths"]):
        assert abs(line.length() - length) < 1e-9
    assert "isometry" in v.message and "about B" in v.message


def test_the_pivot_tool_picks_the_point_and_it_stays_put():
    v, c, _ = rotating_rig()
    a = c.points[0]
    v.set_tool("pivot")
    v.press(*v.screen(a.vector))         # click on A, as drawn right now
    v.release()
    assert v.pivot is a and v.turned == 0.0
    held = a.vector.copy()
    other = c.points[1].vector.copy()
    v.rotate(58.0)
    assert same_elliptic_point(a.vector, held), "the pivot is the fixed point"
    assert not same_elliptic_point(c.points[1].vector, other), "the rest turned"
    expected = geo.rotation(held, np.radians(58.0)) @ other
    assert same_elliptic_point(c.points[1].vector, expected)


def test_the_pivot_tool_on_empty_space_makes_the_point():
    v = EllipticDiskViewer()
    v.set_tool("pivot")
    v.press(0.4, -0.2)
    v.release()
    assert v.pivot is v.construction.points[0]
    assert "turns about A" in v.message


def test_a_deleted_pivot_falls_back_to_the_centre():
    v, c, _ = rotating_rig()
    v.set_pivot(c.points[0])
    c.delete(c.points[0])
    assert v.pivot_text() == "about the centre"
    assert v.live_pivot() is None
    v.rotate(20.0)                       # still turns, now about the disk axis
    assert "about the centre" in v.message


def test_the_slider_coming_home_puts_everything_back():
    v, c, before = rotating_rig()
    v.set_pivot(c.points[2])
    v.rotate(141.0)   # far enough to push a vertex out through the rim
    v.rotate(0.0)
    for point, vector in zip(c.points, before["vectors"]):
        assert same_elliptic_point(point.vector, vector), "back where it began"


def test_choosing_a_pivot_restarts_the_slider():
    v, c, _ = rotating_rig()
    v.rotate(90.0)
    v.set_pivot(c.points[0])
    assert v.turned == 0.0, "a fresh pivot, a fresh zero - nothing snaps back"


def test_rotation_wraps_at_half_a_turn_and_spares_the_history():
    v, c, before = rotating_rig()
    v.rotate(170.0)
    for _ in range(10):
        v.key("right")        # 3 degrees each: through +180 and out the far side
    assert abs(v.turned - (-160.0)) < 1e-9
    assert len(c._created) == before["history"], "rotating made nothing to undo"
    v.key("left")
    assert abs(v.turned - (-163.0)) < 1e-9


def test_the_pivot_wears_a_ring_in_the_scene():
    v, c, _ = rotating_rig()
    rings = lambda: sum(1 for m in v.scene().marks
                        if m.shape == "ring" and m.size == 15.0)
    assert rings() == 0
    v.set_pivot(c.points[0])
    assert rings() == 1


def test_the_bisect_tool_takes_two_lines_and_makes_the_pair():
    v = EllipticDiskViewer()
    v.set_tool("line")
    for x, y in [(0.3, 0.1), (-0.3, 0.2), (0.1, -0.35), (-0.1, 0.4)]:
        v.press(x, y)
        v.release()
    v.set_tool("bisect")
    v.press(0.7, 0.7)  # empty space: not a line
    assert "click on a line" in v.message
    for line in v.construction.lines[:2]:
        path = v.paths(line)[0]
        v.press(*path[len(path) // 2])
        v.release()
    made = [line for line in v.construction.lines if line.is_bisector]
    assert len(made) == 2
    assert "perpendicular to each other" in v.message
    assert "equal angles" in v.describe(made[0])
    assert v.paths(made[0]), "drawn as a whole line"


def test_the_midpoint_tool_takes_two_points():
    v = EllipticDiskViewer()
    v.set_tool("midpoint")
    v.press(0.3, 0.1)
    v.release()
    assert "now pick the second point" in v.message
    v.press(-0.25, 0.35)
    v.release()
    made = [p for p in v.construction.points if not p.is_free]
    assert len(made) == 1 and made[0].kind == "midpoint"
    assert "midpoint of" in v.describe(made[0])
    ends = [p for p in v.construction.points if p.is_free]
    assert abs(geo.distance(made[0].vector, ends[0].vector)
               - geo.distance(made[0].vector, ends[1].vector)) < 1e-9


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} checks passed")
