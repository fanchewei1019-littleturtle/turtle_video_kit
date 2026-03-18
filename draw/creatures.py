# -*- coding: utf-8 -*-
"""
Creatures — programmatically drawn animals using PIL bezier curves and ellipses.
No external image files needed. Each creature can be animated (walk, blink, bounce).
"""
from __future__ import annotations
import math
from typing import Tuple, Optional

from PIL import Image, ImageDraw

from ..core.canvas import Layer
from ..core.keyframe import interpolate


# ── Drawing utilities ─────────────────────────────────────────────────────────

def _bezier(p0, p1, p2, t):
    """Quadratic bezier point."""
    return (
        (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0],
        (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1],
    )

def _bezier_points(p0, p1, p2, n=20):
    return [_bezier(p0, p1, p2, i / n) for i in range(n + 1)]


# ── Turtle ────────────────────────────────────────────────────────────────────

class Turtle(Layer):
    """
    A cute programmatic turtle. Can walk, blink, and bounce.

    Args:
        x, y:       center position
        scale:      overall size multiplier (1.0 = ~100px wide)
        walk_cycle: if True, legs animate with time
        direction:  "right" or "left"
    """
    z_index = 20

    SHELL_COLOR   = (80, 140, 80)
    SHELL_PATTERN = (60, 110, 60)
    BODY_COLOR    = (120, 180, 100)
    EYE_WHITE     = (240, 240, 240)
    EYE_PUPIL     = (40, 40, 40)
    MOUTH_COLOR   = (60, 100, 60)

    def __init__(self, x: float = 200, y: float = 400,
                 scale: float = 1.0,
                 walk_cycle: bool = True,
                 direction: str = "right",
                 t_start: float = 0.0, t_end: Optional[float] = None):
        self.x = x
        self.y = y
        self.scale = scale
        self.walk_cycle = walk_cycle
        self.direction = direction
        self.t_start = t_start
        self.t_end = t_end

    def is_active(self, frame_index, fps):
        t = frame_index / fps
        if t < self.t_start:
            return False
        if self.t_end is not None and t > self.t_end:
            return False
        return True

    def _draw(self, img: Image.Image, t: float):
        d = ImageDraw.Draw(img)
        s = self.scale
        cx, cy = self.x, self.y

        # Walk bob
        bob = math.sin(t * 6) * 3 * s if self.walk_cycle else 0
        cy += bob

        # ── Legs ──────────────────────────────────────────────────────────
        leg_swing = math.sin(t * 6) * 12 * s if self.walk_cycle else 0
        leg_positions = [
            (cx - 28 * s, cy + 20 * s, leg_swing),
            (cx + 28 * s, cy + 20 * s, -leg_swing),
            (cx - 20 * s, cy + 30 * s, -leg_swing),
            (cx + 20 * s, cy + 30 * s, leg_swing),
        ]
        for lx, ly, swing in leg_positions:
            pts = _bezier_points(
                (lx, ly), (lx + swing, ly + 10 * s), (lx + swing * 0.5, ly + 22 * s)
            )
            if len(pts) > 1:
                d.line(pts, fill=self.BODY_COLOR, width=max(1, int(7 * s)))
            # Foot
            d.ellipse([lx + swing * 0.5 - 7 * s, ly + 22 * s - 4 * s,
                       lx + swing * 0.5 + 7 * s, ly + 22 * s + 4 * s],
                      fill=self.BODY_COLOR)

        # ── Body ──────────────────────────────────────────────────────────
        bw, bh = 60 * s, 38 * s
        d.ellipse([cx - bw, cy - bh * 0.5, cx + bw, cy + bh * 0.5],
                  fill=self.BODY_COLOR)

        # ── Shell ─────────────────────────────────────────────────────────
        sw, sh = 52 * s, 42 * s
        d.ellipse([cx - sw, cy - sh, cx + sw, cy + sh * 0.3],
                  fill=self.SHELL_COLOR)

        # Shell pattern (hexagon-ish segments)
        for dr, dt in [(0, 0), (-18 * s, -8 * s), (18 * s, -8 * s),
                       (0, -18 * s), (-22 * s, -20 * s), (22 * s, -20 * s)]:
            r = 10 * s
            d.ellipse([cx + dr - r, cy + dt - r * 0.7,
                       cx + dr + r, cy + dt + r * 0.7],
                      outline=self.SHELL_PATTERN,
                      width=max(1, int(2 * s)))

        # Shell outline
        d.ellipse([cx - sw, cy - sh, cx + sw, cy + sh * 0.3],
                  outline=self.SHELL_PATTERN, width=max(1, int(3 * s)))

        # ── Head ──────────────────────────────────────────────────────────
        head_dir = 1 if self.direction == "right" else -1
        hx = cx + 50 * s * head_dir
        hy = cy - 15 * s
        hr = 20 * s
        d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr],
                  fill=self.BODY_COLOR)

        # Neck connection
        d.ellipse([cx + 30 * s * head_dir - 12 * s, cy - 18 * s,
                   cx + 30 * s * head_dir + 12 * s, cy - 5 * s],
                  fill=self.BODY_COLOR)

        # ── Eyes ──────────────────────────────────────────────────────────
        blink = abs(math.sin(t * 0.7)) > 0.97
        ex = hx + 6 * s * head_dir
        ey = hy - 5 * s
        er = 6 * s
        if blink:
            d.line([ex - er, ey, ex + er, ey], fill=self.EYE_PUPIL,
                   width=max(1, int(3 * s)))
        else:
            d.ellipse([ex - er, ey - er, ex + er, ey + er], fill=self.EYE_WHITE)
            d.ellipse([ex - er * 0.5 + 1 * s * head_dir, ey - er * 0.5,
                       ex + er * 0.5 + 1 * s * head_dir, ey + er * 0.5],
                      fill=self.EYE_PUPIL)

        # ── Smile ─────────────────────────────────────────────────────────
        mx = hx - 4 * s * head_dir
        my = hy + 8 * s
        pts = _bezier_points((mx - 8 * s, my), (mx, my + 6 * s), (mx + 8 * s, my))
        if len(pts) > 1:
            d.line(pts, fill=self.MOUTH_COLOR, width=max(1, int(2 * s)))

        # ── Tail ──────────────────────────────────────────────────────────
        tail_dir = -head_dir
        tx = cx + 45 * s * tail_dir
        pts = _bezier_points(
            (cx + 30 * s * tail_dir, cy + 5 * s),
            (cx + 45 * s * tail_dir, cy - 5 * s),
            (tx, cy - 15 * s)
        )
        if len(pts) > 1:
            d.line(pts, fill=self.BODY_COLOR, width=max(1, int(5 * s)))

    def render_frame(self, frame_index, fps, canvas_size):
        t = frame_index / fps
        img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        self._draw(img, t)
        return img


