"""Check the sphere TikZ camera, visibility, display options and LaTeX output."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import numpy as np

from elliptic import geometry as geo
from elliptic import tikz_sphere
from elliptic.model import SEGMENT, Construction
from tests.test_gclc import sample_construction
from tests.test_tikz import COORDINATE, NUMBER, PAIR


SECTIONS = ("back graticule", "back construction", "sphere", "upper hemisphere",
            "equatorial disk", "flattened construction", "projectors", "antipodes",
            "front graticule", "front construction", "point markers", "front labels")
QUIET = {"labels": False, "rim": False, "poles": False, "meets": False,
         "rays": False, "antipodes": False}


def section(text: str, name: str) -> str:
    start = text.find(f"% {name}\n")
    if start < 0:
        return ""
    start += len(name) + 3
    following = [text.find(f"% {other}\n", start) for other in SECTIONS]
    return text[start:min((i for i in following if i >= 0), default=len(text))]


def paths(text: str) -> list[np.ndarray]:
    return [np.array(re.findall(PAIR, line), dtype=float)
            for line in text.splitlines() if line.startswith(r"\draw[") and " -- " in line]


def coordinates(text: str) -> dict[str, np.ndarray]:
    return {name: np.array([float(x), float(y)]) for name, x, y in COORDINATE.findall(text)}


def camera_projection(vectors, azimuth: float, elevation: float) -> np.ndarray:
    """The explicit camera rotation, independent of the exporter's implementation."""
    right = [-np.sin(azimuth), np.cos(azimuth), 0]
    up = [-np.sin(elevation) * np.cos(azimuth),
          -np.sin(elevation) * np.sin(azimuth), np.cos(elevation)]
    return np.asarray(vectors) @ np.array([right, up]).T


def test_points_follow_camera_rotation_and_zoom():
    c = Construction()
    point = c.add_point(0.45, -0.2)
    positions = []
    for azimuth, elevation in [(0.0, 0.5), (1.2, -0.4), (-2.0, 1.1)]:
        scales = []
        for zoom in (0.6, 1.4):
            text = tikz_sphere.to_tikz(c, flags=QUIET, azimuth=azimuth,
                                       elevation=elevation, zoom=zoom)
            marks = coordinates(section(text, "point markers"))
            assert len(marks) == 1
            position = next(iter(marks.values()))
            assert np.allclose(position, camera_projection(point.vector, azimuth, elevation),
                               atol=1e-7)
            scales.append(float(re.search(rf"x=({NUMBER})mm", text)[1]))
        assert np.isclose(scales[1] / scales[0], 1.4 / 0.6)
        positions.append(position)
    assert not np.allclose(positions[0], positions[1])


def test_front_and_back_pieces_meet_at_the_silhouette():
    c = Construction()
    c.add_line(c.add_point(1, 0), c.add_point(0, 1))
    text = tikz_sphere.to_tikz(c, flags=QUIET, azimuth=0, elevation=0.4)
    back = section(text, "back construction")
    front = section(text, "front construction")
    assert paths(back) and paths(front)
    for part, sign, opacity in ((back, 1, 0.3), (front, -1, 1.0)):
        drawn = paths(part)
        # The back half of the equator has positive screen y for this camera.
        assert all(np.min(sign * path[:, 1]) >= -1e-7 for path in drawn)
        assert all(np.max(np.linalg.norm(path, axis=1)) <= 1 + 1e-7 for path in drawn)
        alphas = re.findall(rf"draw opacity=({NUMBER})", part)
        assert alphas and all(np.isclose(float(value), opacity) for value in alphas)
        endpoints = np.concatenate([path[[0, -1]] for path in drawn])
        for edge in ([-1, 0], [1, 0]):
            assert np.min(np.linalg.norm(endpoints - edge, axis=1)) < 2e-4
    assert text.index("% back construction") < text.index("% sphere")
    assert text.index("% sphere") < text.index("% front construction")


def test_projectors_use_selected_disk_projection():
    c = Construction()
    point = c.add_point(0.55, 0.2)
    azimuth, elevation = 0.3, 0.7
    pictures = []
    for projection in (geo.ORTHOGONAL, geo.STEREOGRAPHIC):
        text = tikz_sphere.to_tikz(c, projection=projection, azimuth=azimuth,
                                   elevation=elevation, flags={**QUIET, "rays": True})
        rays = paths(section(text, "projectors"))
        assert len(rays) == 1
        assert np.allclose(rays[0], camera_projection(projection.ray(point.vector),
                                                    azimuth, elevation), atol=1e-7)
        pictures.append(text)
    assert section(pictures[0], "flattened construction") != section(
        pictures[1], "flattened construction")
    assert coordinates(section(pictures[0], "point markers")).keys() == coordinates(
        section(pictures[1], "point markers")).keys()
    assert np.allclose(list(coordinates(section(pictures[0], "point markers")).values()),
                       list(coordinates(section(pictures[1], "point markers")).values()))


