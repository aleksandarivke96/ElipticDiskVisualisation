"""Checks on the construction model: run with `python3 -m tests.test_model`."""

from __future__ import annotations

import numpy as np

from elliptic import geometry as geo
from elliptic.model import LINE, SEGMENT, Construction


def test_labels_and_colours_cycle():
    c = Construction()
    pts = [c.add_point(0.1 * i, 0.0) for i in range(-4, 5) if i]
    assert [p.label for p in pts][:4] == ["A", "B", "C", "D"]
    lines = [c.add_line(pts[0], p) for p in pts[1:]]
    assert [l.label for l in lines][:3] == ["a", "b", "c"]
    assert len({p.color for p in pts}) > 1


def test_labels_are_reused_after_deletion():
    c = Construction()
    a, b = c.add_point(0.1, 0.1), c.add_point(-0.3, 0.2)
    c.delete(a)
    assert c.add_point(0.5, 0.5).label == "A"  # the freed label comes back
    assert b.label == "B"


def test_line_follows_its_points():
    c = Construction()
    a, b = c.add_point(0.3, 0.0), c.add_point(0.0, 0.4)
    line = c.add_line(a, b)
    before = line.normal.copy()
    b.move_to(0.0, -0.4)
    assert not np.allclose(before, line.normal)
    assert abs(np.dot(line.normal, a.vector)) < 1e-12
    assert abs(np.dot(line.normal, b.vector)) < 1e-12


def test_moving_a_point_clamps_into_the_disk():
    c = Construction()
    p = c.add_point(0.0, 0.0)
    p.move_to(3.0, 4.0)
    assert np.allclose(p.xy, [0.6, 0.8])


def test_degenerate_joins_are_refused():
    c = Construction()
    a = c.add_point(0.2, 0.3)
    b = c.add_point(1.0, 0.0)
    d = c.add_point(-1.0, 0.0)  # the same elliptic point as b
    assert c.add_line(a, a) is None
    assert c.add_line(b, d) is None
    assert c.lines == []


def test_deleting_a_point_removes_its_lines():
    c = Construction()
    a, b, d = c.add_point(0.2, 0.2), c.add_point(-0.4, 0.1), c.add_point(0.0, -0.5)
    c.add_line(a, b)
    c.add_line(b, d)
    keep = c.add_line(a, d)
    c.delete(b)
    assert c.points == [a, d] and c.lines == [keep]


def test_deleting_a_line_keeps_its_points():
    c = Construction()
    a, b = c.add_point(0.2, 0.2), c.add_point(-0.4, 0.1)
    line = c.add_line(a, b)
    c.delete(line)
    assert c.lines == [] and c.points == [a, b]


def test_undo_walks_back_creation_order():
    c = Construction()
    a, b = c.add_point(0.2, 0.2), c.add_point(-0.4, 0.1)
    c.add_line(a, b)
    assert c.undo().label == "a" and c.lines == []
    assert c.undo() is b and c.points == [a]
    assert c.undo() is a and c.points == []
    assert c.undo() is None


def test_undo_after_cascade_does_not_resurrect():
    c = Construction()
    a, b = c.add_point(0.2, 0.2), c.add_point(-0.4, 0.1)
    c.add_line(a, b)
    c.delete(a)              # takes the line with it
    assert c.undo() is b     # the line must not come back as the "last created"
    assert c.lines == [] and c.points == []


def test_every_pair_of_lines_meets_exactly_once():
    c = Construction()
    pts = [c.add_point(r * np.cos(t), r * np.sin(t))
           for r, t in [(0.5, 0.3), (0.7, 1.9), (0.3, 3.4), (0.8, 5.0)]]
    c.add_line(pts[0], pts[1])
    c.add_line(pts[1], pts[2])
    c.add_line(pts[2], pts[3])
    meets = c.intersections()
    assert len(meets) == 3  # C(3,2), all distinct here - no parallels in elliptic geometry
    for xy, first, second in meets:
        v = geo.lift(*xy)
        assert abs(np.dot(v, first.normal)) < 1e-9
        assert abs(np.dot(v, second.normal)) < 1e-9
        assert np.linalg.norm(xy) <= 1 + 1e-12


