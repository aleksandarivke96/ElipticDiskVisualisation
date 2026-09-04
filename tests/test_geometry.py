"""Checks on the elliptic geometry primitives: run with `python3 -m tests.test_geometry`."""

from __future__ import annotations

import numpy as np

from elliptic import geometry as geo

rng = np.random.default_rng(20260801)


def random_disk_points(count):
    r = np.sqrt(rng.random(count))
    a = rng.random(count) * 2 * np.pi
    return np.column_stack([r * np.cos(a), r * np.sin(a)])


def test_lift_is_unit_and_upper():
    for x, y in random_disk_points(200):
        v = geo.lift(x, y)
        assert abs(np.linalg.norm(v) - 1) < 1e-12
        assert v[2] >= 0
        assert np.allclose(geo.project(v), [x, y])


def test_line_contains_both_points():
    for (ax, ay), (bx, by) in zip(random_disk_points(200), random_disk_points(200)):
        p, q = geo.lift(ax, ay), geo.lift(bx, by)
        n = geo.line_normal(p, q)
        assert abs(np.dot(n, p)) < 1e-12 and abs(np.dot(n, q)) < 1e-12
        # both points lie on the drawn curve
        line = geo.line_points(n, 4001)
        for pt in ([ax, ay], [bx, by]):
            assert np.linalg.norm(line - pt, axis=1).min() < 5e-3


def test_line_stays_in_disk_and_ends_on_rim():
    for (ax, ay), (bx, by) in zip(random_disk_points(100), random_disk_points(100)):
        n = geo.line_normal(geo.lift(ax, ay), geo.lift(bx, by))
        line = geo.line_points(n, 1001)
        radii = np.linalg.norm(line, axis=1)
        assert radii.max() < 1 + 1e-9
        assert abs(radii[0] - 1) < 1e-9 and abs(radii[-1] - 1) < 1e-9
        assert np.allclose(line[0], -line[-1], atol=1e-9)  # antipodal ends
        ends = geo.line_endpoints(n)
        assert np.linalg.norm(ends[0] - line[0]) < 1e-9 or \
               np.linalg.norm(ends[1] - line[0]) < 1e-9


def test_line_is_ellipse_with_semi_axes_1_and_nz():
    """x^2 + y^2 + (n.x x + n.y y)^2 / n_z^2 = 1 for every point of the line."""
    for (ax, ay), (bx, by) in zip(random_disk_points(50), random_disk_points(50)):
        n = geo.line_normal(geo.lift(ax, ay), geo.lift(bx, by))
        if abs(n[2]) < 1e-3:
            continue
        line = geo.line_points(n, 401)
        x, y = line[:, 0], line[:, 1]
        val = x**2 + y**2 + (n[0] * x + n[1] * y) ** 2 / n[2] ** 2
        assert np.allclose(val, 1.0, atol=1e-9)
        semi_minor = np.linalg.norm(line, axis=1).min()
        assert abs(semi_minor - abs(n[2])) < 1e-3


def test_diameter_when_normal_is_horizontal():
    p, q = geo.lift(0.3, 0.0), geo.lift(-0.6, 0.0)  # both on the x-axis
    n = geo.line_normal(p, q)
    assert abs(n[2]) < 1e-12
    line = geo.line_points(n, 201)
    assert np.allclose(line[:, 1], 0.0, atol=1e-12)
    assert abs(line[:, 0].min() + 1) < 1e-12 and abs(line[:, 0].max() - 1) < 1e-12


def test_boundary_points_give_the_equator():
    p, q = geo.lift(1.0, 0.0), geo.lift(0.0, 1.0)
    n = geo.line_normal(p, q)
    assert geo.is_boundary_line(n)
    line = geo.line_points(n, 361)
    assert np.allclose(np.linalg.norm(line, axis=1), 1.0)