def test_antipodes_and_labels_follow_visibility_flags():
    c = Construction()
    point = c.add_point(0.3, 0.1)
    point.label = "VisiblePoint"
    azimuth, elevation = 0.2, 0.8
    hidden = tikz_sphere.to_tikz(c, flags=QUIET, azimuth=azimuth, elevation=elevation)
    assert not section(hidden, "projectors") and not section(hidden, "antipodes")
    assert r"\node[" not in section(hidden, "front labels")
    shown = tikz_sphere.to_tikz(c, flags={**QUIET, "labels": True, "antipodes": True},
                              azimuth=azimuth, elevation=elevation)
    assert "VisiblePoint" in section(shown, "front labels")
    diameters = paths(section(shown, "antipodes"))
    assert len(diameters) == 1
    expected = camera_projection([point.vector, -point.vector], azimuth, elevation)
    assert np.allclose(diameters[0], expected, atol=1e-7)
    reversed_view = tikz_sphere.to_tikz(c, flags={**QUIET, "labels": True},
                                      azimuth=azimuth + np.pi, elevation=-elevation)
    assert "VisiblePoint" not in section(reversed_view, "front labels")


def test_plain_is_grayscale_and_preserves_construction_geometry():
    c = sample_construction()
    color = tikz_sphere.to_tikz(c, flags={"antipodes": True})
    plain = tikz_sphere.to_tikz(c, plain=True, flags={"antipodes": True})
    assert r"\definecolor" in color and r"\definecolor" not in plain
    assert "draw=black" in plain
    assert tikz_sphere.to_tikz(c, flags={"plain": True, "antipodes": True}) == plain
    for name in ("front construction", "back construction", "flattened construction"):
        colored_paths, plain_paths = paths(section(color, name)), paths(section(plain, name))
        assert len(colored_paths) == len(plain_paths) > 0
        assert all(np.array_equal(a, b) for a, b in zip(colored_paths, plain_paths))


def test_boundary_and_undefined_objects_remain_finite():
    c = Construction()
    a, b = c.add_point(1, 0), c.add_point(0, 1)
    c.add_line(a, b, SEGMENT)
    c.add_line(c.add_point(0.5, 0), c.add_point(-0.5, 1e-8), SEGMENT)
    c.add_circle(c.add_point(0.8, 0), c.add_point(1e-5, 0))
    d = c.add_point(0.3, 0.4)
    meet = c.add_meet(c.add_line(a, d), c.add_line(b, d))
    c.add_circle(meet, b)
    d.move_to(*a.xy)
    assert meet.vector is None
    for projection in (geo.ORTHOGONAL, geo.STEREOGRAPHIC):
        for elevation in (0, np.pi / 2, -np.pi / 2):
            text = tikz_sphere.to_tikz(c, projection=projection, elevation=elevation,
                                       flags={**QUIET, "rays": True, "antipodes": True})
            assert not re.search(r"(?<![A-Za-z])(?:nan|inf)(?![A-Za-z])", text, re.I)
            marks = coordinates(section(text, "point markers"))
            assert len(marks) == sum(point.vector is not None for point in c.points)
            for name in ("front construction", "back construction"):
                for path in paths(section(text, name)):
                    assert np.isfinite(path).all()
                    assert np.max(np.linalg.norm(path, axis=1)) <= 1 + 1e-7


def test_export_suffix_utf8_and_invalid_inputs():
    c = Construction()
    c.add_point(0.2, 0.1)
    options = {"title": "Sphere – camera\nSecond line", "azimuth": 0.8, "zoom": 1.2}
    with tempfile.TemporaryDirectory(prefix="sphere-tikz-export-") as folder:
        directory = Path(folder)
        for supplied, suffix in (("sphere", ".txt"), ("chosen.txt", ".txt"),
                                 ("picture.tex", ".tex")):
            result = Path(tikz_sphere.export(c, directory / supplied, **options))
            assert result.suffix == suffix
            assert result.read_text(encoding="utf-8") == tikz_sphere.to_tikz(c, **options)
        try:
            tikz_sphere.export(c, directory / "missing" / "sphere.txt")
        except OSError:
            pass
        else:
            raise AssertionError("write errors must reach the caller")
    for name in ("", "  "):
        try:
            tikz_sphere.export(c, name)
        except ValueError:
            pass
        else:
            raise AssertionError("blank filenames must be rejected")
    for options in ({"zoom": 0}, {"zoom": float("nan")}, {"azimuth": float("inf")},
                    {"elevation": float("nan")}, {"size": 0}, {"margin": 50}):
        try:
            tikz_sphere.to_tikz(c, **options)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid picture parameters accepted: {options}")


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
    c.add_pole(c.lines[0])
    c.add_bisectors(c.lines[0], c.lines[1])
    c.add_midpoint(c.points[0], c.points[1])
    c.add_point(0.1, 0.1).label = r"A_1%&#${}\^~" + "\u00b0\u03c0\u25b3"
    with tempfile.TemporaryDirectory(prefix="sphere-tikz-compile-") as folder:
        directory = Path(folder)
        inputs = []
        for projection in (geo.ORTHOGONAL, geo.STEREOGRAPHIC):
            for plain in (False, True):
                name = f"{projection.name}-{plain}.txt"
                tikz_sphere.export(c, directory / name, projection=projection, plain=plain,
                                   flags={"antipodes": True, "poles": True},
                                   title="First line\nSecond line", elevation=1.1)
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
