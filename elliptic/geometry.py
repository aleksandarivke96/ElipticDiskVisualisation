"""Geometry of the closed-disk model of the elliptic plane.

Model
-----
The elliptic plane is the sphere S^2 with antipodal points identified.  Every
class {v, -v} has a representative on the *closed upper hemisphere* z >= 0, and
that representative is unique except on the equator, where v and -v are both
present.  Projecting the upper hemisphere straight down onto the xy-plane gives
the closed unit disk, with diametrically opposite boundary points identified.

Consequences used below:

* A disk point (x, y) lifts to (x, y, sqrt(1 - x^2 - y^2)).
* A line is a great circle, i.e. the unit vectors orthogonal to some normal n.
  Its half in z >= 0 projects to *half* an ellipse with semi-major axis 1 and
  semi-minor axis |n_z|, running from a boundary point to its antipode.
  n_z = 0 degenerates to a diameter; n = +-z_hat is the boundary circle itself.
* Two distinct elliptic points always lie on exactly one line (no parallels).
* Distance is the angle between the lifted vectors, folded into [0, pi/2] by
  the antipodal identification: d(p, q) = arccos(|p . q|).
* Points and lines are dual: the polar of a point is the line whose normal is
  that point, and the pole of a line is the point its normal represents.  The
  duality is an involution, and it is what makes perpendiculars and poles two
  views of the same construction.
"""

from __future__ import annotations

import numpy as np

EPS = 1e-9
HALF_PI = np.pi / 2
ANGLE_RADIUS = 0.13  # how far from a vertex an angle mark is drawn, in radians


def clamp_to_disk(x: float, y: float) -> tuple[float, float]:
    """Snap a point outside the unit disk onto its boundary."""
    r = float(np.hypot(x, y))
    if r > 1.0:
        return x / r, y / r
    return float(x), float(y)


def lift(x: float, y: float) -> np.ndarray:
    """Disk point -> unit vector on the closed upper hemisphere."""
    z = np.sqrt(max(0.0, 1.0 - x * x - y * y))
    return np.array([x, y, z])


def upper(v: np.ndarray) -> np.ndarray:
    """The representative of an elliptic point on the closed upper hemisphere.

    Works on one vector or on a whole (N, 3) array of them.  Only a point
    definitely below the equator is turned over: on the equator itself both
    representatives are equally right, and a point that is there by a hair is
    left where the caller put it, so a curve ending on the rim is not torn in
    two by a z of -1e-17.
    """
    v = np.asarray(v, dtype=float)
    return np.where(v[..., 2:3] < -EPS, -v, v)


def project(v: np.ndarray) -> np.ndarray:
    """Unit vector -> the disk point representing its elliptic point."""
    return upper(v)[..., :2]


def antipode(xy) -> np.ndarray:
    """The boundary point identified with `xy` (only meaningful on |xy| = 1)."""
    return -np.asarray(xy, dtype=float)


def line_normal(p: np.ndarray, q: np.ndarray) -> np.ndarray | None:
    """Unit normal of the great circle through p and q.

    Returns None when p and q are the *same* elliptic point (equal or
    antipodal), in which case infinitely many lines pass through them.
    """
    n = np.cross(p, q)
    norm = float(np.linalg.norm(n))
    if norm < EPS:
        return None
    return n / norm