def test_distance_bounds_and_symmetry():
    for (ax, ay), (bx, by) in zip(random_disk_points(300), random_disk_points(300)):
        p, q = geo.lift(ax, ay), geo.lift(bx, by)
        d = geo.distance(p, q)
        assert -1e-12 <= d <= np.pi / 2 + 1e-12
        assert abs(d - geo.distance(q, p)) < 1e-12
        assert geo.distance(p, p) < 1e-7
        assert abs(geo.distance(p, -p)) < 1e-7  # antipode is the same point


def test_pole_is_pi_over_2_from_the_whole_line():
    for (ax, ay), (bx, by) in zip(random_disk_points(50), random_disk_points(50)):
        n = geo.line_normal(geo.lift(ax, ay), geo.lift(bx, by))
        pole = geo.lift(*geo.polar_point(n))
        for x, y in geo.line_points(n, 101):
            assert abs(geo.distance(pole, geo.lift(x, y)) - np.pi / 2) < 1e-6


def test_segment_length_matches_distance():
    for (ax, ay), (bx, by) in zip(random_disk_points(100), random_disk_points(100)):
        p, q = geo.lift(ax, ay), geo.lift(bx, by)
        paths = geo.segment_paths(p, q, 4001)
        assert 1 <= len(paths) <= 2
        # measure on the hemisphere: sum of angles between consecutive samples
        total = 0.0
        for path in paths:
            v = np.array([geo.lift(x, y) for x, y in path])
            dots = np.clip(np.abs(np.sum(v[:-1] * v[1:], axis=1)), -1, 1)
            total += float(np.arccos(dots).sum())
        assert abs(total - geo.distance(p, q)) < 1e-3
        assert np.linalg.norm(paths[0][0] - [ax, ay]) < 1e-9  # starts at A


def test_segment_splits_only_when_it_leaves_the_disk():
    near = geo.segment_paths(geo.lift(0.1, 0.0), geo.lift(0.2, 0.1))
    assert len(near) == 1
    far = geo.segment_paths(geo.lift(0.97, 0.0), geo.lift(-0.97, 0.02))
    assert len(far) == 2 and geo.distance(geo.lift(0.97, 0.0), geo.lift(-0.97, 0.02)) < np.pi / 2


def test_same_point_has_no_unique_line():
    p = geo.lift(0.4, -0.2)
    assert geo.line_normal(p, p) is None
    assert geo.line_normal(geo.lift(1.0, 0.0), geo.lift(-1.0, 0.0)) is None  # identified


def test_perpendicular_is_perpendicular_and_passes_through_the_pole():
    for (ax, ay), (bx, by), (px, py) in zip(random_disk_points(100),
                                            random_disk_points(100),
                                            random_disk_points(100)):
        n = geo.line_normal(geo.lift(ax, ay), geo.lift(bx, by))
        p = geo.lift(px, py)
        m = geo.perpendicular_normal(p, n)
        assert abs(np.dot(m, p)) < 1e-12, "the perpendicular must pass through p"
        assert abs(np.dot(m, n)) < 1e-12, "normals orthogonal <=> lines at a right angle"
        pole = geo.lift(*geo.polar_point(n))
        assert abs(np.dot(m, pole)) < 1e-12, "every perpendicular meets the pole"


def test_foot_lies_on_the_line_and_realises_the_distance():
    for (ax, ay), (bx, by), (px, py) in zip(random_disk_points(100),
                                            random_disk_points(100),
                                            random_disk_points(100)):
        n = geo.line_normal(geo.lift(ax, ay), geo.lift(bx, by))
        p = geo.lift(px, py)
        foot = geo.foot_of_perpendicular(p, n)
        assert abs(np.dot(foot, n)) < 1e-12 and foot[2] >= 0
        d = geo.distance_to_line(p, n)
        assert abs(geo.distance(p, foot) - d) < 1e-9
        # nothing on the line is nearer than the foot
        others = [geo.distance(p, geo.lift(x, y)) for x, y in geo.line_points(n, 601)]
        assert d <= min(others) + 1e-9