# ── Dog ───────────────────────────────────────────────────────────────────────

class Dog(Layer):
    """A simple programmatic dog."""
    z_index = 20

    FUR   = (200, 150, 100)
    DARK  = (140, 90, 50)
    NOSE  = (50, 30, 30)
    EYE   = (40, 30, 20)
    WHITE = (240, 235, 225)

    def __init__(self, x: float = 300, y: float = 400, scale: float = 1.0,
                 wag: bool = True,
                 t_start: float = 0.0, t_end: Optional[float] = None):
        self.x = x
        self.y = y
        self.scale = scale
        self.wag = wag
        self.t_start = t_start
        self.t_end = t_end

    def is_active(self, frame_index, fps):
        t = frame_index / fps
        if t < self.t_start:
            return False
        if self.t_end is not None and t > self.t_end:
            return False
        return True

    def _draw(self, img, t):
        d = ImageDraw.Draw(img)
        s = self.scale
        cx, cy = self.x, self.y

        # Body
        d.ellipse([cx - 40 * s, cy - 20 * s, cx + 40 * s, cy + 25 * s],
                  fill=self.FUR)

        # Legs
        for lx in [-25 * s, -10 * s, 10 * s, 25 * s]:
            d.rectangle([cx + lx - 5 * s, cy + 20 * s, cx + lx + 5 * s, cy + 45 * s],
                        fill=self.FUR)

        # Head
        hx, hy = cx + 42 * s, cy - 15 * s
        d.ellipse([hx - 22 * s, hy - 20 * s, hx + 22 * s, hy + 20 * s],
                  fill=self.FUR)

        # Floppy ears
        for ex, ew in [(-1, -20 * s), (1, 12 * s)]:
            d.ellipse([hx + ew - 12 * s, hy - 25 * s, hx + ew + 6 * s, hy + 8 * s],
                      fill=self.DARK)

        # Snout
        d.ellipse([hx + 8 * s, hy - 5 * s, hx + 22 * s, hy + 10 * s],
                  fill=self.WHITE)
        d.ellipse([hx + 12 * s, hy - 2 * s, hx + 18 * s, hy + 4 * s],
                  fill=self.NOSE)

        # Eyes
        for ey_offset in [-8 * s, 4 * s]:
            d.ellipse([hx + ey_offset, hy - 12 * s,
                       hx + ey_offset + 8 * s, hy - 4 * s],
                      fill=self.EYE)

        # Tail (wag)
        wag_angle = math.sin(t * 8) * 30 if self.wag else 0
        tx = cx - 42 * s
        ty = cy - 5 * s
        tail_end_x = tx - 20 * s * math.cos(math.radians(wag_angle))
        tail_end_y = ty - 20 * s - 15 * s * math.sin(math.radians(wag_angle))
        pts = _bezier_points((tx, ty), (tx - 10 * s, ty - 10 * s),
                             (tail_end_x, tail_end_y))
        if len(pts) > 1:
            d.line(pts, fill=self.FUR, width=max(1, int(8 * s)))

    def render_frame(self, frame_index, fps, canvas_size):
        t = frame_index / fps
        img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        self._draw(img, t)
        return img