def plane_basis(n: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Orthonormal basis (e1, e2) of the plane orthogonal to unit vector n."""
    helper = np.array([0.0, 0.0, 1.0]) if abs(n[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(n, helper)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    return e1, e2


def is_boundary_line(n: np.ndarray) -> bool:
    """True when the line is the equator, drawn as the whole disk boundary."""
    return abs(abs(float(n[2])) - 1.0) < EPS


class Projection:
    """A way of drawing the hemisphere onto the closed unit disk.

    Both of the two below send the hemisphere onto the same disk and fix the
    rim, so the model, the picking and the elliptic geometry are untouched by
    the choice - only where a point of the sphere lands on the page.  Each also
    knows what a line looks like once drawn, which is what lets the export write
    real arcs instead of sampled chains:

    `conic(n)` gives the curve a line becomes, as (centre, major, minor) - the
    centre of an ellipse and its two semi-axes as vectors.  `point_conic(a, r)`
    does the same for the circle of everything r away from a point.  Either can
    be None, which means the image is straight and the caller should draw a
    segment through the two ends instead.

    `ray(v)` is the line of sight the projection works along, which is what the
    3-D view draws to show a point of the sphere being carried down to the disk.
    """

    name = ""
    summary = ""

    def project(self, v: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def lift(self, x: float, y: float) -> np.ndarray:
        raise NotImplementedError

    def conic(self, n):
        raise NotImplementedError

    def point_conic(self, a, radius):
        raise NotImplementedError

    def landing(self, v: np.ndarray) -> np.ndarray:
        """Where a point of the sphere lands, as a point of the plane z = 0."""
        x, y = self.project(np.asarray(v, dtype=float))
        return np.array([x, y, 0.0])

    def ray(self, v: np.ndarray) -> np.ndarray:
        """The two ends of the line of sight that carries v down to the disk."""
        raise NotImplementedError


class Orthogonal(Projection):
    """Straight down: drop the z coordinate.  A line becomes half an ellipse."""

    name = "orthogonal"
    summary = "seen straight down; a line is half an ellipse"

    def project(self, v):
        return upper(v)[..., :2]

    def lift(self, x, y):
        return lift(*clamp_to_disk(x, y))

    def conic(self, n):
        axes = line_ellipse(n)
        if axes is None:
            return None
        rim, minor = axes
        return np.zeros(2), rim, minor

    def point_conic(self, a, radius):
        return small_circle_ellipse(a, radius)

    def ray(self, v):
        """Straight down, so the sight line is the drop from the point itself."""
        return np.array([upper(v), self.landing(v)])


class Stereographic(Projection):
    """From the south pole: (x, y) / (1 + z).  A line becomes a circular arc.

    This is the conformal view - angles on the page are the angles of the
    geometry - bought at the price of distance no longer being the plain
    distance from the centre.
    """

    name = "stereographic"
    summary = "from the south pole; a line is a circular arc, angles are true"

    def project(self, v):
        v = upper(v)
        return v[..., :2] / (1.0 + v[..., 2:3])

    def lift(self, x, y):
        x, y = clamp_to_disk(x, y)
        squared = x * x + y * y
        return np.array([2.0 * x, 2.0 * y, 1.0 - squared]) / (1.0 + squared)

    def conic(self, n):
        """The plane n.x = 0 becomes |s|^2 - 2(n1 u + n2 v)/n3 - 1 = 0."""
        if abs(float(n[2])) < EPS:  # a great circle through the poles: a diameter
            return None
        centre = np.array([n[0], n[1]], dtype=float) / float(n[2])
        radius = 1.0 / abs(float(n[2]))
        return centre, np.array([radius, 0.0]), np.array([0.0, radius])

    def point_conic(self, a, radius):
        """Same working, for the plane a.x = cos(radius)."""
        cos_r, denominator = np.cos(radius), float(a[2]) + np.cos(radius)
        if abs(denominator) < EPS:  # the circle passes through the south pole
            return None
        centre = np.array([a[0], a[1]], dtype=float) / denominator
        size = float(np.sqrt(1.0 - cos_r * cos_r)) / abs(denominator)
        return centre, np.array([size, 0.0]), np.array([0.0, size])

    def ray(self, v):
        """The sight line starts at the south pole and runs on through the point."""
        return np.array([[0.0, 0.0, -1.0], self.landing(v)])


ORTHOGONAL = Orthogonal()
STEREOGRAPHIC = Stereographic()
PROJECTIONS = {p.name: p for p in (ORTHOGONAL, STEREOGRAPHIC)}


def line_arc(n: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, float]:
    """The line with normal n as one arc: basis (e1, e2) and a range of t.

    The point at parameter t is cos(t) e1 + sin(t) e2, and over [t0, t1] the
    whole of it lies on z >= 0.  Generically that is a half turn, which projects
    to half an ellipse; the equator (n = +-z_hat) is the whole turn.
    """
    e1, e2 = plane_basis(n)
    if is_boundary_line(n):
        return e1, e2, 0.0, 2.0 * np.pi
    # z(t) = cos(t) e1_z + sin(t) e2_z = R cos(t - phi), so z >= 0 exactly on
    # the half-turn centred at phi.
    phi = float(np.arctan2(e2[2], e1[2]))
    return e1, e2, phi - HALF_PI, phi + HALF_PI


def arc_vectors(e1: np.ndarray, e2: np.ndarray, t0: float, t1: float,
                samples: int = 512) -> np.ndarray:
    """An arc sampled into an (N, 3) array of points on the sphere."""
    t = np.linspace(t0, t1, samples)
    return np.cos(t)[:, None] * e1 + np.sin(t)[:, None] * e2


def arc_points(e1: np.ndarray, e2: np.ndarray, t0: float, t1: float,
               samples: int = 512) -> np.ndarray:
    """The same arc seen straight down, as an (N, 2) array of disk points."""
    return arc_vectors(e1, e2, t0, t1, samples)[:, :2]


def arc_end_vector(e1: np.ndarray, e2: np.ndarray, t: float) -> np.ndarray:
    """The point of the sphere an arc reaches at parameter t."""
    return np.cos(t) * e1 + np.sin(t) * e2


def arc_end(e1: np.ndarray, e2: np.ndarray, t: float) -> np.ndarray:
    """The disk point an arc reaches at parameter t, seen straight down."""
    return arc_end_vector(e1, e2, t)[:2]


def line_vectors(n: np.ndarray, samples: int = 512) -> np.ndarray:
    """The full elliptic line with normal n, sampled on the sphere."""
    return arc_vectors(*line_arc(n), samples)


def line_points(n: np.ndarray, samples: int = 512) -> np.ndarray:
    """The full elliptic line with normal n, as an (N, 2) array of disk points.

    Generically a half-ellipse joining two antipodal boundary points; the
    equator (n = +-z_hat) comes back as the whole boundary circle.
    """
    return line_vectors(n, samples)[:, :2]


def line_ellipse(n: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    """The ellipse a line projects to, as (rim end, minor axis end).

    The projection of a great circle is an ellipse about the centre of the disk
    with semi-major axis 1 - reaching the rim at the two points where the line
    crosses it - and semi-minor axis |n_z|.  The rim end returned is the one a
    counterclockwise half turn from which sweeps out the half that the model
    shows, so `drawellipsearc`-style commands need nothing else.

    None when there is no ellipse to speak of: the equator is the whole rim
    circle, and n_z = 0 gives a diameter, an ellipse squashed flat.
    """
    flat = float(np.hypot(n[0], n[1]))
    if is_boundary_line(n) or flat < EPS or abs(float(n[2])) < EPS:
        return None
    # the highest point of the great circle projects to -n_z (n_x, n_y) / flat,
    # which is the end of the minor axis on the half the disk shows
    minor = -np.sign(float(n[2])) * np.array([n[0], n[1]]) / flat
    rim = np.array([minor[1], -minor[0]])  # a quarter turn back, so ccw reaches `minor`
    return rim, abs(float(n[2])) * minor


def line_endpoints(n: np.ndarray) -> np.ndarray | None:
    """The pair of antipodal boundary points where the line meets the rim."""
    if is_boundary_line(n):
        return None
    d = np.array([-n[1], n[0]])  # in-plane and horizontal, hence on the equator
    d /= np.linalg.norm(d)
    return np.array([d, -d])


def distance(p: np.ndarray, q: np.ndarray) -> float:
    """Elliptic distance between two lifted points; at most pi/2."""
    return float(np.arccos(np.clip(abs(float(np.dot(p, q))), 0.0, 1.0)))


def segment_arcs(p: np.ndarray, q: np.ndarray) -> list[tuple[np.ndarray, np.ndarray, float, float]]:
    """Shortest elliptic segment from p to q, as one or two arcs.

    The segment is a single arc unless the shortest route leaves the disk
    through the rim and re-enters at the antipodal boundary point; the second
    arc is that re-entry, and it carries a negated basis, which is exactly what
    the fold back onto the upper hemisphere amounts to.  The cut is worked out
    from where z changes sign rather than from the samples, so the pieces do
    not depend on how finely they are drawn.
    """
    n = line_normal(p, q)
    if n is None:
        return []
    e1, e2 = plane_basis(n)
    t_p = float(np.arctan2(np.dot(p, e2), np.dot(p, e1)))
    t_q = float(np.arctan2(np.dot(q, e2), np.dot(q, e1)))

    delta = (t_q - t_p + np.pi) % (2.0 * np.pi) - np.pi  # in (-pi, pi]
    if abs(delta) > HALF_PI:  # antipodal representative of q is nearer
        delta -= np.sign(delta) * np.pi

    # z(t) = R cos(t - phi) vanishes a quarter turn either side of phi, and the
    # segment is short enough to meet at most one of those.
    phi = float(np.arctan2(e2[2], e1[2]))
    cuts = [t for t in (phi + HALF_PI, phi - HALF_PI, phi + 3.0 * HALF_PI, phi - 3.0 * HALF_PI)
            if 0.0 < (t - t_p) / delta < 1.0] if abs(delta) > EPS else []
    bounds = [t_p, *sorted(cuts, key=lambda t: (t - t_p) / delta), t_p + delta]

    arcs = []
    for start, end in zip(bounds, bounds[1:]):
        if abs(end - start) < EPS:
            continue
        middle = np.cos(0.5 * (start + end)) * e1 + np.sin(0.5 * (start + end)) * e2
        flip = -1.0 if middle[2] < 0.0 else 1.0  # fold this piece up if it dipped
        arcs.append((flip * e1, flip * e2, start, end))
    return arcs


def segment_vector_paths(p: np.ndarray, q: np.ndarray,
                         samples: int = 256) -> list[np.ndarray]:
    """Shortest elliptic segment from p to q, sampled on the sphere."""
    return [arc_vectors(*arc, samples) for arc in segment_arcs(p, q)]


def segment_paths(p: np.ndarray, q: np.ndarray, samples: int = 256) -> list[np.ndarray]:
    """Shortest elliptic segment from p to q, as one or two drawable paths."""
    return [path[:, :2] for path in segment_vector_paths(p, q, samples)]


def polar_point(n: np.ndarray) -> np.ndarray:
    """The pole of a line: the point at distance pi/2 from all of its points."""
    return project(n)


def pole_vector(n: np.ndarray) -> np.ndarray:
    """The pole of a line, as a lifted point rather than a disk point."""
    return upper(n)


def polar_normal(p: np.ndarray) -> np.ndarray | None:
    """Normal of the polar of a point: the point's own vector.

    Point and polar are dual - `pole_vector(polar_normal(p))` is p again - and
    the polar is exactly the set of points at distance pi/2 from p.
    """
    norm = float(np.linalg.norm(p))
    return None if norm < EPS else np.asarray(p, dtype=float) / norm


def meet_vector(n1: np.ndarray, n2: np.ndarray) -> np.ndarray | None:
    """The point where two lines cross, as a lifted vector.

    Never None for two distinct lines - in elliptic geometry there are no
    parallels - but the same line twice has no single meet.
    """
    v = np.cross(n1, n2)
    norm = float(np.linalg.norm(v))
    return None if norm < EPS else upper(v / norm)


def nearest_representative(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Whichever of +-b is the nearer end of the shortest arc from a."""
    return np.asarray(b, dtype=float) if float(np.dot(a, b)) >= 0.0 else -np.asarray(b, float)


def tangent(a: np.ndarray, b: np.ndarray) -> np.ndarray | None:
    """Unit tangent at a, pointing along the shortest arc towards b.

    None when b is the same elliptic point as a.  At exactly pi/2 the two
    representatives of b are equally near and the direction is only defined up
    to sign; the +b end is taken.
    """
    b = nearest_representative(a, b)
    t = b - float(np.dot(a, b)) * np.asarray(a, dtype=float)
    norm = float(np.linalg.norm(t))
    return None if norm < EPS else t / norm


def arc_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float | None:
    """The angle at a between the shortest arcs a->b and a->c, in [0, pi]."""
    t1, t2 = tangent(a, b), tangent(a, c)
    if t1 is None or t2 is None:
        return None
    return float(np.arccos(np.clip(float(np.dot(t1, t2)), -1.0, 1.0)))


def triangle_angles(a: np.ndarray, b: np.ndarray,
                    c: np.ndarray) -> tuple[float, float, float] | None:
    """The three interior angles, or None if two vertices coincide."""
    angles = (arc_angle(a, b, c), arc_angle(b, c, a), arc_angle(c, a, b))
    return None if any(x is None for x in angles) else angles


def bounds_a_disk(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> bool:
    """Whether the three shortest sides close up into an ordinary triangle.

    Each side lifts to the sphere by taking the nearer representative of its far
    end, and walking the three of them lands back on a or on -a according to the
    sign of (a.b)(b.c)(c.a).  When it lands on -a the loop is a closed curve in
    the elliptic plane that no disk fills - it runs out through the rim and back
    in on the other side - and Girard's formula does not apply to it.
    """
    return float(np.dot(a, b)) * float(np.dot(b, c)) * float(np.dot(c, a)) >= 0.0


def triangle_area(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float | None:
    """Girard: the area of a triangle is how much its angles beat pi by.

    None when the vertices do not bound a disk, or two of them coincide.
    """
    angles = triangle_angles(a, b, c)
    if angles is None or not bounds_a_disk(a, b, c):
        return None
    return float(sum(angles) - np.pi)


def triangle_centre(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray | None:
    """A point inside the triangle, for hanging a label on."""
    total = (np.asarray(a, dtype=float) + nearest_representative(a, b)
             + nearest_representative(a, c))
    norm = float(np.linalg.norm(total))
    return None if norm < EPS else upper(total / norm)


def small_circle_ellipse(a: np.ndarray, radius: float
                         ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Everything at distance `radius` from a point, projected into the disk.

    That set is a circle on the sphere - a plane section - and the orthogonal
    projection of a circle is an ellipse, off-centre unless a is the pole of the
    disk.  Returned as (centre, major, minor): the centre of the ellipse and its
    two semi-axes as vectors, which is all a drawing command needs.
    """
    e1, e2 = plane_basis(a)
    centre = np.cos(radius) * np.asarray(a, dtype=float)[:2]
    # the unit circle in the tangent plane, seen from above
    spread = np.sin(radius) * np.column_stack([e1[:2], e2[:2]])
    directions, lengths, _ = np.linalg.svd(spread)  # the principal axes
    return centre, directions[:, 0] * lengths[0], directions[:, 1] * lengths[1]


def angle_arc(a: np.ndarray, b: np.ndarray, c: np.ndarray,
              radius: float = ANGLE_RADIUS, samples: int = 24) -> np.ndarray | None:
    """The little arc marking the angle at a, drawn on the sphere and projected.

    Given as points of the sphere for the caller to project; like
    `right_angle_marker` it is dropped near the rim, where it would tear.
    """
    t1, t2 = tangent(a, b), tangent(a, c)
    if t1 is None or t2 is None:
        return None
    theta = float(np.arccos(np.clip(float(np.dot(t1, t2)), -1.0, 1.0)))
    if theta < EPS:
        return None
    perp = t2 - float(np.dot(t1, t2)) * t1
    norm = float(np.linalg.norm(perp))
    if norm < EPS:  # a straight angle: no plane to swing the arc through
        return None
    perp /= norm

    s = np.linspace(0.0, theta, samples)
    directions = np.cos(s)[:, None] * t1 + np.sin(s)[:, None] * perp
    pts = np.cos(radius) * np.asarray(a, dtype=float) + np.sin(radius) * directions
    if np.any(pts[:, 2] < -EPS):  # the arc would straddle the rim
        return None
    return pts


def perpendicular_normal(p: np.ndarray, n: np.ndarray) -> np.ndarray | None:
    """Normal of the perpendicular dropped from point p onto the line n.

    Any line through the pole of n meets n at a right angle, so the
    perpendicular is simply the join of p and that pole - which is why it is
    unique unless p *is* the pole, where every line through p is perpendicular.
    """
    m = np.cross(p, n)
    norm = float(np.linalg.norm(m))
    if norm < EPS:
        return None
    return m / norm


def foot_of_perpendicular(p: np.ndarray, n: np.ndarray) -> np.ndarray | None:
    """Where that perpendicular meets the line: the point of n nearest to p."""
    m = perpendicular_normal(p, n)
    if m is None:
        return None
    foot = np.cross(n, m)
    return upper(foot / np.linalg.norm(foot))


def distance_to_line(p: np.ndarray, n: np.ndarray) -> float:
    """Distance from a point to a line: pi/2 less the distance to its pole."""
    return float(np.arcsin(np.clip(abs(float(np.dot(p, n))), 0.0, 1.0)))


def right_angle_marker(foot: np.ndarray, n1: np.ndarray, n2: np.ndarray,
                       size: float = 0.09) -> np.ndarray | None:
    """A small square on the sphere at the foot, as three points of the sphere.

    Seen straight down this comes out as a slanted parallelogram everywhere
    except the centre - the drawing is honest about the distortion rather than
    faking a square corner, and under the conformal projection it squares up by
    itself. None near the rim, where the square would straddle the boundary and
    tear.
    """
    t1 = np.cross(n1, foot)
    t2 = np.cross(n2, foot)
    if np.linalg.norm(t1) < EPS or np.linalg.norm(t2) < EPS:
        return None
    t1 /= np.linalg.norm(t1)
    t2 /= np.linalg.norm(t2)

    corners = [foot + size * t1, foot + size * (t1 + t2), foot + size * t2]
    xy = []
    for corner in corners:
        corner = corner / np.linalg.norm(corner)
        if np.dot(corner, foot) < 0:
            corner = -corner
        if corner[2] < -EPS:  # crossed the equator: the marker would tear
            return None
        xy.append(corner)
    return np.array(xy)