def test_a_point_on_a_line_is_at_distance_zero_from_it():
    p, q = geo.lift(0.3, 0.4), geo.lift(-0.5, 0.1)
    n = geo.line_normal(p, q)
    assert geo.distance_to_line(p, n) < 1e-12
    assert geo.distance(p, geo.foot_of_perpendicular(p, n)) < 1e-9  # foot is p itself


def test_the_pole_is_the_far_point_with_no_unique_perpendicular():
    n = geo.line_normal(geo.lift(0.3, 0.4), geo.lift(-0.5, 0.1))
    pole = geo.lift(*geo.polar_point(n))
    assert abs(geo.distance_to_line(pole, n) - np.pi / 2) < 1e-12
    assert geo.perpendicular_normal(pole, n) is None


def test_right_angle_marker_sits_at_the_foot():
    n = geo.line_normal(geo.lift(0.3, 0.4), geo.lift(-0.5, 0.1))
    p = geo.lift(-0.1, -0.35)
    foot = geo.foot_of_perpendicular(p, n)
    marker = geo.right_angle_marker(foot, n, geo.perpendicular_normal(p, n), size=0.09)
    assert marker.shape == (3, 3), "three points of the sphere"
    assert np.linalg.norm(marker - foot, axis=1).max() < 0.2
    assert np.allclose(np.linalg.norm(marker, axis=1), 1.0), "unit vectors"
    assert marker[:, 2].min() >= 0.0
    # At a foot on the rim the square straddles the equator whenever the
    # perpendicular heads downwards; that half would reappear on the far side of
    # the disk, so the marker is dropped rather than drawn torn.
    rim_foot = np.array([1.0, 0.0, 0.0])
    equator = np.array([0.0, 0.0, 1.0])
    markers = [geo.right_angle_marker(rim_foot, equator, np.array([0.0, s, 0.0]),
                                      size=0.3) for s in (1.0, -1.0)]
    assert sum(m is None for m in markers) == 1


def test_both_projections_cover_the_disk_and_undo_each_other():
    for projection in (geo.ORTHOGONAL, geo.STEREOGRAPHIC):
        for (x, y) in random_disk_points(200):
            v = projection.lift(x, y)
            assert abs(np.linalg.norm(v) - 1) < 1e-12 and v[2] >= 0.0
            assert np.allclose(projection.project(v), [x, y], atol=1e-12)
        for _ in range(200):
            v = geo.upper(rng.normal(size=3))
            v /= np.linalg.norm(v)
            xy = projection.project(v)
            assert np.linalg.norm(xy) <= 1.0 + 1e-12, "the hemisphere fills the disk"
            assert np.allclose(projection.lift(*xy), v, atol=1e-9)
        for angle in np.linspace(0.0, 2 * np.pi, 37):  # both fix the rim
            rim = np.array([np.cos(angle), np.sin(angle), 0.0])
            assert np.allclose(projection.project(rim), rim[:2], atol=1e-12)


def test_stereographic_turns_lines_into_circles():
    """(x, y)/(1 + z) sends the plane n.x = 0 to the circle about (n1,n2)/n3."""
    for (ax, ay), (bx, by) in zip(random_disk_points(200), random_disk_points(200)):
        n = geo.line_normal(geo.lift(ax, ay), geo.lift(bx, by))
        shape = geo.STEREOGRAPHIC.conic(n)
        if shape is None:
            assert abs(n[2]) < geo.EPS, "only a diameter has no circle"
            continue
        centre, major, minor = shape
        radius = np.linalg.norm(major)
        assert abs(radius - np.linalg.norm(minor)) < 1e-12, "a circle, not an ellipse"
        assert np.allclose(centre, np.array([n[0], n[1]]) / n[2], atol=1e-12)
        assert abs(radius - 1.0 / abs(n[2])) < 1e-12
        for v in geo.line_vectors(n, 101):
            drawn = geo.STEREOGRAPHIC.project(v)
            assert abs(np.linalg.norm(drawn - centre) - radius) < 1e-9