def test_concurrent_lines_report_one_meet():
    c = Construction()
    hub = c.add_point(0.15, -0.2)
    for angle in (0.4, 1.5, 2.6):
        c.add_line(hub, c.add_point(0.8 * np.cos(angle), 0.8 * np.sin(angle)))
    meets = c.intersections()
    assert len(meets) == 1
    assert np.linalg.norm(meets[0][0] - hub.xy) < 1e-6


def test_segment_length_is_the_elliptic_distance():
    c = Construction()
    a, b = c.add_point(0.6, 0.1), c.add_point(-0.5, 0.4)
    seg = c.add_line(a, b, SEGMENT)
    assert seg.is_segment and not c.add_line(a, b, LINE).is_segment
    assert abs(seg.length() - geo.distance(a.vector, b.vector)) < 1e-12
    assert seg.length() <= np.pi / 2 + 1e-12


def test_perpendicular_tracks_both_its_point_and_its_base():
    c = Construction()
    a, b = c.add_point(0.6, 0.2), c.add_point(-0.4, 0.5)
    base = c.add_line(a, b)
    p = c.add_point(0.1, -0.5)
    perp = c.add_perpendicular(p, base)
    assert perp.is_perpendicular and perp.is_partial and perp.q is None
    for move in [(p, (0.4, -0.2)), (a, (0.7, -0.1)), (b, (-0.2, 0.8))]:
        move[0].move_to(*move[1])
        assert abs(np.dot(perp.normal, base.normal)) < 1e-12, "still a right angle"
        assert abs(np.dot(perp.normal, p.vector)) < 1e-12, "still through the point"
        assert abs(np.dot(base.normal, perp.foot)) < 1e-12, "foot still on the base"


def test_perpendicular_length_is_the_point_to_line_distance():
    c = Construction()
    base = c.add_line(c.add_point(0.6, 0.2), c.add_point(-0.4, 0.5))
    p = c.add_point(0.1, -0.5)
    perp = c.add_perpendicular(p, base)
    assert abs(perp.length() - geo.distance_to_line(p.vector, base.normal)) < 1e-12
    on_the_line = c.add_perpendicular(base.p, base)
    assert on_the_line.length() < 1e-12  # erected at a point of the line


def test_perpendicular_from_a_pole_is_refused():
    c = Construction()
    base = c.add_line(c.add_point(0.6, 0.2), c.add_point(-0.4, 0.5))
    pole = c.add_point(*geo.polar_point(base.normal))
    assert c.add_perpendicular(pole, base) is None
    assert len(c.lines) == 1


def test_deleting_a_base_line_takes_its_perpendiculars():
    c = Construction()
    a, b = c.add_point(0.6, 0.2), c.add_point(-0.4, 0.5)
    base = c.add_line(a, b)
    p = c.add_point(0.1, -0.5)
    perp = c.add_perpendicular(p, base)
    second = c.add_perpendicular(p, perp)  # perpendicular to a perpendicular
    assert second.base is perp
    c.delete(base)
    assert c.lines == [], "the whole dependent chain goes"
    assert c.points == [a, b, p], "points survive"


def test_deleting_a_point_takes_perpendiculars_built_on_its_lines():
    c = Construction()
    a, b = c.add_point(0.6, 0.2), c.add_point(-0.4, 0.5)
    base = c.add_line(a, b)
    p = c.add_point(0.1, -0.5)
    c.add_perpendicular(p, base)
    c.delete(a)
    assert c.lines == [] and c.points == [b, p]


def test_dependents_lists_the_chain_without_deleting():
    c = Construction()
    a, b = c.add_point(0.6, 0.2), c.add_point(-0.4, 0.5)
    base = c.add_line(a, b)
    perp = c.add_perpendicular(c.add_point(0.1, -0.5), base)
    doomed = c.dependents(base)
    assert doomed == [base, perp] and len(c.lines) == 2


def test_undo_removes_a_perpendicular():
    c = Construction()
    base = c.add_line(c.add_point(0.6, 0.2), c.add_point(-0.4, 0.5))
    perp = c.add_perpendicular(c.add_point(0.1, -0.5), base)
    assert c.undo() is perp
    assert c.lines == [base]


