"""Check TikZ syntax, projected geometry, file output, and optional LaTeX compilation."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import numpy as np

from elliptic import geometry as geo
from elliptic import tikz
from elliptic.model import SEGMENT, Construction
from tests.test_gclc import sample_construction


NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
PAIR = rf"\(({NUMBER}),\s*({NUMBER})\)"
COORDINATE = re.compile(rf"\\coordinate \(([^)]+)\) at {PAIR};")
ARC = re.compile(
    rf"rotate=({NUMBER})\] {PAIR} arc\[start angle=({NUMBER}), "
    rf"delta angle=({NUMBER}), x radius=({NUMBER}), y radius=({NUMBER})\]")


def curves(text: str) -> list[np.ndarray]:
    """Read the numeric drawing paths back, applying TikZ's arc and rotation rules."""
    paths = []
    for line in text.splitlines():
        if not line.startswith(r"\draw["):
            continue
        arc = ARC.search(line)
        if arc:
            rotation, x, y, start, sweep, a, b = map(float, arc.groups())
            angle = np.deg2rad(start + np.linspace(0, sweep, 101))
            origin = [x - a * np.cos(angle[0]), y - b * np.sin(angle[0])]
            local = origin + np.column_stack([a * np.cos(angle), b * np.sin(angle)])
            c, s = np.cos(np.deg2rad(rotation)), np.sin(np.deg2rad(rotation))
            paths.append(local @ np.array([[c, s], [-s, c]]))
        elif " -- " in line:
            paths.append(np.array(re.findall(PAIR, line), dtype=float))
    return paths


def assert_in_disk(paths):
    for path in paths:
        path = np.atleast_2d(path)
        assert np.isfinite(path).all(), "all drawn coordinates must be finite"
        assert np.max(np.linalg.norm(path, axis=1)) < 1 + 2e-6


def test_snippet_and_page_dimensions():
    text = tikz.to_tikz(Construction(), size=120, margin=10)
    assert text.count(r"\begin{tikzpicture}") == 1
    assert text.count(r"\end{tikzpicture}") == 1
    assert r"\documentclass" not in text
    assert r"\usepackage{tikz}" in text
    assert re.search(r"x=50(?:\.0+)?mm, y=50(?:\.0+)?mm", text)
    assert "circle[radius=1]" in text
    bounds = next(line for line in text.splitlines() if "use as bounding box" in line)
    assert np.allclose(np.array(re.findall(PAIR, bounds), dtype=float),
                       [[-1.2, -1.2], [1.2, 1.2]])


def test_point_coordinates_follow_both_projections():
    c = sample_construction()
    c.add_midpoint(c.points[0], c.points[1])
    for projection in (geo.ORTHOGONAL, geo.STEREOGRAPHIC):
        text = tikz.to_tikz(c, projection=projection)
        placed = {name: np.array([float(x), float(y)])
                  for name, x, y in COORDINATE.findall(text)}
        assert len(placed) == len(c.points)
        for point in c.points:
            assert np.allclose(placed[point.label], projection.project(point.vector), atol=1e-7)
            assert rf"\textit{{{point.label}}}" in text
        assert_in_disk(list(placed.values()))


def test_exact_line_arcs_lie_on_the_spherical_line():
    c = Construction()
    line = c.add_line(c.add_point(0.55, 0.12), c.add_point(-0.25, 0.6))
    for projection in (geo.ORTHOGONAL, geo.STEREOGRAPHIC):
        text = tikz.to_tikz(c, projection=projection)
        paths = curves(text)
        assert len(paths) == 1 and len(ARC.findall(text)) == 1
        assert_in_disk(paths)
        vectors = np.array([projection.lift(*xy) for xy in paths[0][1:-1]])
        assert np.max(np.abs(vectors @ line.normal)) < 2e-6
        assert np.allclose(paths[0][0], -paths[0][-1], atol=1e-6)