def test_stereographic_keeps_the_angles():
    """It is conformal: the angle at a vertex is the angle you see on the page."""
    for (ax, ay), (bx, by), (cx, cy) in zip(*[random_disk_points(120) for _ in range(3)]):
        a, b, c = geo.lift(ax, ay), geo.lift(bx, by), geo.lift(cx, cy)
        true_angle = geo.arc_angle(a, b, c)
        if true_angle is None or min(geo.distance(a, b), geo.distance(a, c)) < 0.2:
            continue
        # walk a whisker along each side and measure the angle in the picture
        tiny = 1e-4
        centre = geo.STEREOGRAPHIC.project(a)
        legs = []
        for far in (b, c):
            step = np.cos(tiny) * a + np.sin(tiny) * geo.tangent(a, far)
            legs.append(geo.STEREOGRAPHIC.project(step) - centre)
        drawn = np.arccos(np.clip(np.dot(*[leg / np.linalg.norm(leg) for leg in legs]),
                                  -1.0, 1.0))
        assert abs(drawn - true_angle) < 1e-3, "conformal: angles come out true"


def test_a_line_is_half_an_ellipse_about_the_centre():
    """Semi-axes 1 and |n_z| - which is what lets it be drawn as one arc."""
    for (ax, ay), (bx, by) in zip(random_disk_points(200), random_disk_points(200)):
        n = geo.line_normal(geo.lift(ax, ay), geo.lift(bx, by))
        axes = geo.line_ellipse(n)
        if axes is None:  # a diameter or the rim circle, no ellipse to draw
            assert abs(n[2]) < geo.EPS or geo.is_boundary_line(n)
            continue
        rim, minor = axes
        assert abs(np.linalg.norm(rim) - 1.0) < 1e-12
        assert abs(np.linalg.norm(minor) - abs(n[2])) < 1e-12
        assert abs(np.dot(rim, minor)) < 1e-12, "the axes are perpendicular"
        for xy in (rim, -rim, minor):
            # 1e-6, not 1e-12: lifting a rim point takes the square root of
            # almost nothing, so the third coordinate is only half as precise
            assert abs(np.dot(geo.lift(*xy), n)) < 1e-6, "every axis end is on the line"
        # but -minor is not: that is the far end of the whole ellipse, which is
        # where the *lower* half of the great circle projects, and lifting it
        # back up lands on a different point altogether.  Only half the ellipse
        # is the line - which is exactly why the export sweeps 180 and no more.
        if abs(n[2]) > 1e-3:
            assert abs(np.dot(geo.lift(*-minor), n)) > 1e-6
        # the drawn half runs counterclockwise from `rim` through `minor`
        quarter = np.array([[0.0, -1.0], [1.0, 0.0]]) @ rim
        assert np.allclose(quarter * abs(n[2]), minor, atol=1e-12)
        # and `minor` is the point of the line nearest the centre
        line = geo.line_points(n, 2001)
        assert abs(np.linalg.norm(line, axis=1).min() - abs(n[2])) < 1e-6
        assert np.linalg.norm(line - minor, axis=1).min() < 5e-3


def test_a_line_arc_is_the_line():
    for (ax, ay), (bx, by) in zip(random_disk_points(100), random_disk_points(100)):
        n = geo.line_normal(geo.lift(ax, ay), geo.lift(bx, by))
        e1, e2, t0, t1 = geo.line_arc(n)
        assert np.allclose(geo.arc_points(e1, e2, t0, t1, 257), geo.line_points(n, 257))
        for t in np.linspace(t0, t1, 51):
            xy = geo.arc_end(e1, e2, t)
            assert np.linalg.norm(xy) <= 1.0 + 1e-12, "the arc stays in the disk"
            assert abs(np.dot(geo.lift(*xy), n)) < 1e-6  # ill-conditioned at the rim


