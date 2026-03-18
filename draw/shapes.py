# -*- coding: utf-8 -*-
"""
Shapes — animatable primitive shapes as Layers.
Each shape has x, y, color, alpha properties that can be updated each frame.
"""
from __future__ import annotations
import math
from typing import Tuple, Optional

from PIL import Image, ImageDraw, ImageFilter

from ..core.canvas import Layer
from ..core.keyframe import interpolate


# ── Base Shape ────────────────────────────────────────────────────────────────

class Shape(Layer):
    z_index = 10

    def __init__(self, t_start: float = 0.0, t_end: Optional[float] = None):
        self.t_start = t_start
        self.t_end = t_end

    def is_active(self, frame_index, fps):
        t = frame_index / fps
        if t < self.t_start:
            return False
        if self.t_end is not None and t > self.t_end:
            return False
        return True


# ── Circle ────────────────────────────────────────────────────────────────────

class Circle(Shape):
    def __init__(self, cx: float, cy: float, r: float,
                 color: Tuple[int, int, int] = (255, 215, 0),
                 outline: Optional[Tuple[int, int, int]] = None,
                 outline_width: int = 2,
                 alpha: int = 255,
                 shadow: bool = False,
                 t_start: float = 0.0, t_end: Optional[float] = None):
        super().__init__(t_start, t_end)
        self.cx = cx
        self.cy = cy
        self.r = r
        self.color = color
        self.outline = outline
        self.outline_width = outline_width
        self.alpha = alpha
        self.shadow = shadow

    def render_frame(self, frame_index, fps, canvas_size):
        img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        if self.shadow:
            sd = ImageDraw.Draw(img)
            sr = self.r + 4
            sd.ellipse([self.cx - sr + 6, self.cy - sr + 6,
                        self.cx + sr + 6, self.cy + sr + 6],
                       fill=(0, 0, 0, 80))

        d.ellipse([self.cx - self.r, self.cy - self.r,
                   self.cx + self.r, self.cy + self.r],
                  fill=(*self.color, self.alpha),
                  outline=(*self.outline, self.alpha) if self.outline else None,
                  width=self.outline_width)
        return img


# ── Rectangle ─────────────────────────────────────────────────────────────────

class Rect(Shape):
    def __init__(self, cx: float, cy: float, w: float, h: float,
                 color: Tuple[int, int, int] = (255, 215, 0),
                 outline: Optional[Tuple[int, int, int]] = None,
                 outline_width: int = 2,
                 radius: int = 0,
                 alpha: int = 255,
                 shadow: bool = False,
                 t_start: float = 0.0, t_end: Optional[float] = None):
        super().__init__(t_start, t_end)
        self.cx = cx
        self.cy = cy
        self.w = w
        self.h = h
        self.color = color
        self.outline = outline
        self.outline_width = outline_width
        self.radius = radius
        self.alpha = alpha
        self.shadow = shadow

    def render_frame(self, frame_index, fps, canvas_size):
        img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        x0 = self.cx - self.w / 2
        y0 = self.cy - self.h / 2
        x1 = self.cx + self.w / 2
        y1 = self.cy + self.h / 2

        if self.shadow:
            d.rounded_rectangle([x0 + 6, y0 + 6, x1 + 6, y1 + 6],
                                 radius=self.radius, fill=(0, 0, 0, 80))

        draw_fn = d.rounded_rectangle if self.radius > 0 else d.rectangle
        kwargs = dict(fill=(*self.color, self.alpha),
                      outline=(*self.outline, self.alpha) if self.outline else None,
                      width=self.outline_width)
        if self.radius > 0:
            kwargs["radius"] = self.radius
        draw_fn([x0, y0, x1, y1], **kwargs)
        return img


# ── Line ──────────────────────────────────────────────────────────────────────