def test_folded_segment_has_two_separate_pieces():
    c = Construction()
    line = c.add_line(c.add_point(0.93, 0.1), c.add_point(-0.9, 0.2), SEGMENT)
    pieces = geo.segment_vector_paths(*line.endpoints())
    assert len(pieces) == 2
    for projection in (geo.ORTHOGONAL, geo.STEREOGRAPHIC):
        paths = curves(tikz.to_tikz(c, projection=projection))
        assert len(paths) == 3, "the context line followed by two separate segment paths"
        assert_in_disk(paths)
        for drawn, expected in zip(paths[1:], pieces):
            assert np.allclose(drawn[[0, -1]], projection.project(expected[[0, -1]]), atol=1e-6)
            vectors = np.array([projection.lift(*xy) for xy in drawn[1:-1]])
            assert np.max(np.abs(vectors @ line.normal)) < 1e-5


def test_circle_paths_lie_at_the_requested_elliptic_distance():
    for centre, through in [((0.15, 0.1), (0.5, 0.2)),
                            ((0.8, 0.1), (0.25, 0.0)),
                            ((0.8, 0.0), (1e-5, 0.0)),
                            ((1.0, 0.0), (1e-5, 0.7))]:
        c = Construction()
        circle = c.add_circle(c.add_point(*centre), c.add_point(*through))
        axis, radius = circle.axis_radius()
        expected = geo.circle_vector_paths(axis, radius)
        for projection in (geo.ORTHOGONAL, geo.STEREOGRAPHIC):
            paths = curves(tikz.to_tikz(c, projection=projection))
            assert len(paths) == len(expected), "folded circles must keep their separate paths"
            assert_in_disk(paths)
            for path in paths:
                # Rounding a rim coordinate before lifting magnifies its z error.
                inside = path[np.linalg.norm(path, axis=1) < 1 - 1e-5]
                vectors = np.array([projection.lift(*xy) for xy in inside])
                assert np.max(np.abs(np.abs(vectors @ axis) - np.cos(radius))) < 1e-5


def test_plain_changes_ink_without_changing_geometry():
    c = sample_construction()
    colored = tikz.to_tikz(c)
    plain = tikz.to_tikz(c, plain=True)
    assert r"\definecolor" in colored and r"\definecolor" not in plain
    assert "draw=black" in plain and "text=black" in plain
    assert "draw opacity=" in colored and "draw opacity=" not in plain
    assert plain.count("dashed") > colored.count("dashed")
    colored_paths, plain_paths = curves(colored), curves(plain)
    assert len(colored_paths) == len(plain_paths)
    assert all(np.array_equal(a, b) for a, b in zip(colored_paths, plain_paths))


def test_boundary_diameter_and_flat_conics_remain_finite():
    for endpoints in [((0.5, 0.0), (-0.5, 0.0)),
                      ((0.5, 0.0), (-0.5, 1e-6)),
                      ((1.0, 0.0), (0.0, 1.0))]:
        c = Construction()
        line = c.add_line(*(c.add_point(*xy) for xy in endpoints), SEGMENT)
        for projection in (geo.ORTHOGONAL, geo.STEREOGRAPHIC):
            text = tikz.to_tikz(c, projection=projection, plain=True)
            paths = curves(text)
            assert paths
            assert_in_disk(paths)
            if geo.is_boundary_line(line.normal):
                assert text.count("circle[radius=1]") == 2
            elif abs(line.normal[2]) < 1e-6:
                assert " -- " in text


def test_undefined_objects_are_omitted_safely():
    c = Construction()
    a, b, d = [c.add_point(*xy) for xy in ((0.6, 0.2), (-0.4, 0.5), (0.1, -0.6))]
    meet = c.add_meet(c.add_line(a, b), c.add_line(a, d))
    circle = c.add_circle(meet, d)
    d.move_to(*b.xy)
    assert meet.vector is None and circle.axis_radius() is None
    for projection in (geo.ORTHOGONAL, geo.STEREOGRAPHIC):
        text = tikz.to_tikz(c, projection=projection)
        assert "undetermined" in text
        assert meet.label not in {name for name, _, _ in COORDINATE.findall(text)}
        assert_in_disk(curves(text))