def test_segment_arcs_cut_exactly_where_the_segment_leaves_the_disk():
    for (ax, ay), (bx, by) in zip(random_disk_points(300), random_disk_points(300)):
        p, q = geo.lift(ax, ay), geo.lift(bx, by)
        arcs = geo.segment_arcs(p, q)
        assert 1 <= len(arcs) <= 2
        ends = [geo.arc_end(e1, e2, t) for e1, e2, t0, t1 in arcs for t in (t0, t1)]
        assert geo.distance(geo.lift(*ends[0]), p) < 1e-6, "starts where it should"
        assert geo.distance(geo.lift(*ends[-1]), q) < 1e-6, "and finishes there"
        if len(arcs) == 2:
            # the cut is on the rim, and the two pieces meet at antipodal points
            assert abs(np.linalg.norm(ends[1]) - 1.0) < 1e-9
            assert np.allclose(ends[1], -ends[2], atol=1e-9)
        total = sum(abs(t1 - t0) for _, _, t0, t1 in arcs)
        assert abs(total - geo.distance(p, q)) < 1e-9, "and no length is lost at the cut"


def test_polar_and_pole_are_inverse():
    for (x, y) in random_disk_points(200):
        p = geo.lift(x, y)
        n = geo.polar_normal(p)
        assert abs(np.linalg.norm(n) - 1) < 1e-12
        assert np.allclose(geo.pole_vector(n), p, atol=1e-12)  # an involution
        # every point of the polar is a quarter turn away from the point
        e1, e2 = geo.plane_basis(n)
        for t in np.linspace(0.0, 2 * np.pi, 37):
            q = np.cos(t) * e1 + np.sin(t) * e2
            assert abs(geo.distance(p, q) - np.pi / 2) < 1e-12


def test_the_polar_of_a_pole_is_the_line_again():
    n = geo.line_normal(geo.lift(0.3, 0.4), geo.lift(-0.5, 0.1))
    back = geo.polar_normal(geo.pole_vector(n))
    assert np.allclose(back, n, atol=1e-12) or np.allclose(back, -n, atol=1e-12)


def test_two_lines_always_meet_exactly_once():
    for (ax, ay), (bx, by), (cx, cy), (dx, dy) in zip(*[random_disk_points(200)
                                                        for _ in range(4)]):
        n1 = geo.line_normal(geo.lift(ax, ay), geo.lift(bx, by))
        n2 = geo.line_normal(geo.lift(cx, cy), geo.lift(dx, dy))
        meet = geo.meet_vector(n1, n2)
        assert meet is not None, "no parallels in elliptic geometry"
        assert meet[2] >= 0 and abs(np.linalg.norm(meet) - 1) < 1e-12
        assert abs(np.dot(meet, n1)) < 1e-9 and abs(np.dot(meet, n2)) < 1e-9
    assert geo.meet_vector(n1, n1) is None  # a line does not cross itself


def test_a_line_meets_its_own_perpendicular_at_the_foot():
    n = geo.line_normal(geo.lift(0.3, 0.4), geo.lift(-0.5, 0.1))
    p = geo.lift(-0.1, -0.35)
    m = geo.perpendicular_normal(p, n)
    assert geo.distance(geo.meet_vector(n, m), geo.foot_of_perpendicular(p, n)) < 1e-12


def test_tangent_points_along_the_shortest_arc():
    a = geo.lift(0.2, -0.1)
    for (x, y) in random_disk_points(200):
        b = geo.lift(x, y)
        t = geo.tangent(a, b)
        if t is None:
            continue
        assert abs(np.dot(t, a)) < 1e-12 and abs(np.linalg.norm(t) - 1) < 1e-12
        # stepping along the tangent gets closer to b, and by the full distance
        # of the arc it has arrived
        d = geo.distance(a, b)
        arrived = np.cos(d) * a + np.sin(d) * t
        assert np.allclose(arrived, geo.nearest_representative(a, b), atol=1e-9)
    assert geo.tangent(a, a) is None
    assert geo.tangent(a, -a) is None  # the same elliptic point


