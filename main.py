#!/usr/bin/env python3
"""Entry point for the elliptic-plane disk viewer.

    python3 main.py
    python3 main.py --points 0.35 0.45 -0.6 0.2 0.1 -0.7 --lines 0 1 1 2 --save out.png
    python3 main.py --points 0.1 0.15 0.55 -0.2 -0.3 0.5 --triangles 0 1 2
"""

from __future__ import annotations

import argparse

from elliptic import EllipticDiskViewer, gclc
from elliptic.model import LINE, SEGMENT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--points", nargs="+", type=float, metavar="X Y",
                        help="start with these points placed (x y x y ...)")
    parser.add_argument("--lines", nargs="+", type=int, metavar="I J",
                        help="join those points by index (i j i j ...)")
    parser.add_argument("--segments", nargs="+", type=int, metavar="I J",
                        help="like --lines but draws the shortest path")
    parser.add_argument("--perps", nargs="+", type=int, metavar="P L",
                        help="drop perpendiculars: point index, line index, ...")
    parser.add_argument("--triangles", nargs="+", type=int, metavar="I J K",
                        help="triangles on three point indices each, with their angles")
    parser.add_argument("--polars", nargs="+", type=int, metavar="I",
                        help="the polar line of each of those points")
    parser.add_argument("--bisects", nargs="+", type=int, metavar="I J",
                        help="both angle bisectors of two lines, by line index")
    parser.add_argument("--midpoints", nargs="+", type=int, metavar="I J",
                        help="the midpoint of each pair of points, by point index")
    parser.add_argument("--meets", nargs="+", type=int, metavar="I J",
                        help="name the point where two lines cross, by line index")
    parser.add_argument("--circles", nargs="+", type=int, metavar="C T",
                        help="circles by point index: the centre, a point on it, ...")
    parser.add_argument("--save", metavar="PATH",
                        help="render to an image file instead of opening a window")
    parser.add_argument("--gclc", metavar="PATH",
                        help="write the construction as a GCLC file and exit")
    parser.add_argument("--plain", action="store_true",
                        help="with --gclc: black ink only, construction lines dashed")
    projection = parser.add_mutually_exclusive_group()
    projection.add_argument("--conformal", dest="conformal", action="store_true",
                            default=True,
                            help="draw from the south pole (the default)")
    projection.add_argument("--orthogonal", dest="conformal", action="store_false",
                            help="draw by dropping the hemisphere straight down")
    parser.add_argument("--no-sphere", dest="sphere", action="store_false",
                        help="leave out the 3-D pane showing the sphere itself")
    args = parser.parse_args()

    viewer = EllipticDiskViewer()
    viewer.flags["conformal"] = args.conformal
    viewer.flags["sphere"] = args.sphere
    build(viewer, args)

    if args.gclc:
        written = gclc.export(viewer.construction, args.gclc, plain=args.plain,
                              projection=viewer.projection)
        how = " (plain)" if args.plain else ""
        print(f"wrote {written} for GCLC, {viewer.projection.name} view{how}")
    if args.save:
        viewer.save(args.save)
        print(f"wrote {args.save}")
    if not (args.save or args.gclc):
        viewer.show()


def groups(indices, size: int, flag: str):
    """Chop a flat list of indices into tuples, complaining if it does not divide."""
    indices = indices or []
    if len(indices) % size:
        raise SystemExit(f"--{flag} needs groups of {size} indices")
    return list(zip(*[indices[k::size] for k in range(size)]))


def build(viewer: EllipticDiskViewer, args: argparse.Namespace) -> None:
    """Pre-populate the construction from the command line.

    Line indices count in creation order: --lines, then --segments, then the
    three sides of each --triangle, then --perps, then --polars - so a
    perpendicular can be dropped onto a triangle's side.
    """
    construction = viewer.construction
    coords = args.points or []
    if len(coords) % 2:
        raise SystemExit("--points needs an even number of values (x y x y ...)")
    # Command-line coordinates name positions in the view being rendered, just
    # like mouse clicks do.  In particular, conformal coordinates must first be
    # lifted through the stereographic projection rather than being mistaken
    # for orthogonal model coordinates.
    points = [construction.place_point(viewer.lift(x, y))
              for x, y in zip(coords[::2], coords[1::2])]

    def point(i):
        if not 0 <= i < len(points):
            raise SystemExit(f"point index out of range: {i}")
        return points[i]

    def line(i):
        if not 0 <= i < len(construction.lines):
            raise SystemExit(f"line index out of range: {i}")
        return construction.lines[i]

    for flag, kind in ((args.lines, LINE), (args.segments, SEGMENT)):
        for i, j in groups(flag, 2, f"{kind}s"):
            construction.add_line(point(i), point(j), kind)
    for i, j, k in groups(args.triangles, 3, "triangles"):
        construction.add_triangle(point(i), point(j), point(k))
    for i, j in groups(args.perps, 2, "perps"):
        construction.add_perpendicular(point(i), line(j))
    for (i,) in groups(args.polars, 1, "polars"):
        construction.add_polar(point(i))
    for i, j in groups(args.bisects, 2, "bisects"):
        construction.add_bisectors(line(i), line(j))
    for i, j in groups(args.midpoints, 2, "midpoints"):
        construction.add_midpoint(point(i), point(j))
    for i, j in groups(args.meets, 2, "meets"):
        construction.add_meet(line(i), line(j))
    for i, j in groups(args.circles, 2, "circles"):
        construction.add_circle(point(i), point(j))

    if points:
        viewer.changed()


if __name__ == "__main__":
    main()