def test_tex_special_characters_in_labels_and_multiline_title():
    c = Construction()
    c.add_point(0.2, 0.1).label = r"A_1%&#${}\^~"
    text = tikz.to_tikz(c, title="First line\nSecond line")
    assert "% First line\n% Second line" in text
    assert r"A\_1\%\&\#\$\{\}" in text
    for command in (r"\textbackslash{}", r"\textasciicircum{}", r"\textasciitilde{}"):
        assert command in text
    assert len(COORDINATE.findall(text)) == 1


def test_export_suffixes_paths_and_utf8():
    c = sample_construction()
    with tempfile.TemporaryDirectory(prefix="tikz.export.") as folder:
        directory = Path(folder)
        for supplied, expected in [(directory / "construction", "construction.txt"),
                                   (str(directory / "chosen.txt"), "chosen.txt"),
                                   (directory / "picture.tex", "picture.tex")]:
            result = Path(tikz.export(c, supplied, title="Elliptic — disk", plain=True))
            assert result == directory / expected
            assert result.read_text(encoding="utf-8") == tikz.to_tikz(
                c, title="Elliptic — disk", plain=True)


def test_export_reports_missing_filename_and_write_errors():
    for name in ("", "  "):
        try:
            tikz.export(Construction(), name)
        except ValueError:
            pass
        else:
            raise AssertionError("a blank file name must be rejected")
    with tempfile.TemporaryDirectory() as folder:
        try:
            tikz.export(Construction(), Path(folder) / "missing" / "drawing.txt")
        except OSError:
            pass
        else:
            raise AssertionError("a failed write must be reported to the caller")


def test_snippets_compile_with_pdflatex_when_available():
    executable = shutil.which("pdflatex")
    if executable is None:
        print("      (no pdflatex on this machine - skipped)", end="")
        return
    kpsewhich = shutil.which("kpsewhich")
    if kpsewhich and not subprocess.run([kpsewhich, "tikz.sty"], capture_output=True,
                                        text=True, timeout=15).stdout.strip():
        print("      (TikZ is not installed - skipped)", end="")
        return
    version = subprocess.run([executable, "--version"], capture_output=True,
                             text=True, timeout=15)
    command = [executable, "-interaction=nonstopmode", "-halt-on-error", "-no-shell-escape"]
    if "MiKTeX" in version.stdout:
        command.append("--disable-installer")
    c = sample_construction()
    c.add_bisectors(c.lines[0], c.lines[1])
    c.add_pole(c.lines[0])
    c.add_midpoint(c.points[0], c.points[1])
    c.add_point(0.2, 0.1).label = r"A_1%&#${}\^~"
    c.add_line(c.add_point(1, 0), c.add_point(0, 1), SEGMENT)
    c.add_line(c.add_point(0.5, 0), c.add_point(-0.5, 0), SEGMENT)
    c.add_circle(c.add_point(0.8, 0), c.add_point(1e-5, 0))
    with tempfile.TemporaryDirectory(prefix="tikz-compile-") as folder:
        directory = Path(folder)
        inputs = []
        for projection in (geo.ORTHOGONAL, geo.STEREOGRAPHIC):
            for plain in (False, True):
                name = f"{projection.name}-{plain}.txt"
                tikz.export(c, directory / name, projection=projection, plain=plain)
                inputs.append(rf"\input{{{name}}}\newpage")
        source = "\n".join([r"\documentclass{article}", r"\usepackage{tikz}",
                            r"\begin{document}", *inputs, r"\end{document}"])
        (directory / "check.tex").write_text(source, encoding="utf-8")
        result = subprocess.run([*command, "check.tex"], cwd=folder, capture_output=True,
                                text=True, errors="replace", timeout=60)
        assert result.returncode == 0, result.stdout[-6000:] + result.stderr[-2000:]
        assert (directory / "check.pdf").stat().st_size > 0


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