def test_angles_of_a_right_angled_corner():
    a, b, c = geo.lift(0.0, 0.0), geo.lift(0.4, 0.0), geo.lift(0.0, 0.6)
    angles = geo.triangle_angles(a, b, c)
    assert abs(angles[0] - np.pi / 2) < 1e-12, "a right angle at the centre"
    assert abs(sum(angles) - np.pi - geo.triangle_area(a, b, c)) < 1e-12


def test_girard_on_the_octant():
    """Three mutually orthogonal points: three right angles, an eighth of a sphere."""
    a, b, c = np.eye(3)
    assert np.allclose(geo.triangle_angles(a, b, c), np.pi / 2)
    assert abs(geo.triangle_area(a, b, c) - np.pi / 2) < 1e-12


def test_area_shrinks_to_the_euclidean_one_near_the_centre():
    """A tiny triangle at the centre has almost no excess, and area s^2 / 2."""
    for s in (0.02, 0.01, 0.005):
        a, b, c = geo.lift(0, 0), geo.lift(s, 0), geo.lift(0, s)
        area = geo.triangle_area(a, b, c)
        assert abs(area - s * s / 2) < 0.02 * s * s


def test_triangles_that_close_up_through_the_rim_have_no_area():
    """(a.b)(b.c)(c.a) < 0: the three shortest sides lift to a path from a to -a,
    so they bound no disk and Girard's formula does not apply."""
    a = geo.lift(0.95, 0.0)
    b = geo.lift(-0.3, 0.9)
    c = geo.lift(-0.35, -0.9)
    assert not geo.bounds_a_disk(a, b, c)
    assert geo.triangle_area(a, b, c) is None
    assert geo.triangle_angles(a, b, c) is not None, "the angles are still there"
    assert not geo.bounds_a_disk(b, c, a), "and it does not depend on the order"

    # walking the three sides on the sphere lands on -a, not a
    walked = a
    for far in (b, c, a):
        walked = geo.nearest_representative(walked, far)
    assert np.allclose(walked, -a, atol=1e-12)


def test_ordinary_triangles_do_bound_a_disk():
    for (ax, ay), (bx, by), (cx, cy) in zip(*[random_disk_points(300) for _ in range(3)]):
        a, b, c = geo.lift(ax, ay), geo.lift(bx, by), geo.lift(cx, cy)
        area = geo.triangle_area(a, b, c)
        if area is None:
            continue
        assert 0.0 <= area <= np.pi + 1e-9, "an excess, but never more than the plane"
        centre = geo.triangle_centre(a, b, c)
        assert np.linalg.norm(centre) > 0.99 and centre[2] >= 0


def test_angle_arc_hugs_its_vertex_and_is_dropped_at_the_rim():
    a, b, c = geo.lift(0.1, 0.2), geo.lift(0.7, 0.1), geo.lift(-0.2, 0.6)
    arc = geo.angle_arc(a, b, c, radius=0.13)
    assert arc is not None and arc.shape[1] == 3, "points of the sphere"
    for point in arc:  # every sample really is 0.13 from the vertex
        assert abs(geo.distance(a, point) - 0.13) < 1e-12
        assert point[2] >= 0.0, "and on the half the disk shows"
    rim = geo.lift(1.0, 0.0)
    assert geo.angle_arc(rim, b, c, radius=0.13) is None, "would tear at the rim"
    assert geo.angle_arc(a, b, b) is None, "no angle between an arc and itself"


def test_clamp_to_disk():
    assert np.allclose(geo.clamp_to_disk(3.0, 4.0), (0.6, 0.8))
    assert np.allclose(geo.clamp_to_disk(0.3, 0.4), (0.3, 0.4))


def test_a_point_lands_in_the_plane_of_the_disk():
    """Both projections drop into z = 0, which is what lets one 3-D view show both."""
    for x, y in [(0.0, 0.0), (0.4, -0.55), (-0.9, 0.2), (0.6, 0.8)]:
        for projection in (geo.ORTHOGONAL, geo.STEREOGRAPHIC):
            v = projection.lift(x, y)
            landing = projection.landing(v)
            assert landing[2] == 0.0
            assert np.allclose(landing[:2], (x, y), atol=1e-9)
            assert np.linalg.norm(landing) <= 1.0 + 1e-9


