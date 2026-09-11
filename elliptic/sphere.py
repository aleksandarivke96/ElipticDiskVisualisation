"""Camera and geometry shared by the sphere canvas and its vector export."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import geometry as geo

COL_WIRE = "#9aa4b4"
COL_EQUATOR = "#3f4756"
COL_PLATE = "#6f7c90"
COL_RAY = "#8a93a3"
COL_PAPER = "#ffffff"
COL_HINT = "#98a0ac"

MARGIN = 1.28
BACK = 0.30
PLATE = 0.32
HOME = (np.radians(-62.0), np.radians(35.0), 1.0)


@dataclass
class SphereView:
    """The current sphere camera; angles are in radians."""

    azimuth: float = HOME[0]
    elevation: float = HOME[1]
    zoom: float = HOME[2]


def camera(azimuth: float, elevation: float):
    """Right, up and towards-the-camera unit vectors of an orthographic camera."""
    ce, se = np.cos(elevation), np.sin(elevation)
    towards = np.array([ce * np.cos(azimuth), ce * np.sin(azimuth), se])
    right = np.cross([0.0, 0.0, 1.0], towards)
    length = float(np.linalg.norm(right))
    right = np.array([1.0, 0.0, 0.0]) if length < 1e-9 else right / length
    return right, np.cross(towards, right), towards


def split_at_silhouette(points: np.ndarray, towards: np.ndarray):
    """Cut a curve at the camera silhouette into (piece, in front) pairs."""
    points = np.asarray(points, dtype=float)
    if len(points) == 0:
        return []
    depth = points @ towards
    pieces, run, front = [], [points[0]], bool(depth[0] >= 0)
    for i in range(1, len(points)):
        if (depth[i] >= 0) == front:
            run.append(points[i])
            continue
        gap = depth[i - 1] - depth[i]
        t = 0.0 if abs(gap) < 1e-15 else depth[i - 1] / gap
        edge = points[i - 1] + t * (points[i] - points[i - 1])
        run.append(edge)
        pieces.append((np.array(run), front))
        run, front = [edge, points[i]], not front
    pieces.append((np.array(run), front))
    return [(piece, is_front) for piece, is_front in pieces if len(piece) > 1]


def great_circle(normal, samples: int = 180) -> np.ndarray:
    e1, e2 = geo.plane_basis(np.asarray(normal, dtype=float))
    t = np.linspace(0.0, 2.0 * np.pi, samples)
    return np.cos(t)[:, None] * e1 + np.sin(t)[:, None] * e2


def parallel(height: float, samples: int = 120) -> np.ndarray:
    r = float(np.sqrt(max(0.0, 1.0 - height * height)))
    t = np.linspace(0.0, 2.0 * np.pi, samples)
    return np.column_stack([r * np.cos(t), r * np.sin(t), np.full_like(t, height)])


def cap_outline(elevation: float, samples: int = 121) -> np.ndarray:
    """Upper hemisphere outline in camera coordinates, including views below it.

    A sight line through (X, Y) reaches the upper hemisphere exactly when
    Y >= -sin(elevation) * sqrt(1 - X**2). Its outline joins the top half of
    the silhouette circle to the appropriate half of the projected equator.
    """
    t = np.linspace(0.0, np.pi, samples)
    top = np.column_stack([np.cos(t), np.sin(t)])
    bottom = np.column_stack([np.cos(t[::-1]), -np.sin(elevation) * np.sin(t[::-1])])
    return np.vstack([top, bottom])
