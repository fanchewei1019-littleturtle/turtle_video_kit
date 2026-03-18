# -*- coding: utf-8 -*-
"""
Morph — smooth shape-to-shape interpolation.
Uses polygon vertex interpolation so any closed shape can morph into any other.
"""
from __future__ import annotations
import math
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageDraw

from ..core.canvas import Layer
from ..core.keyframe import interpolate, EASINGS


# ── Polygon utilities ─────────────────────────────────────────────────────────

def circle_polygon(cx: float, cy: float, r: float, n: int = 64) -> List[Tuple[float, float]]:
    """Approximate a circle as an n-gon."""
    return [
        (cx + r * math.cos(2 * math.pi * i / n),
         cy + r * math.sin(2 * math.pi * i / n))
        for i in range(n)
    ]

def rect_polygon(cx: float, cy: float, w: float, h: float,
                 n: int = 64) -> List[Tuple[float, float]]:
    """Rectangle as n evenly-spaced points along its perimeter."""
    hw, hh = w / 2, h / 2
    perimeter = 2 * (w + h)
    pts = []
    for i in range(n):
        d = (i / n) * perimeter
        if d < w:
            pts.append((cx - hw + d, cy - hh))
        elif d < w + h:
            pts.append((cx + hw, cy - hh + (d - w)))
        elif d < 2 * w + h:
            pts.append((cx + hw - (d - w - h), cy + hh))
        else:
            pts.append((cx - hw, cy + hh - (d - 2 * w - h)))
    return pts

def star_polygon(cx: float, cy: float, r_outer: float, r_inner: float,
                 points: int = 5, n: int = 64) -> List[Tuple[float, float]]:
    """Star shape as n-gon."""
    pts = []
    for i in range(n):
        angle = 2 * math.pi * i / n - math.pi / 2
        spike = i % (n // points) < (n // points // 2)
        r = r_outer if spike else r_inner
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts

def triangle_polygon(cx: float, cy: float, r: float,
                     n: int = 64) -> List[Tuple[float, float]]:
    return circle_polygon(cx, cy, r, 3) if n == 3 else _resample(
        circle_polygon(cx, cy, r, 3), n
    )

def _resample(poly: List[Tuple], n: int) -> List[Tuple[float, float]]:
    """Resample a polygon to exactly n points by linear interpolation along edges."""
    pts = np.array(poly, dtype=float)
    # Compute cumulative edge lengths
    diffs = np.diff(np.vstack([pts, pts[0:1]]), axis=0)
    lengths = np.sqrt((diffs ** 2).sum(axis=1))
    cumlen = np.concatenate([[0], np.cumsum(lengths)])
    total = cumlen[-1]
    targets = np.linspace(0, total, n, endpoint=False)
    result = []
    for t in targets:
        idx = np.searchsorted(cumlen, t, side="right") - 1
        idx = min(idx, len(pts) - 1)
        seg_len = lengths[idx] if idx < len(lengths) else 1e-9
        local_t = (t - cumlen[idx]) / max(seg_len, 1e-9)
        p0 = pts[idx]
        p1 = pts[(idx + 1) % len(pts)]
        result.append(tuple(p0 + local_t * (p1 - p0)))
    return result


# ── ShapeMorph Layer ──────────────────────────────────────────────────────────

class ShapeMorph(Layer):
    """
    Morphs from one polygon shape to another over time.

    Both shapes must be defined as polygon vertex lists (use the helpers above).
    The number of vertices is automatically resampled to match.

    Example:
        circle_pts = circle_polygon(640, 360, 100)
        square_pts = rect_polygon(640, 360, 200, 200)
        morph = ShapeMorph(circle_pts, square_pts,
                           t_start=1.0, t_end=2.5,
                           fill=(255, 215, 0), easing="ease_in_out")
    """
    z_index = 10

    def __init__(self,
                 shape_from: List[Tuple[float, float]],
                 shape_to: List[Tuple[float, float]],
                 t_start: float, t_end: float,
                 fill: Tuple[int, int, int] = (255, 215, 0),
                 outline: Tuple[int, int, int] = None,
                 outline_width: int = 3,
                 easing: str = "ease_in_out",
                 n_points: int = 64):
        self.t_start = t_start
        self.t_end = t_end
        self.fill = fill
        self.outline = outline
        self.outline_width = outline_width
        self.easing = easing
        # Resample both shapes to n_points
        self._from = np.array(_resample(shape_from, n_points), dtype=float)
        self._to   = np.array(_resample(shape_to,   n_points), dtype=float)

    def is_active(self, frame_index, fps):
        return True  # Always visible (holds end shape after t_end)

    def render_frame(self, frame_index, fps, canvas_size):
        t = frame_index / fps
        easing_fn = EASINGS.get(self.easing, EASINGS["linear"])
        raw = (t - self.t_start) / max(self.t_end - self.t_start, 1e-9)
        alpha_t = easing_fn(max(0.0, min(1.0, raw)))

        pts = self._from + alpha_t * (self._to - self._from)
        poly = [tuple(p) for p in pts]

        img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.polygon(poly, fill=(*self.fill, 255),
                  outline=(*self.outline, 255) if self.outline else None)
        return img


# ── ColorMorph Layer ──────────────────────────────────────────────────────────

class ColorMorph(Layer):
    """Morphs the background color of the whole canvas."""
    z_index = 0

    def __init__(self, color_from: Tuple[int, int, int],
                 color_to: Tuple[int, int, int],
                 t_start: float, t_end: float,
                 easing: str = "ease_in_out"):
        self.color_from = color_from
        self.color_to = color_to
        self.t_start = t_start
        self.t_end = t_end
        self.easing = easing

    def is_active(self, frame_index, fps):
        return True

    def render_frame(self, frame_index, fps, canvas_size):
        t = frame_index / fps
        color = interpolate(self.color_from, self.color_to,
                            self.t_start, self.t_end, t, self.easing)
        img = Image.new("RGBA", canvas_size, (*color, 255))
        return img