def test_the_sight_line_of_each_projection():
    """The 3-D view draws these, so they have to be the real lines of sight."""
    for x, y in [(0.15, 0.25), (-0.5, 0.4), (0.8, -0.1)]:
        v = geo.ORTHOGONAL.lift(x, y)
        ray = geo.ORTHOGONAL.ray(v)
        assert np.allclose(ray[0], v), "it starts at the point itself"
        assert np.allclose(ray[1], [x, y, 0.0]), "and drops straight down"
        assert abs(ray[0][0] - ray[1][0]) < 1e-12 and abs(ray[0][1] - ray[1][1]) < 1e-12

        w = geo.STEREOGRAPHIC.lift(x, y)
        ray = geo.STEREOGRAPHIC.ray(w)
        south = np.array([0.0, 0.0, -1.0])
        assert np.allclose(ray[0], south), "it starts at the south pole"
        assert np.allclose(ray[1], [x, y, 0.0])
        along = ray[1] - south                       # and the point is on the way
        across = np.cross(along, w - south)
        assert np.linalg.norm(across) < 1e-9, "the point of the sphere is on the ray"


# ---------------------------------------------------------------- circles


def test_a_circle_is_everything_at_its_radius():
    for (ax, ay), radius in zip(random_disk_points(100),
                                rng.uniform(0.05, geo.HALF_PI, 100)):
        a = geo.lift(ax, ay)
        for path in geo.circle_vector_paths(a, radius):
            assert np.all(np.abs(np.linalg.norm(path, axis=1) - 1) < 1e-9)
            assert np.all(path[:, 2] > -1e-6), "every drawn point is upper"
            d = np.arccos(np.clip(np.abs(path @ a), -1.0, 1.0))
            assert np.allclose(d, radius, atol=1e-9), "all of it at distance r"


def test_a_circle_folds_exactly_when_it_dips_below_the_equator():
    """One closed piece while centre-depth + radius stays under pi/2; else two."""
    for (ax, ay), radius in zip(random_disk_points(200),
                                rng.uniform(0.05, geo.HALF_PI, 200)):
        a = geo.lift(ax, ay)
        depth = np.arccos(np.clip(a[2], -1.0, 1.0))  # how far a is from the pole
        if abs(depth + radius - geo.HALF_PI) < 1e-3:
            continue  # tangent to the rim: either answer is honest
        pieces = geo.circle_vector_paths(a, radius)
        if depth + radius < geo.HALF_PI:
            assert len(pieces) == 1
            assert np.allclose(pieces[0][0], pieces[0][-1], atol=1e-9), "closed"
        else:
            assert len(pieces) == 2, "through the rim and back on the far side"
            for piece in pieces:
                for end in (piece[0], piece[-1]):
                    assert abs(np.hypot(end[0], end[1]) - 1) < 1e-9, "ends on the rim"
            # the fold re-enters at the antipodal boundary points
            assert np.allclose(pieces[0][-1][:2], -pieces[1][0][:2], atol=1e-9)
            assert np.allclose(pieces[0][0][:2], -pieces[1][-1][:2], atol=1e-9)


def test_the_circle_cut_is_analytic_not_sampled():
    a = geo.lift(0.82, 0.1)
    coarse = geo.circle_vector_paths(a, 0.6, samples=24)
    fine = geo.circle_vector_paths(a, 0.6, samples=2048)
    assert len(coarse) == len(fine) == 2
    for lo, hi in zip(coarse, fine):
        assert np.allclose(lo[0], hi[0], atol=1e-12)
        assert np.allclose(lo[-1], hi[-1], atol=1e-12)


def test_a_circle_of_radius_half_pi_is_the_polar_of_its_centre():
    for ax, ay in random_disk_points(50):
        a = geo.lift(ax, ay)
        paths = geo.circle_vector_paths(a, geo.HALF_PI)
        assert len(paths) == 1, "the polar line must not be drawn twice"
        for path in paths:
            assert np.all(np.abs(path @ a) < 1e-9), "it lies on the polar line"


