# -*- coding: utf-8 -*-
"""
Motion — animate position, scale, rotation, and opacity of any Layer.
Wrap any existing layer with these animators.
"""
from __future__ import annotations
import math
from typing import Optional, Tuple

from PIL import Image

from ..core.canvas import Layer
from ..core.keyframe import interpolate


class MoveTo(Layer):
    """Move a layer from its initial position to a target position."""
    z_index = 10

    def __init__(self, layer: Layer,
                 x_start: float, y_start: float,
                 x_end: float, y_end: float,
                 t_start: float, t_end: float,
                 easing: str = "ease_in_out"):
        self.layer = layer
        self.x_start = x_start
        self.y_start = y_start
        self.x_end = x_end
        self.y_end = y_end
        self.t_start = t_start
        self.t_end = t_end
        self.easing = easing
        self.z_index = layer.z_index

    def is_active(self, frame_index, fps):
        return self.layer.is_active(frame_index, fps)

    def render_frame(self, frame_index, fps, canvas_size):
        t = frame_index / fps
        x = interpolate(self.x_start, self.x_end, self.t_start, self.t_end, t, self.easing)
        y = interpolate(self.y_start, self.y_end, self.t_start, self.t_end, t, self.easing)

        # Set position on wrapped layer if it supports it
        if hasattr(self.layer, 'x'):
            self.layer.x = x
        if hasattr(self.layer, 'y'):
            self.layer.y = y

        base = self.layer.render_frame(frame_index, fps, canvas_size)
        if base is None:
            return None

        # If layer doesn't have x/y, shift the rendered image
        img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        img.paste(base, (int(x), int(y)), base if base.mode == "RGBA" else None)
        return img


class ScaleAnim(Layer):
    """Animate the scale of a layer."""
    z_index = 10

    def __init__(self, layer: Layer,
                 scale_start: float, scale_end: float,
                 t_start: float, t_end: float,
                 anchor: Tuple[float, float] = (0.5, 0.5),
                 easing: str = "ease_out"):
        self.layer = layer
        self.scale_start = scale_start
        self.scale_end = scale_end
        self.t_start = t_start
        self.t_end = t_end
        self.anchor = anchor
        self.easing = easing
        self.z_index = layer.z_index

    def is_active(self, frame_index, fps):
        return self.layer.is_active(frame_index, fps)

    def render_frame(self, frame_index, fps, canvas_size):
        t = frame_index / fps
        scale = interpolate(self.scale_start, self.scale_end,
                            self.t_start, self.t_end, t, self.easing)

        base = self.layer.render_frame(frame_index, fps, canvas_size)
        if base is None:
            return None

        W, H = canvas_size
        new_w = max(1, int(W * scale))
        new_h = max(1, int(H * scale))
        scaled = base.resize((new_w, new_h), Image.LANCZOS)

        ax, ay = self.anchor
        offset_x = int((W - new_w) * ax)
        offset_y = int((H - new_h) * ay)

        img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        img.paste(scaled, (offset_x, offset_y),
                  scaled if scaled.mode == "RGBA" else None)
        return img


class FadeLayer(Layer):
    """Fade the opacity of any layer in or out."""
    z_index = 10

    def __init__(self, layer: Layer,
                 alpha_start: float, alpha_end: float,
                 t_start: float, t_end: float,
                 easing: str = "ease_in_out",
                 hold_after: bool = True):
        self.layer = layer
        self.alpha_start = alpha_start
        self.alpha_end = alpha_end
        self.t_start = t_start
        self.t_end = t_end
        self.easing = easing
        self.hold_after = hold_after
        self.z_index = layer.z_index

    def is_active(self, frame_index, fps):
        if not self.hold_after and frame_index / fps > self.t_end:
            return False
        return self.layer.is_active(frame_index, fps)

    def render_frame(self, frame_index, fps, canvas_size):
        t = frame_index / fps
        alpha = interpolate(self.alpha_start, self.alpha_end,
                            self.t_start, self.t_end, t, self.easing)
        alpha = max(0.0, min(1.0, alpha))

        base = self.layer.render_frame(frame_index, fps, canvas_size)
        if base is None:
            return None

        if base.mode != "RGBA":
            base = base.convert("RGBA")

        r, g, b, a = base.split()
        a = a.point(lambda x: int(x * alpha))
        return Image.merge("RGBA", (r, g, b, a))


class RotateAnim(Layer):
    """Rotate a layer around a center point."""
    z_index = 10

    def __init__(self, layer: Layer,
                 angle_start: float, angle_end: float,
                 t_start: float, t_end: float,
                 center: Optional[Tuple[float, float]] = None,
                 easing: str = "linear",
                 expand: bool = False):
        self.layer = layer
        self.angle_start = angle_start
        self.angle_end = angle_end
        self.t_start = t_start
        self.t_end = t_end
        self.center = center
        self.easing = easing
        self.expand = expand
        self.z_index = layer.z_index

    def is_active(self, frame_index, fps):
        return self.layer.is_active(frame_index, fps)

    def render_frame(self, frame_index, fps, canvas_size):
        t = frame_index / fps
        angle = interpolate(self.angle_start, self.angle_end,
                            self.t_start, self.t_end, t, self.easing)

        base = self.layer.render_frame(frame_index, fps, canvas_size)
        if base is None:
            return None

        if base.mode != "RGBA":
            base = base.convert("RGBA")

        rotated = base.rotate(-angle, resample=Image.BICUBIC,
                              center=self.center, expand=self.expand)
        if self.expand:
            # Re-center on canvas
            img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
            W, H = canvas_size
            ox = (W - rotated.width) // 2
            oy = (H - rotated.height) // 2
            img.paste(rotated, (ox, oy), rotated)
            return img
        return rotated


class Shake(Layer):
    """Apply a random-ish camera shake to a layer."""
    z_index = 10

    def __init__(self, layer: Layer,
                 t_start: float, t_end: float,
                 intensity: float = 8.0, frequency: float = 20.0):
        self.layer = layer
        self.t_start = t_start
        self.t_end = t_end
        self.intensity = intensity
        self.frequency = frequency
        self.z_index = layer.z_index

    def is_active(self, frame_index, fps):
        return self.layer.is_active(frame_index, fps)

    def render_frame(self, frame_index, fps, canvas_size):
        t = frame_index / fps
        if not (self.t_start <= t <= self.t_end):
            return self.layer.render_frame(frame_index, fps, canvas_size)

        dx = int(self.intensity * math.sin(t * self.frequency * 2 * math.pi))
        dy = int(self.intensity * math.cos(t * self.frequency * 1.7 * math.pi))

        base = self.layer.render_frame(frame_index, fps, canvas_size)
        if base is None:
            return None

        img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        img.paste(base, (dx, dy), base if base.mode == "RGBA" else None)
        return img