def test_perpendicular_meets_its_base_at_the_foot():
    c = Construction()
    base = c.add_line(c.add_point(0.6, 0.2), c.add_point(-0.4, 0.5))
    perp = c.add_perpendicular(c.add_point(0.1, -0.5), base)
    meets = c.intersections()
    assert len(meets) == 1
    assert np.linalg.norm(meets[0][0] - perp.foot[:2]) < 1e-9


def test_a_meet_point_follows_its_lines():
    c = Construction()
    a, b, d, e = (c.add_point(0.6, 0.2), c.add_point(-0.4, 0.5),
                  c.add_point(0.1, -0.6), c.add_point(-0.7, -0.2))
    first, second = c.add_line(a, b), c.add_line(d, e)
    meet = c.add_meet(first, second)
    assert not meet.is_free and meet.kind == "meet"
    for move in [(a, (0.7, -0.1)), (e, (-0.2, -0.8))]:
        move[0].move_to(*move[1])
        assert abs(np.dot(meet.vector, first.normal)) < 1e-12
        assert abs(np.dot(meet.vector, second.normal)) < 1e-12
    assert np.linalg.norm(meet.xy) <= 1 + 1e-12


def test_a_meet_point_cannot_be_dragged():
    c = Construction()
    a, b, d = c.add_point(0.6, 0.2), c.add_point(-0.4, 0.5), c.add_point(0.1, -0.6)
    meet = c.add_meet(c.add_line(a, b), c.add_line(b, d))
    before = meet.xy.copy()
    meet.move_to(0.0, 0.0)
    assert np.allclose(meet.xy, before), "it belongs to its lines, not to you"
    assert np.linalg.norm(meet.xy - b.xy) < 1e-9, "and b is where they cross"


def test_a_line_can_be_built_on_a_meet():
    c = Construction()
    corners = [c.add_point(0.6, 0.2), c.add_point(-0.4, 0.5), c.add_point(0.1, -0.6)]
    first, second = c.add_line(corners[0], corners[1]), c.add_line(corners[1], corners[2])
    meet = c.add_meet(first, second)
    onward = c.add_line(meet, c.add_point(-0.8, -0.1))
    assert abs(np.dot(onward.normal, meet.vector)) < 1e-12
    c.delete(first)
    assert c.points == corners + [c.points[-1]], "the meet went with its line"
    assert onward not in c.lines, "and took the line built on it"


def test_a_meet_of_one_line_with_itself_is_refused():
    c = Construction()
    line = c.add_line(c.add_point(0.6, 0.2), c.add_point(-0.4, 0.5))
    assert c.add_meet(line, line) is None
    assert len(c.points) == 2


def test_an_undetermined_meet_has_nowhere_to_be():
    """Two lines that fall together stop crossing anywhere in particular."""
    c = Construction()
    a, b = c.add_point(0.6, 0.2), c.add_point(-0.4, 0.5)
    d = c.add_point(0.1, -0.6)
    meet = c.add_meet(c.add_line(a, b), c.add_line(a, d))
    assert meet.xy is not None
    d.move_to(*b.xy)  # now both lines are the same line
    assert meet.xy is None and meet.vector is None


def test_polar_and_pole_are_dual():
    c = Construction()
    a = c.add_point(0.35, -0.45)
    polar = c.add_polar(a)
    pole = c.add_pole(polar)
    assert polar.is_polar and polar.q is None
    assert np.allclose(pole.xy, a.xy, atol=1e-12), "the pole of the polar is the point"
    assert abs(geo.distance_to_line(a.vector, polar.normal) - np.pi / 2) < 1e-12
    a.move_to(0.1, 0.8)
    assert np.allclose(pole.xy, a.xy, atol=1e-12), "and it stays that way"


def test_every_perpendicular_to_a_line_runs_through_its_pole():
    c = Construction()
    base = c.add_line(c.add_point(0.6, 0.2), c.add_point(-0.4, 0.5))
    pole = c.add_pole(base)
    for x, y in [(0.1, -0.5), (-0.7, -0.1), (0.3, 0.7)]:
        perp = c.add_perpendicular(c.add_point(x, y), base)
        assert abs(np.dot(perp.normal, pole.vector)) < 1e-12


def test_deleting_a_point_takes_its_polar():
    c = Construction()
    a = c.add_point(0.35, -0.45)
    pole = c.add_pole(c.add_polar(a))
    c.delete(a)
    assert c.lines == [] and c.points == [], "the polar and its pole both go"
    assert pole not in c.points


