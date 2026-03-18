# -*- coding: utf-8 -*-
"""
Transitions — overlay layers that handle scene-level fades, wipes, and zooms.
Each transition is a Layer subclass you add to a Canvas.
"""
from __future__ import annotations
from PIL import Image, ImageDraw
from typing import Tuple

from ..core.canvas import Layer
from ..core.keyframe import interpolate, alpha_at


# ── Fade ──────────────────────────────────────────────────────────────────────

class FadeIn(Layer):
    """Black-to-transparent fade at the start of a scene."""
    z_index = 900

    def __init__(self, t_start: float = 0.0, t_end: float = 0.5,
                 color: Tuple[int, int, int] = (0, 0, 0), easing: str = "ease_out"):
        self.t_start = t_start
        self.t_end = t_end
        self.color = color
        self.easing = easing

    def is_active(self, frame_index, fps):
        return frame_index / fps <= self.t_end

    def render_frame(self, frame_index, fps, canvas_size):
        t = frame_index / fps
        alpha = 255 - int(alpha_at(self.t_start, self.t_end, t, self.easing) * 255)
        if alpha <= 0:
            return None
        img = Image.new("RGBA", canvas_size, (*self.color, alpha))
        return img


class FadeOut(Layer):
    """Transparent-to-black fade at the end of a scene."""
    z_index = 900

    def __init__(self, t_start: float = 4.5, t_end: float = 5.0,
                 color: Tuple[int, int, int] = (0, 0, 0), easing: str = "ease_in"):
        self.t_start = t_start
        self.t_end = t_end
        self.color = color
        self.easing = easing

    def is_active(self, frame_index, fps):
        return frame_index / fps >= self.t_start

    def render_frame(self, frame_index, fps, canvas_size):
        t = frame_index / fps
        alpha = int(alpha_at(self.t_start, self.t_end, t, self.easing) * 255)
        if alpha <= 0:
            return None
        img = Image.new("RGBA", canvas_size, (*self.color, alpha))
        return img


class FadeTo(Layer):
    """Fade from one color to another (e.g. black → white)."""
    z_index = 900

    def __init__(self, t_start: float, t_end: float,
                 color_from: Tuple[int, int, int] = (0, 0, 0),
                 color_to: Tuple[int, int, int] = (255, 255, 255),
                 easing: str = "ease_in_out"):
        self.t_start = t_start
        self.t_end = t_end
        self.color_from = color_from
        self.color_to = color_to
        self.easing = easing

    def is_active(self, frame_index, fps):
        t = frame_index / fps
        return self.t_start <= t <= self.t_end

    def render_frame(self, frame_index, fps, canvas_size):
        t = frame_index / fps
        color = interpolate(self.color_from, self.color_to,
                            self.t_start, self.t_end, t, self.easing)
        img = Image.new("RGBA", canvas_size, (*color, 255))
        return img


# ── Slide Wipe ────────────────────────────────────────────────────────────────

class SlideIn(Layer):
    """A colored panel slides in from an edge, then dissolves."""
    z_index = 850

    DIRECTIONS = ("left", "right", "top", "bottom")

    def __init__(self, t_start: float, t_mid: float, t_end: float,
                 color: Tuple[int, int, int] = (30, 30, 30),
                 direction: str = "left", easing: str = "ease_in_out"):
        assert direction in self.DIRECTIONS
        self.t_start = t_start
        self.t_mid = t_mid
        self.t_end = t_end
        self.color = color
        self.direction = direction
        self.easing = easing

    def is_active(self, frame_index, fps):
        t = frame_index / fps
        return self.t_start <= t <= self.t_end

    def render_frame(self, frame_index, fps, canvas_size):
        W, H = canvas_size
        t = frame_index / fps

        if t <= self.t_mid:
            # Slide in: panel covers 0 → full
            progress = alpha_at(self.t_start, self.t_mid, t, self.easing)
        else:
            # Slide out: panel retreats full → 0
            progress = 1.0 - alpha_at(self.t_mid, self.t_end, t, self.easing)

        img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        if self.direction == "left":
            x = int(W * progress)
            d.rectangle([0, 0, x, H], fill=(*self.color, 255))
        elif self.direction == "right":
            x = int(W * (1 - progress))
            d.rectangle([x, 0, W, H], fill=(*self.color, 255))
        elif self.direction == "top":
            y = int(H * progress)
            d.rectangle([0, 0, W, y], fill=(*self.color, 255))
        elif self.direction == "bottom":
            y = int(H * (1 - progress))
            d.rectangle([0, y, W, H], fill=(*self.color, 255))

        return img


# ── Zoom Pulse ────────────────────────────────────────────────────────────────

class ZoomPulse(Layer):
    """Briefly zoom in on the center — useful for emphasis."""
    z_index = 800

    def __init__(self, t_peak: float, duration: float = 0.3,
                 max_scale: float = 1.05, easing: str = "ease_in_out"):
        self.t_peak = t_peak
        self.t_start = t_peak - duration / 2
        self.t_end = t_peak + duration / 2
        self.max_scale = max_scale
        self.easing = easing

    def is_active(self, frame_index, fps):
        t = frame_index / fps
        return self.t_start <= t <= self.t_end

    def render_frame(self, frame_index, fps, canvas_size):
        # ZoomPulse works by scaling the canvas content — handled at scene level.
        # This layer signals the scale factor via a public property.
        t = frame_index / fps
        if t <= self.t_peak:
            s = interpolate(1.0, self.max_scale, self.t_start, self.t_peak, t, self.easing)
        else:
            s = interpolate(self.max_scale, 1.0, self.t_peak, self.t_end, t, self.easing)
        self._current_scale = s
        return None  # No overlay — the scene builder reads _current_scale