class Line(Shape):
    def __init__(self, x0: float, y0: float, x1: float, y1: float,
                 color: Tuple[int, int, int] = (255, 255, 255),
                 width: int = 3, alpha: int = 255,
                 t_start: float = 0.0, t_end: Optional[float] = None,
                 draw_progress: float = 1.0):
        """
        draw_progress: 0.0 = nothing drawn, 1.0 = full line.
        Animate this to get a line-drawing effect.
        """
        super().__init__(t_start, t_end)
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self.color = color
        self.width = width
        self.alpha = alpha
        self.draw_progress = draw_progress

    def render_frame(self, frame_index, fps, canvas_size):
        img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        p = max(0.0, min(1.0, self.draw_progress))
        ex = self.x0 + (self.x1 - self.x0) * p
        ey = self.y0 + (self.y1 - self.y0) * p
        d.line([self.x0, self.y0, ex, ey],
               fill=(*self.color, self.alpha), width=self.width)
        return img


# ── Arrow ─────────────────────────────────────────────────────────────────────

class Arrow(Shape):
    def __init__(self, x0: float, y0: float, x1: float, y1: float,
                 color: Tuple[int, int, int] = (255, 255, 255),
                 width: int = 3, head_size: int = 15,
                 alpha: int = 255,
                 t_start: float = 0.0, t_end: Optional[float] = None):
        super().__init__(t_start, t_end)
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.color = color
        self.width = width
        self.head_size = head_size
        self.alpha = alpha

    def render_frame(self, frame_index, fps, canvas_size):
        img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        c = (*self.color, self.alpha)
        d.line([self.x0, self.y0, self.x1, self.y1], fill=c, width=self.width)

        # Arrowhead
        angle = math.atan2(self.y1 - self.y0, self.x1 - self.x0)
        hs = self.head_size
        for da in [math.pi * 0.75, -math.pi * 0.75]:
            hx = self.x1 + hs * math.cos(angle + da)
            hy = self.y1 + hs * math.sin(angle + da)
            d.line([self.x1, self.y1, hx, hy], fill=c, width=self.width)
        return img


# ── Polygon ───────────────────────────────────────────────────────────────────

class Polygon(Shape):
    def __init__(self, points: list,
                 color: Tuple[int, int, int] = (255, 215, 0),
                 outline: Optional[Tuple[int, int, int]] = None,
                 outline_width: int = 2,
                 alpha: int = 255,
                 t_start: float = 0.0, t_end: Optional[float] = None):
        super().__init__(t_start, t_end)
        self.points = points
        self.color = color
        self.outline = outline
        self.outline_width = outline_width
        self.alpha = alpha

    def render_frame(self, frame_index, fps, canvas_size):
        img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.polygon(self.points,
                  fill=(*self.color, self.alpha),
                  outline=(*self.outline, self.alpha) if self.outline else None)
        return img


# ── Gradient Background ───────────────────────────────────────────────────────

class GradientBG(Shape):
    """Vertical or horizontal linear gradient background."""
    z_index = 0

    def __init__(self, color_top: Tuple[int, int, int],
                 color_bottom: Tuple[int, int, int],
                 direction: str = "vertical",
                 t_start: float = 0.0, t_end: Optional[float] = None):
        super().__init__(t_start, t_end)
        self.color_top = color_top
        self.color_bottom = color_bottom
        self.direction = direction

    def render_frame(self, frame_index, fps, canvas_size):
        W, H = canvas_size
        img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        for i in range(H if self.direction == "vertical" else W):
            t = i / (H - 1 if self.direction == "vertical" else W - 1)
            r = int(self.color_top[0] + (self.color_bottom[0] - self.color_top[0]) * t)
            g = int(self.color_top[1] + (self.color_bottom[1] - self.color_top[1]) * t)
            b = int(self.color_top[2] + (self.color_bottom[2] - self.color_top[2]) * t)
            if self.direction == "vertical":
                img.paste(Image.new("RGBA", (W, 1), (r, g, b, 255)), (0, i))
            else:
                img.paste(Image.new("RGBA", (1, H), (r, g, b, 255)), (i, 0))
        return img
