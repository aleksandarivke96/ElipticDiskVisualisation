"""Checks on the GCLC export: run with `python3 -m tests.test_gclc`.

Most of this parses the file back and checks it against the construction it came
from.  The last checks go further and run `gclc` itself, when there is one to
run: set GCLC to the binary, or drop it somewhere obvious like ~/Desktop/GCLC.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile

import numpy as np

from elliptic import gclc
from elliptic import geometry as geo
from elliptic.model import SEGMENT, Construction

# every command the exporter is allowed to write
COMMANDS = {"dim", "ang_picture", "ang_origin", "ang_unit", "ang_point",
            "circle", "drawcircle", "drawdashcircle", "drawarc_p", "drawellipse",
            "drawellipsearc2", "drawdashellipsearc2", "drawsegment", "drawdashsegment",
            "drawpoint", "color", "linethickness",
            "cmark_lt", "cmark_rt", "cmark_lb", "cmark_rb"}

CANDIDATES = ["gclc", os.path.expanduser("~/Desktop/GCLC/gclc"),
              os.path.expanduser("~/GCLC/gclc")]


def find_gclc() -> str | None:
    """The gclc binary, if this machine has one."""
    named = os.environ.get("GCLC")
    for candidate in ([named] if named else []) + CANDIDATES:
        found = shutil.which(candidate) or (candidate if os.path.isfile(candidate) else None)
        if found and os.access(found, os.X_OK):
            return found
    return None


def sample_construction() -> Construction:
    """A triangle, its altitudes, the orthocentre, a polar, and two circles -
    one snug inside the disk, one folding out through the rim."""
    c = Construction()
    a, b, d = c.add_point(0.0, 0.35), c.add_point(0.55, -0.3), c.add_point(-0.5, -0.25)
    triangle = c.add_triangle(a, b, d)
    altitudes = [c.add_perpendicular(vertex, side)
                 for vertex, side in zip((d, a, b), triangle.sides)]
    c.add_meet(altitudes[0], altitudes[1])
    c.add_polar(c.add_point(0.8, 0.45))
    c.add_circle(a, b)
    c.add_circle(c.add_point(-0.75, 0.45), d)
    return c


def statements(text: str):
    """The file with its comments and blank lines stripped, split into words."""
    for raw in text.splitlines():
        code = raw.split("%")[0].strip()
        if code:
            yield code.split()


def is_number(word: str) -> bool:
    try:
        float(word)
    except ValueError:
        return False
    return True


def test_only_known_gclc_commands_are_written():
    text = gclc.to_gclc(sample_construction())
    used = {words[0] for words in statements(text)}
    assert used <= COMMANDS, f"unexpected commands: {sorted(used - COMMANDS)}"
    assert {"dim", "ang_point", "drawellipsearc2"} <= used


def test_the_file_opens_with_its_dimensions_and_coordinate_system():
    text = gclc.to_gclc(sample_construction(), size=120.0)
    assert text.startswith("%"), "a comment header first"
    head = [words for words in statements(text)][:4]
    assert head[0] == ["dim", "120", "120"], "dim takes its arguments plainly"
    assert head[1] == ["ang_picture", "0", "0", "120", "120"]
    assert head[2] == ["ang_origin", "60", "60"]
    assert head[3] == ["ang_unit", "53"], "the disk's radius in mm is the unit"


def test_nothing_is_drawn_before_it_is_defined():
    """GCLC reads top to bottom, so every name has to exist by the time it is used."""
    defined: set[str] = set()
    for words in statements(gclc.to_gclc(sample_construction())):
        head, rest = words[0], words[1:]
        if head == "ang_point":
            assert rest[0] not in defined, f"{rest[0]} defined twice"
            defined.add(rest[0])
        elif head.startswith("draw") or head.startswith("cmark"):
            for name in rest:
                assert is_number(name) or name in defined, f"{words} draws the undefined"


def test_the_coordinates_are_the_constructions_own():
    """ang_origin and ang_unit put the disk on the page, so the numbers stay ours."""
    c = sample_construction()
    text = gclc.to_gclc(c)
    placed = {words[1]: np.array([float(words[2]), float(words[3])])
              for words in statements(text) if words[0] == "ang_point"}
    labelled = {words[1] for words in statements(text) if words[0].startswith("cmark")}
    for point in c.points:
        assert point.label in placed, "every point travels under its own name"
        assert np.allclose(placed[point.label], point.xy, atol=1e-5)
        assert point.label in labelled, "and carries its label"
    for xy in placed.values():  # 1e-4 of slack: the file keeps five decimals
        assert np.linalg.norm(xy) <= 1.0 + 1e-4, "and nothing lands outside the disk"


def test_a_line_is_one_arc_not_a_chain_of_segments():
    c = Construction()
    a, b = c.add_point(0.5, 0.35), c.add_point(-0.45, 0.15)
    c.add_line(a, b)
    words = list(statements(gclc.to_gclc(c)))
    arcs = [w for w in words if w[0] == "drawellipsearc2"]
    assert len(arcs) == 1, "half an ellipse, in one command"
    assert abs(float(arcs[0][-1]) - 180.0) < 1e-6, "and that half is a half turn"
    assert not [w for w in words if w[0] == "drawsegment"], "and nothing straight"


def test_a_triangle_draws_no_straight_pieces_at_all():
    """Sides and angle marks alike: every curve in the file is one arc command."""
    c = Construction()
    a, b, d = c.add_point(0.0, 0.35), c.add_point(0.55, -0.3), c.add_point(-0.5, -0.25)
    c.add_triangle(a, b, d)
    words = list(statements(gclc.to_gclc(c)))
    assert not [w for w in words if w[0] in ("drawsegment", "drawdashsegment")]
    # three sides, each a faint whole conic plus the piece, and three angle marks
    assert len([w for w in words if w[0] == "drawellipsearc2"]) == 9


def test_an_angle_mark_is_an_arc_of_its_own_ellipse():
    """The mark is a circle about the vertex, and circles project to ellipses."""
    for xy in [(0.0, 0.0), (0.31, -0.42), (0.7, 0.1)]:
        a = geo.lift(*xy)
        centre, major, minor = geo.small_circle_ellipse(a, geo.ANGLE_RADIUS)
        assert np.linalg.norm(major) >= np.linalg.norm(minor), "major axis first"
        assert abs(np.dot(major, minor)) < 1e-12, "and the axes are perpendicular"
        # the whole circle about a, projected, satisfies the ellipse's equation
        for direction in np.linspace(0.0, 2 * np.pi, 60):
            e1, e2 = geo.plane_basis(a)
            point = (np.cos(geo.ANGLE_RADIUS) * a
                     + np.sin(geo.ANGLE_RADIUS) * (np.cos(direction) * e1
                                                   + np.sin(direction) * e2))[:2]
            offset = point - centre
            u = np.dot(offset, major) / np.dot(major, major)
            v = np.dot(offset, minor) / np.dot(minor, minor)
            assert abs(u * u + v * v - 1.0) < 1e-9, "on the ellipse"


def test_the_ellipse_of_a_line_has_the_right_axes():
    for (ax, ay), (bx, by) in [((0.5, 0.35), (-0.45, 0.15)), ((0.2, -0.7), (0.6, 0.1))]:
        c = Construction()
        line = c.add_line(c.add_point(ax, ay), c.add_point(bx, by))
        rim, minor = geo.line_ellipse(line.normal)
        assert abs(np.linalg.norm(rim) - 1.0) < 1e-12, "the major axis reaches the rim"
        assert abs(np.linalg.norm(minor) - abs(line.normal[2])) < 1e-12, "semi-minor is |n_z|"
        assert abs(np.dot(rim, minor)) < 1e-12, "and the axes are perpendicular"
        for xy in (rim, minor, -rim):  # lifting a rim point is only half-precise
            assert abs(np.dot(geo.lift(*xy), line.normal)) < 1e-6, "all on the line"
        # a quarter turn counterclockwise from the rim end lands on the minor end,
        # which is what makes a 180 degree sweep draw the half the model shows
        turn = np.array([[0.0, -1.0], [1.0, 0.0]]) @ rim
        assert np.allclose(turn * np.linalg.norm(minor), minor, atol=1e-12)


def test_a_diameter_and_the_equator_are_not_drawn_as_ellipses():
    c = Construction()
    diameter = c.add_line(c.add_point(0.5, 0.0), c.add_point(-0.5, 0.0))
    assert geo.line_ellipse(diameter.normal) is None
    text = gclc.to_gclc(c)
    assert "drawellipsearc" not in text and "a diameter" in text

    c = Construction()
    equator = c.add_line(c.add_point(1.0, 0.0), c.add_point(0.0, 1.0))
    assert geo.is_boundary_line(equator.normal)
    text = gclc.to_gclc(c)
    assert "drawcircle Ocentre Orim" in text and "the rim circle itself" in text


def test_a_segment_that_leaves_through_the_rim_comes_back_as_two_arcs():
    c = Construction()
    a, b = c.add_point(0.93, 0.1), c.add_point(-0.9, 0.2)
    seg = c.add_line(a, b, SEGMENT)
    assert len(geo.segment_arcs(*seg.endpoints())) == 2, "the model splits it"
    words = list(statements(gclc.to_gclc(c)))
    arcs = [w for w in words if w[0] == "drawellipsearc2"]
    assert len(arcs) == 3, "the two pieces, plus the whole line behind them"
    for arc in arcs:
        offset, sweep = float(arc[-2]), float(arc[-1])
        assert 0.0 <= offset <= 360.0 and 0.0 < sweep <= 180.0
    pieces = [a for a in arcs if float(a[-1]) < 180.0 - 1e-6]
    assert len(pieces) == 2 and sum(float(a[-1]) for a in pieces) < 180.0 + 1e-6


def test_colours_come_across_as_gclc_triples():
    c = Construction()
    a = c.add_point(0.2, 0.1, "#1a9e6a")
    b = c.add_point(-0.3, 0.4, "#e8543f")
    c.add_line(a, b, SEGMENT, color="#2f7bd6")
    colours = [tuple(words[1:]) for words in statements(gclc.to_gclc(c))
               if words[0] == "color"]
    assert ("26", "158", "106") in colours and ("232", "84", "63") in colours
    assert ("47", "123", "214") in colours
    # the faint context line has no transparency to lean on, so it is paler
    assert ("197", "218", "244") in colours
    for triple in colours:
        assert all(0 <= int(value) <= 255 for value in triple)


def test_plain_drops_the_colour_and_dashes_the_construction_lines():
    """Old-school: black ink, and the rest of a line dashed instead of faint."""
    c = Construction()
    a, b = c.add_point(0.5, 0.35), c.add_point(-0.45, 0.15)
    c.add_line(a, b, SEGMENT)
    plain = gclc.to_gclc(c, plain=True)
    assert not [w for w in statements(plain) if w[0] == "color"], "no colour at all"
    assert "drawdashellipsearc2 Ocentre" in plain, "the whole line, dashed"
    assert "\ndrawellipsearc2 Ocentre" in plain, "the segment itself, solid"
    assert "Drawn plain" in plain, "and the header says so"

    coloured = gclc.to_gclc(c)
    assert [w for w in statements(coloured) if w[0] == "color"], "unlike the default"
    assert "drawdashellipsearc" not in coloured, "only the rim is dashed in colour"
    for text in (plain, coloured):  # the geometry is the same either way
        assert [w for w in statements(text) if w[0] == "ang_point" and w[1] == "aX"]
    arcs = lambda text: [w[1:] for w in statements(text) if w[0].endswith("ellipsearc2")]
    assert arcs(plain) == arcs(coloured), "the same arcs in the same places, other ink"


def test_plain_dashes_the_degenerate_lines_too():
    for (ax, ay), (bx, by), expected in [((0.5, 0.0), (-0.4, 0.0), "drawdashsegment"),
                                         ((1.0, 0.0), (0.0, 1.0), "drawdashcircle")]:
        c = Construction()
        a, b = c.add_point(ax, ay), c.add_point(bx, by)
        c.add_line(a, b, SEGMENT)
        plain = gclc.to_gclc(c, plain=True)
        # the rim is a dashed circle in every file, so count rather than search
        assert plain.count(expected) >= 1 + (expected == "drawdashcircle")


def test_the_conformal_view_exports_circles_instead_of_ellipses():
    c = Construction()
    a, b = c.add_point(0.5, 0.35), c.add_point(-0.45, 0.15)
    line = c.add_line(a, b)
    text = gclc.to_gclc(c, projection=geo.STEREOGRAPHIC)
    assert "View: stereographic" in text and "arc of a circle" in text

    placed = {w[1]: np.array([float(w[2]), float(w[3])])
              for w in statements(text) if w[0] == "ang_point"}
    centre, major, minor = geo.STEREOGRAPHIC.conic(line.normal)
    assert np.allclose(placed["aC"], centre, atol=1e-5), "the circle's centre is named"
    for name, axis in (("aX", major), ("aY", minor)):
        assert abs(np.linalg.norm(placed[name] - centre)
                   - np.linalg.norm(axis)) < 1e-5, "both axes are the radius"
    # the same construction, drawn the other way, is a different picture
    straight = gclc.to_gclc(c)
    assert "half an ellipse" in straight and "aC" not in straight


def test_a_point_lands_where_the_projection_puts_it():
    c = Construction()
    a = c.add_point(0.6, 0.2)
    for projection in (geo.ORTHOGONAL, geo.STEREOGRAPHIC):
        text = gclc.to_gclc(c, projection=projection)
        placed = [np.array([float(w[2]), float(w[3])]) for w in statements(text)
                  if w[0] == "ang_point" and w[1] == "A"]
        assert np.allclose(placed[0], projection.project(a.vector), atol=1e-5)
    # and the two really do differ - the conformal view pulls points inward
    assert (np.linalg.norm(geo.STEREOGRAPHIC.project(a.vector))
            < np.linalg.norm(geo.ORTHOGONAL.project(a.vector)))


def test_what_a_triangle_measures_travels_in_the_comments():
    c = Construction()
    a, b, d = c.add_point(0.0, 0.0), c.add_point(0.4, 0.0), c.add_point(0.0, 0.6)
    triangle = c.add_triangle(a, b, d)
    text = gclc.to_gclc(c)
    assert f"area {triangle.area():.4f}" in text and "Girard" in text
    assert "triangle ABC" in text


def test_a_triangle_that_bounds_no_disk_says_so_instead():
    c = Construction()
    a, b, d = c.add_point(0.95, 0.0), c.add_point(-0.3, 0.9), c.add_point(-0.35, -0.9)
    c.add_triangle(a, b, d)
    text = gclc.to_gclc(c)
    assert "bounds no disk" in text and "area" not in text.split("triangle ABC")[1][:200]


def test_an_undetermined_point_is_left_out_but_accounted_for():
    c = Construction()
    a, b = c.add_point(0.6, 0.2), c.add_point(-0.4, 0.5)
    d = c.add_point(0.1, -0.6)
    meet = c.add_meet(c.add_line(a, b), c.add_line(a, d))
    d.move_to(*b.xy)  # the two lines fall together and the meet loses its place
    assert meet.xy is None
    text = gclc.to_gclc(c)
    assert "nowhere to be" in text
    assert not any(words[0] == "ang_point" and words[1] == meet.label
                   for words in statements(text))


def test_an_empty_construction_still_gives_a_usable_file():
    text = gclc.to_gclc(Construction())
    assert "dim 100 100" in text and "drawdashcircle Ocentre Orim" in text
    assert "0 points, 0 lines" in text


def test_export_writes_the_file_and_supplies_the_suffix():
    c = sample_construction()
    with tempfile.TemporaryDirectory() as folder:
        path = gclc.export(c, os.path.join(folder, "drawing"))
        assert path.endswith(".gcl") and os.path.exists(path)
        with open(path, encoding="utf-8") as handle:
            assert handle.read() == gclc.to_gclc(c)
        kept = gclc.export(c, os.path.join(folder, "named.txt"))
        assert kept.endswith("named.txt"), "a suffix of your own is left alone"
    try:
        gclc.export(c, "   ")
    except ValueError:
        pass
    else:
        raise AssertionError("an empty name should be refused")


# ------------------------------------------------------- with gclc itself


def compile_with_gclc(text: str, folder: str) -> str:
    """Run the real gclc over the text and hand back the SVG it draws."""
    binary = find_gclc()
    with open(os.path.join(folder, "t.gcl"), "w", encoding="utf-8") as handle:
        handle.write(text)
    done = subprocess.run([binary, "t.gcl", "-svg"], cwd=folder,
                          capture_output=True, text=True, timeout=120)
    assert "successfully processed" in done.stdout, \
        f"gclc rejected the file:\n{done.stdout}\n{done.stderr}"
    with open(os.path.join(folder, "t.svg"), encoding="utf-8") as handle:
        return handle.read()


def drawn_pieces(svg: str, color: str, sheet: gclc.Sheet):
    """Every straight piece gclc drew in one colour, back in disk coordinates."""
    def to_disk(x, y):
        return np.array([(float(x) - sheet.size / 2) / sheet.radius,
                         ((sheet.size - float(y)) - sheet.size / 2) / sheet.radius])
    found = re.findall(r'<line x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"'
                       r'[^>]*stroke:' + color.upper(), svg)
    return [(to_disk(x1, y1), to_disk(x2, y2)) for x1, y1, x2, y2 in found]


def ink(pieces, samples: int = 101) -> np.ndarray:
    """The drawn ink as points, each straight piece filled in - not just its
    ends, which is all a single long `drawsegment` would otherwise put in."""
    t = np.linspace(0.0, 1.0, samples)[:, None]
    return np.vstack([start + (end - start) * t for start, end in pieces])


def test_gclc_accepts_what_we_write():
    if find_gclc() is None:
        print("      (no gclc on this machine - skipped)", end="")
        return
    for plain in (False, True):
        with tempfile.TemporaryDirectory() as folder:
            svg = compile_with_gclc(gclc.to_gclc(sample_construction(), plain=plain),
                                    folder)
        assert svg.lstrip().startswith("<?xml") and "</svg>" in svg
        inked = set(re.findall(r'stroke:(#[0-9A-Fa-f]{6})', svg))
        if plain:
            assert inked <= {"#000000"}, f"plain should be black only, got {inked}"
        else:
            assert len(inked) > 1, "the coloured one really is coloured"


def test_gclc_draws_the_curve_the_model_says():
    """Compile it, read the picture back, and check it lies on the real line."""
    if find_gclc() is None:
        print("      (no gclc on this machine - skipped)", end="")
        return
    sheet = gclc.Sheet()
    for projection in (geo.ORTHOGONAL, geo.STEREOGRAPHIC):
        for (ax, ay), (bx, by), kind in [((0.5, 0.35), (-0.45, 0.15), None),
                                         ((0.5, 0.35), (-0.45, 0.15), SEGMENT),
                                         ((0.62, 0.3), (-0.2, -0.75), SEGMENT),
                                         ((0.93, 0.1), (-0.9, 0.2), SEGMENT),
                                         # nearly a diameter: drawn straight, and
                                         # rightly so - it is straight to 5e-7
                                         ((0.6, 0.0), (-0.6, 1e-6), None)]:
            c = Construction()
            line = c.add_line(c.add_point(ax, ay), c.add_point(bx, by), kind or "line")
            with tempfile.TemporaryDirectory() as folder:
                svg = compile_with_gclc(gclc.to_gclc(c, projection=projection), folder)
            pieces = drawn_pieces(svg, line.color, sheet)
            straight = abs(line.normal[2]) < 1e-4  # a near-diameter may be one stroke
            assert len(pieces) > (0 if straight else 10), \
                "the arc should come out as a smooth curve"
            drawn = ink(pieces)
            assert max(np.linalg.norm(xy) for xy in drawn) <= 1.0 + 1e-3, "in the disk"
            # measured in the picture, not by lifting back: at the rim, lifting
            # takes the square root of almost nothing and tells you little
            truth = projection.project(
                geo.line_vectors(line.normal, 2000) if kind is None
                else np.vstack(geo.segment_vector_paths(*line.endpoints(), 2000)))
            stray = max(min(np.linalg.norm(truth - xy, axis=1)) for xy in drawn)
            gap = max(min(np.linalg.norm(drawn - point, axis=1)) for point in truth)
            assert stray < 0.01, f"{projection.name} drew something off the curve"
            assert gap < 0.02, f"{projection.name} misses part of the curve ({gap:.4f})"


# ---------------------------------------------------------------- circles


def test_a_snug_circle_is_one_closed_ellipse():
    c = Construction()
    circle = c.add_circle(c.add_point(0.15, 0.1), c.add_point(0.4, 0.15))
    text = to_check = gclc.to_gclc(c)
    drawn = [w for w in statements(to_check) if w[0] == "drawellipse"]
    assert len(drawn) == 1, "one command, not a chain and not two arcs"
    assert not any(w[0] == "drawellipsearc2" for w in statements(text))
    assert f"circle {circle.label} about A through B" in text


def test_a_circle_through_the_rim_is_two_arcs_of_two_conics():
    c = Construction()
    c.add_circle(c.add_point(0.85, 0.0), c.add_point(0.3, 0.0))
    text = gclc.to_gclc(c)
    arcs = [w for w in statements(text) if w[0] == "drawellipsearc2"]
    assert len(arcs) == 2, "the visible piece and the folded one"
    assert not any(w[0] == "drawellipse" for w in statements(text))
    assert len({w[1] for w in arcs}) == 2, "each piece has a conic of its own"


def test_the_folded_conic_names_stay_clear_of_every_line():
    c = Construction()
    a, b = c.add_point(0.85, 0.0), c.add_point(0.3, 0.0)
    c.add_circle(a, b)
    c.add_line(a, b)
    text = gclc.to_gclc(c)
    named = [w[1] for w in statements(text) if w[0] == "ang_point"]
    assert len(named) == len(set(named)) or         all(named.count(n) == 1 for n in named if n[0].islower()),         "no conic point is defined twice under one name"


def test_the_circle_ellipse_has_the_axes_the_model_says():
    c = Construction()
    circle = c.add_circle(c.add_point(0.2, 0.25), c.add_point(0.45, -0.1))
    axis, radius = circle.axis_radius()
    centre, major, minor = geo.ORTHOGONAL.point_conic(axis, radius)
    placed = {w[1]: np.array([float(w[2]), float(w[3])])
              for w in statements(gclc.to_gclc(c)) if w[0] == "ang_point"}
    label = circle.label
    assert np.allclose(placed[f"{label}C"], centre, atol=1e-5)
    assert np.allclose(placed[f"{label}X"], centre + major, atol=1e-5)
    assert np.allclose(placed[f"{label}Y"], centre + minor, atol=1e-5)


def test_the_conformal_view_draws_a_circle_as_a_circle():
    c = Construction()
    circle = c.add_circle(c.add_point(0.3, 0.2), c.add_point(0.55, 0.35))
    placed = {w[1]: np.array([float(w[2]), float(w[3])])
              for w in statements(gclc.to_gclc(c, projection=geo.STEREOGRAPHIC))
              if w[0] == "ang_point"}
    label = circle.label
    spans = (np.linalg.norm(placed[f"{label}X"] - placed[f"{label}C"]),
             np.linalg.norm(placed[f"{label}Y"] - placed[f"{label}C"]))
    assert abs(spans[0] - spans[1]) < 1e-9, "equal axes: it really is a circle"


def test_a_circle_of_radius_half_pi_is_named_the_polar():
    c = Construction()
    a = c.add_point(0.0, 0.3)
    polar = c.add_polar(a)
    foot = c.add_point(*geo.project(geo.line_vectors(polar.normal, 101)[50]))
    c.add_circle(a, foot)
    assert "the polar line of its centre" in gclc.to_gclc(c)


def test_an_undetermined_circle_is_left_out_but_accounted_for():
    c = Construction()
    a, b = c.add_point(0.6, 0.2), c.add_point(-0.4, 0.5)
    d = c.add_point(0.1, -0.6)
    meet = c.add_meet(c.add_line(a, b), c.add_line(a, d))
    circle = c.add_circle(meet, d)
    d.move_to(*b.xy)  # the lines fall together; the meet, then the circle, go
    assert circle.axis_radius() is None
    text = gclc.to_gclc(c)
    assert f"circle {circle.label} is undetermined" in text


def test_gclc_draws_the_circle_the_model_says():
    """Compile a folding circle and check the picture lies on the true curve."""
    if find_gclc() is None:
        print("      (no gclc on this machine - skipped)", end="")
        return
    sheet = gclc.Sheet()
    for projection in (geo.ORTHOGONAL, geo.STEREOGRAPHIC):
        for centre, through in [((0.15, 0.1), (0.5, 0.2)),      # snug inside
                                ((0.8, 0.1), (0.25, 0.0)),     # out through the rim
                                ((0.8, 0.0), (1e-5, 0.0)),     # folded conic huge
                                ((0.75, 0.0), (2e-6, 0.0)),    # huger still
                                ((1.0, 0.0), (1e-5, 0.7))]:    # radius a hair under pi/2
            c = Construction()
            circle = c.add_circle(c.add_point(*centre), c.add_point(*through))
            with tempfile.TemporaryDirectory() as folder:
                svg = compile_with_gclc(gclc.to_gclc(c, projection=projection), folder)
            pieces = drawn_pieces(svg, circle.color, sheet)
            assert len(pieces) > 10, "the circle should come out as a smooth curve"
            drawn = ink(pieces)
            truth = np.vstack([projection.project(path) for path in
                               geo.circle_vector_paths(*circle.axis_radius(), 2000)])
            stray = max(min(np.linalg.norm(truth - xy, axis=1)) for xy in drawn)
            gap = max(min(np.linalg.norm(drawn - point, axis=1)) for point in truth)
            assert stray < 0.01, f"{projection.name} drew something off the circle"
            assert gap < 0.02, f"{projection.name} misses part of the circle ({gap:.4f})"


def test_a_nearly_degenerate_conic_is_never_named():
    """A stereographic circle whose section almost passes through the south
    pole would need a conic thousands of disk radii across; arc angles are
    written with four decimals of a degree, which on such a conic scatters
    points across the page or rounds the whole sweep away.  Past FAR the
    exporter must fall back to the sampled curve instead."""
    for through in ((1e-5, 0.0), (2e-6, 0.0), (0.0, 0.0)):
        c = Construction()
        c.add_circle(c.add_point(0.8, 0.0), c.add_point(*through))
        text = gclc.to_gclc(c, projection=geo.STEREOGRAPHIC)
        for words in statements(text):
            if words[0] == "ang_point":
                assert all(abs(float(w)) <= gclc.FAR + 1 for w in words[2:4]), \
                    f"an outsized conic point was written: {' '.join(words)}"
        # the folded piece is still there - as sampled segments, not dropped
        drawn = [w[0] for w in statements(text)]
        assert "drawsegment" in drawn, "the near-degenerate piece is sampled"


def test_circles_advance_the_auto_palette():
    c = Construction()
    points = [c.add_point(x, 0.05) for x in (0.55, 0.15, -0.35)]
    first = c.add_circle(points[0], points[1])
    second = c.add_circle(points[1], points[2])
    line = c.add_line(points[0], points[2])
    assert first.color != second.color, "two circles are told apart by colour"
    assert second.color != line.color, "and the line continues the same cycle"


def test_bisectors_come_across_as_two_more_curves():
    c = Construction()
    a, b = c.add_point(0.3, 0.1), c.add_point(-0.3, 0.2)
    d, e = c.add_point(0.1, -0.35), c.add_point(-0.1, 0.4)
    made = c.add_bisectors(c.add_line(a, b), c.add_line(d, e))
    for projection in (geo.ORTHOGONAL, geo.STEREOGRAPHIC):
        text = gclc.to_gclc(c, projection=projection)
        assert text.count("bisector") >= 2, "each named in the comments"
        arcs = [w for w in statements(text) if w[0].startswith("drawellipsearc")]
        assert len(arcs) >= 4, "four whole lines, each a real arc"
        for bisector in made:
            assert bisector.label in text


def test_a_midpoint_travels_with_its_story():
    c = Construction()
    m = c.add_midpoint(c.add_point(0.3, 0.1), c.add_point(-0.25, 0.35))
    text = gclc.to_gclc(c)
    assert f"{m.label} is the midpoint of AB" in text
    assert any(w[0] == "ang_point" and w[1] == m.label for w in statements(text))


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} checks passed")