# ── Bird ──────────────────────────────────────────────────────────────────────

class Bird(Layer):
    """A small flying bird — flaps its wings."""
    z_index = 20

    def __init__(self, x: float = 400, y: float = 200, scale: float = 1.0,
                 color: Tuple[int, int, int] = (80, 120, 200),
                 flap_speed: float = 3.0,
                 t_start: float = 0.0, t_end: Optional[float] = None):
        self.x = x
        self.y = y
        self.scale = scale
        self.color = color
        self.flap_speed = flap_speed
        self.t_start = t_start
        self.t_end = t_end

    def is_active(self, frame_index, fps):
        t = frame_index / fps
        if t < self.t_start:
            return False
        if self.t_end is not None and t > self.t_end:
            return False
        return True

    def _draw(self, img, t):
        d = ImageDraw.Draw(img)
        s = self.scale
        cx, cy = self.x, self.y

        flap = math.sin(t * self.flap_speed * 2 * math.pi) * 18 * s

        # Wings
        for side in [-1, 1]:
            wx = cx + side * 25 * s
            wy = cy + flap * side * 0.5
            pts = _bezier_points((cx, cy), (wx, wy - 10 * s), (wx + side * 10 * s, cy + 5 * s))
            if len(pts) > 1:
                d.line(pts, fill=self.color, width=max(1, int(10 * s)))

        # Body
        d.ellipse([cx - 12 * s, cy - 8 * s, cx + 12 * s, cy + 8 * s],
                  fill=self.color)

        # Head
        d.ellipse([cx + 8 * s, cy - 14 * s, cx + 22 * s, cy + 2 * s],
                  fill=self.color)

        # Beak
        d.polygon([(cx + 22 * s, cy - 8 * s),
                   (cx + 30 * s, cy - 5 * s),
                   (cx + 22 * s, cy - 2 * s)],
                  fill=(255, 180, 50))

        # Eye
        d.ellipse([cx + 14 * s, cy - 12 * s, cx + 18 * s, cy - 8 * s],
                  fill=(240, 240, 240))
        d.ellipse([cx + 15 * s, cy - 11 * s, cx + 17 * s, cy - 9 * s],
                  fill=(30, 30, 30))

        # Tail
        pts = _bezier_points((cx - 10 * s, cy), (cx - 20 * s, cy - 5 * s),
                             (cx - 28 * s, cy + 5 * s))
        if len(pts) > 1:
            d.line(pts, fill=self.color, width=max(1, int(6 * s)))

    def render_frame(self, frame_index, fps, canvas_size):
        t = frame_index / fps
        img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        self._draw(img, t)
        return img
