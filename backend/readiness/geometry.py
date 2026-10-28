"""Explicit CPU planar registration and conservative footprint rasterization.

Measured points are required. SAM masks do not supply drawing coordinates.
Synthetic points verify this implementation, never the real camera geometry.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np

from .checks import Footprint, Frame


@dataclass(frozen=True)
class Correspondence:
    plane_mm: tuple[float, float]
    image_px: tuple[float, float]


@dataclass(frozen=True)
class Registration:
    matrix: tuple[tuple[float, ...], ...]
    camera: str
    rig: str
    surface_pose: str
    source_frame_sha256: str
    max_validation_error_px: float
    validated: bool
    support_plane_mm: tuple[tuple[float, float], ...]


def _hull(points):
    points = sorted(set(tuple(p) for p in points))
    def cross(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
    lower, upper = [], []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return tuple(lower[:-1] + upper[:-1])


def _within_support(points, support):
    for i, start in enumerate(support):
        end = support[(i+1) % len(support)]
        for point in points:
            if ((end[0]-start[0])*(point[1]-start[1]) - (end[1]-start[1])*(point[0]-start[0])) < -1e-8:
                return False
    return len(support) >= 3


def _normalise(points):
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all():
        raise ValueError('Coordinates must be finite 2D points')
    centre = points.mean(axis=0)
    shifted = points - centre
    if np.linalg.matrix_rank(shifted) < 2:
        raise ValueError('Correspondences must span the plane')
    distance = np.sqrt((shifted ** 2).sum(axis=1)).mean()
    scale = math.sqrt(2) / distance
    matrix = np.array([[scale, 0, -scale*centre[0]], [0, scale, -scale*centre[1]], [0, 0, 1]])
    return shifted*scale, matrix


def project(matrix, points):
    p = np.asarray(points, dtype=float)
    if p.ndim != 2 or p.shape[1] != 2 or not np.isfinite(p).all():
        raise ValueError('Invalid projection coordinates')
    out = np.column_stack((p, np.ones(len(p)))) @ np.asarray(matrix).T
    if not np.isfinite(out).all() or np.any(np.abs(out[:, 2]) < 1e-9) or not (np.all(out[:, 2] > 0) or np.all(out[:, 2] < 0)):
        raise ValueError('Projection crosses the homography horizon')
    return out[:, :2] / out[:, 2, None]


def fit_registration(fit, validation, *, camera, rig, surface_pose, source_frame_sha256,
                     max_error_px=2.0):
    if len(fit) < 4 or len(validation) < 4:
        raise ValueError('Require at least four fitting and four independent validation points')
    if not all((camera, rig, surface_pose, source_frame_sha256)) or not math.isfinite(max_error_px) or not 0 < max_error_px <= 2:
        raise ValueError('Registration needs identity and a positive tolerance no greater than 2px')
    fit_plane = [p.plane_mm for p in fit]
    held_plane = [p.plane_mm for p in validation]
    if len(set(fit_plane + held_plane)) != len(fit_plane + held_plane):
        raise ValueError('Fitting and validation points must be distinct')
    a, ta = _normalise(fit_plane)
    b, tb = _normalise([p.image_px for p in fit])
    _normalise(held_plane)
    _normalise([p.image_px for p in validation])
    rows = []
    for (x, y), (u, v) in zip(a, b):
        rows.extend(([-x, -y, -1, 0, 0, 0, u*x, u*y, u], [0, 0, 0, -x, -y, -1, v*x, v*y, v]))
    rows = np.asarray(rows)
    if np.linalg.matrix_rank(rows) < 8:
        raise ValueError('Degenerate registration')
    _, _, vt = np.linalg.svd(rows, full_matrices=True)
    h = np.linalg.inv(tb) @ vt[-1].reshape(3, 3) @ ta
    h /= np.linalg.norm(h)
    if not np.isfinite(h).all() or abs(np.linalg.det(h)) < 1e-12:
        raise ValueError('Singular registration')
    error = np.linalg.norm(project(h, held_plane) - np.asarray([p.image_px for p in validation]), axis=1)
    worst = float(error.max())
    if worst > max_error_px:
        raise ValueError('Independent registration validation exceeds tolerance')
    return Registration(tuple(tuple(float(v) for v in row) for row in h), camera, rig, surface_pose,
                        source_frame_sha256, worst, True, _hull(fit_plane))


def _convex(vertices):
    p = np.asarray(vertices, dtype=float)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 3 or not np.isfinite(p).all():
        raise ValueError('Footprint must be a finite convex polygon')
    # Consistent turn alone does not exclude star polygons: every other vertex
    # must also lie on the interior side of every edge.
    area = sum(p[i, 0]*p[(i+1)%len(p), 1] - p[(i+1)%len(p), 0]*p[i, 1] for i in range(len(p)))
    if abs(area) < 1e-9:
        raise ValueError('Degenerate footprint')
    if area < 0:
        p = p[::-1]
    for i, start in enumerate(p):
        edge = p[(i+1)%len(p)] - start
        if np.linalg.norm(edge) < 1e-9:
            raise ValueError('Duplicate footprint vertex')
        offsets = p - start
        if np.any(edge[0]*offsets[:, 1] - edge[1]*offsets[:, 0] < -1e-8):
            raise ValueError('Footprint must be convex and non-self-intersecting')
    return p


def _expand(vertices, margin):
    p = _convex(vertices)
    normals, offsets = [], []
    for i, a in enumerate(p):
        e = p[(i+1)%len(p)] - a
        n = np.array([e[1], -e[0]]) / np.linalg.norm(e)
        normals.append(n)
        offsets.append(float(n @ a) + margin)
    out = []
    for i in range(len(p)):
        try:
            out.append(np.linalg.solve(np.array([normals[i-1], normals[i]]), [offsets[i-1], offsets[i]]))
        except np.linalg.LinAlgError:
            raise ValueError('Collinear footprint edges') from None
    return _convex(out)


def _touches_cell(polygon, x, y):
    square = np.array([[x, y], [x+1, y], [x+1, y+1], [x, y+1]])
    edges = np.roll(polygon, -1, axis=0) - polygon
    axes = [np.array([1., 0.]), np.array([0., 1.])] + [np.array([-e[1], e[0]]) for e in edges]
    for axis in axes:
        a, b = polygon @ axis, square @ axis
        if a.max() < b.min() - 1e-9 or b.max() < a.min() - 1e-9:
            return False
    return True


def rasterize_footprint(frame: Frame, registration: Registration, vertices_mm, *, margin_mm=2.0, required_margin_mm=2.0):
    if (not registration.validated or not registration.source_frame_sha256
            or (registration.camera, registration.rig, registration.surface_pose) != (frame.camera, frame.rig, frame.surface_pose)):
        raise ValueError('Registration does not belong to this camera, rig and surface pose')
    if not all(math.isfinite(v) and v >= 0 for v in (margin_mm, required_margin_mm)) or margin_mm < required_margin_mm:
        raise ValueError('Invalid footprint margin')
    expanded = _expand(vertices_mm, margin_mm)
    if not _within_support(expanded, registration.support_plane_mm):
        raise ValueError('Footprint extends beyond the measured registration support')
    polygon = _convex(project(registration.matrix, expanded))
    low = np.floor(polygon.min(axis=0)).astype(int) - 1
    high = np.ceil(polygon.max(axis=0)).astype(int)
    if low[0] < 0 or low[1] < 0 or high[0] >= frame.width or high[1] >= frame.height:
        raise ValueError('Footprint, including conservative boundary cells, is not entirely visible')
    if (high[0]-low[0]+1)*(high[1]-low[1]+1) > 2_000_000:
        raise ValueError('Footprint rasterization exceeds the offline cell limit')
    cells = frozenset((x, y) for y in range(low[1], high[1]+1) for x in range(low[0], high[0]+1)
                      if _touches_cell(polygon, x, y))
    return Footprint(frame.sha256, frame.camera, frame.rig, frame.surface_pose, cells, True, margin_mm, required_margin_mm)