def test_the_projected_circle_lies_on_its_point_conic():
    """The exporter's whole premise: each arc's image is an arc of the conic
    `point_conic` names, under either projection - the folded arc included."""
    for (ax, ay), radius in zip(random_disk_points(60),
                                rng.uniform(0.1, geo.HALF_PI - 0.05, 60)):
        a = geo.lift(ax, ay)
        for projection in (geo.ORTHOGONAL, geo.STEREOGRAPHIC):
            for axis, e1, e2, t0, t1 in geo.circle_arcs(a, radius):
                shape = projection.point_conic(axis, radius)
                if shape is None or np.linalg.norm(shape[2]) < 1e-4:
                    continue  # edge-on or straight: drawn as samples instead
                centre, major, minor = shape
                drawn = projection.project(
                    geo.circle_arc_vectors(axis, e1, e2, radius, t0, t1, 64))
                s1 = (drawn - centre) @ major / float(major @ major)
                s2 = (drawn - centre) @ minor / float(minor @ minor)
                assert np.allclose(s1 * s1 + s2 * s2, 1.0, atol=1e-7), \
                    f"{projection.name} arc strays off its conic"


def test_circle_point_and_arc_vectors_agree():
    a = geo.lift(0.3, -0.2)
    (axis, e1, e2, t0, t1), = geo.circle_arcs(a, 0.4)
    path = geo.circle_arc_vectors(axis, e1, e2, 0.4, t0, t1, 7)
    for i, t in enumerate(np.linspace(t0, t1, 7)):
        assert np.allclose(path[i], geo.circle_point(axis, e1, e2, 0.4, t))


def test_bisector_normals_halve_the_angle_and_are_perpendicular():
    rng = np.random.default_rng(11)
    for _ in range(200):
        m = rng.normal(size=3); m /= np.linalg.norm(m)
        n = rng.normal(size=3); n /= np.linalg.norm(n)
        if abs(float(np.dot(m, n))) > 1.0 - 1e-6:
            continue
        both = [geo.bisector_normal(m, n, sign) for sign in (1.0, -1.0)]
        meet = geo.meet_vector(m, n)
        for b in both:
            assert abs(np.linalg.norm(b) - 1.0) < 1e-12
            assert abs(float(np.dot(b, meet))) < 1e-9, "through the meet"
            assert abs(abs(float(np.dot(b, m)))
                       - abs(float(np.dot(b, n)))) < 1e-9, "equal angles"
        assert abs(float(np.dot(both[0], both[1]))) < 1e-9, "perpendicular pair"


def test_bisecting_a_line_with_itself_degenerates():
    m = np.array([0.3, -0.4, 0.866])
    m /= np.linalg.norm(m)
    assert geo.bisector_normal(m, m, -1.0) is None
    same = geo.bisector_normal(m, m, 1.0)
    assert abs(abs(float(np.dot(same, m))) - 1.0) < 1e-12, "the line itself"


def test_the_midpoint_is_halfway_along_the_segment():
    rng = np.random.default_rng(13)
    for _ in range(200):
        a = rng.normal(size=3); a /= np.linalg.norm(a); a = geo.upper(a)
        b = rng.normal(size=3); b /= np.linalg.norm(b); b = geo.upper(b)
        if abs(float(np.dot(a, b))) > 1.0 - 1e-6:
            continue
        m = geo.midpoint_vector(a, b)
        assert abs(np.linalg.norm(m) - 1.0) < 1e-12
        assert m[2] > -geo.EPS, "drawn representative"
        assert abs(float(np.dot(m, np.cross(a, b)))) < 1e-9, "on their line"
        assert abs(geo.distance(m, a) - geo.distance(m, b)) < 1e-9
        assert abs(geo.distance(m, a) - geo.distance(a, b) / 2.0) < 1e-9


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} checks passed")