def test_a_triangle_measures_its_angles():
    c = Construction()
    a, b, d = c.add_point(0.0, 0.0), c.add_point(0.4, 0.0), c.add_point(0.0, 0.6)
    t = c.add_triangle(a, b, d)
    assert t.label == "ABC" and len(c.lines) == 3
    assert all(side.is_segment for side in t.sides)
    assert abs(t.angles()[0] - np.pi / 2) < 1e-12
    assert abs(sum(t.angles()) - np.pi - t.area()) < 1e-12, "Girard"
    assert t.area() > 0.0, "more than pi, always"


def test_a_triangle_follows_its_vertices():
    c = Construction()
    a, b, d = c.add_point(0.1, 0.1), c.add_point(0.4, 0.0), c.add_point(0.0, 0.5)
    t = c.add_triangle(a, b, d)
    small = t.area()
    b.move_to(0.7, -0.15)
    d.move_to(-0.25, 0.75)
    assert t.area() > small, "a bigger triangle has a bigger excess"


def test_a_triangle_that_wraps_through_the_rim_has_no_area():
    c = Construction()
    a = c.add_point(0.95, 0.0)
    b = c.add_point(-0.3, 0.9)
    d = c.add_point(-0.35, -0.9)
    t = c.add_triangle(a, b, d)
    assert not t.bounds_a_disk() and t.area() is None
    assert t.angles() is not None, "the angles are still there to read"
    b.move_to(0.1, 0.4)  # pull a vertex in and it becomes an ordinary triangle
    assert t.bounds_a_disk() and t.area() > 0.0


def test_a_triangle_undoes_in_one_go():
    c = Construction()
    a, b, d = c.add_point(0.1, 0.1), c.add_point(0.4, 0.0), c.add_point(0.0, 0.5)
    t = c.add_triangle(a, b, d)
    assert c.undo() is t
    assert c.triangles == [] and c.lines == [], "the sides came with it"
    assert c.points == [a, b, d], "the vertices were already there"


def test_a_triangle_dies_with_any_of_its_sides():
    c = Construction()
    a, b, d = c.add_point(0.1, 0.1), c.add_point(0.4, 0.0), c.add_point(0.0, 0.5)
    t = c.add_triangle(a, b, d)
    other = c.add_line(a, b)  # an unrelated line on the same two points
    c.delete(t.sides[1])
    assert c.triangles == [] and c.lines == [t.sides[0], t.sides[2], other]
    assert c.points == [a, b, d]


def test_a_triangle_needs_three_distinct_points():
    c = Construction()
    a, b = c.add_point(0.2, 0.3), c.add_point(1.0, 0.0)
    twin = c.add_point(-1.0, 0.0)  # the same elliptic point as b
    assert c.add_triangle(a, b, b) is None
    assert c.add_triangle(a, b, twin) is None
    assert c.lines == [], "and it leaves no half-built sides behind"


def test_altitudes_of_a_triangle_meet_at_one_point():
    """The orthocentre, built out of a triangle, its sides and their meets."""
    c = Construction()
    a, b, d = c.add_point(0.1, 0.15), c.add_point(0.55, -0.2), c.add_point(-0.3, 0.5)
    t = c.add_triangle(a, b, d)
    altitudes = [c.add_perpendicular(vertex, side)
                 for vertex, side in zip((d, a, b), t.sides)]
    first = c.add_meet(altitudes[0], altitudes[1])
    second = c.add_meet(altitudes[1], altitudes[2])
    for move in [None, (0.8, 0.1), (-0.1, 0.75)]:
        if move:
            b.move_to(*move)
        # the three normals are coplanar, so the three lines share a point
        assert abs(np.linalg.det([alt.normal for alt in altitudes])) < 1e-12
        assert geo.distance(first.vector, second.vector) < 1e-6


def test_clear_resets_everything():
    c = Construction()
    a, b = c.add_point(0.2, 0.2), c.add_point(-0.4, 0.1)
    c.add_line(a, b)
    c.clear()
    assert (c.points, c.lines, c.undo()) == ([], [], None)
    assert c.add_point(0.0, 0.0).label == "A"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} checks passed")
