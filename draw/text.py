# -*- coding: utf-8 -*-
"""
Text layers — animated text with typewriter, fade-in, slide-in effects.
"""
from __future__ import annotations
import textwrap
from pathlib import Path
from typing import Tuple, Optional

from PIL import Image, ImageDraw, ImageFont

from ..core.canvas import Layer
from ..core.keyframe import interpolate, alpha_at

# Default font paths (Windows)
FONT_PATHS = [
    "C:/Windows/Fonts/msjh.ttc",   # Microsoft JhengHei (Traditional Chinese)
    "C:/Windows/Fonts/msyh.ttc",   # Microsoft YaHei (Simplified Chinese)
    "C:/Windows/Fonts/arial.ttf",
]

def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ── Static Text ───────────────────────────────────────────────────────────────

class TextLabel(Layer):
    """Simple static text label with optional shadow."""
    z_index = 50

    def __init__(self, text: str, x: float, y: float,
                 font_size: int = 36,
                 color: Tuple[int, int, int] = (255, 255, 255),
                 alpha: int = 255,
                 anchor: str = "lt",
                 shadow: bool = False,
                 shadow_color: Tuple[int, int, int] = (0, 0, 0),
                 shadow_offset: Tuple[int, int] = (2, 2),
                 max_width: Optional[int] = None,
                 t_start: float = 0.0, t_end: Optional[float] = None):
        self.text = text
        self.x = x
        self.y = y
        self.font_size = font_size
        self.color = color
        self.alpha = alpha
        self.anchor = anchor
        self.shadow = shadow
        self.shadow_color = shadow_color
        self.shadow_offset = shadow_offset
        self.max_width = max_width
        self.t_start = t_start
        self.t_end = t_end
        self._font = _load_font(font_size)

    def is_active(self, frame_index, fps):
        t = frame_index / fps
        if t < self.t_start:
            return False
        if self.t_end is not None and t > self.t_end:
            return False
        return True

    def _wrapped_text(self) -> str:
        if self.max_width and self._font:
            avg_char = self.font_size * 0.6
            chars = max(1, int(self.max_width / avg_char))
            return "\n".join(textwrap.wrap(self.text, chars))
        return self.text

    def render_frame(self, frame_index, fps, canvas_size):
        img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        text = self._wrapped_text()

        if self.shadow:
            ox, oy = self.shadow_offset
            d.text((self.x + ox, self.y + oy), text,
                   font=self._font, fill=(*self.shadow_color, self.alpha),
                   anchor=self.anchor)

        d.text((self.x, self.y), text,
               font=self._font, fill=(*self.color, self.alpha),
               anchor=self.anchor)
        return img


# ── Typewriter ────────────────────────────────────────────────────────────────

class Typewriter(Layer):
    """Text appears character by character."""
    z_index = 50

    def __init__(self, text: str, x: float, y: float,
                 t_start: float, t_end: float,
                 font_size: int = 36,
                 color: Tuple[int, int, int] = (255, 255, 255),
                 anchor: str = "lt",
                 cursor: bool = True,
                 max_width: Optional[int] = None):
        self.text = text
        self.x = x
        self.y = y
        self.t_start = t_start
        self.t_end = t_end
        self.font_size = font_size
        self.color = color
        self.anchor = anchor
        self.cursor = cursor
        self.max_width = max_width
        self._font = _load_font(font_size)

    def is_active(self, frame_index, fps):
        return frame_index / fps >= self.t_start

    def render_frame(self, frame_index, fps, canvas_size):
        t = frame_index / fps
        progress = alpha_at(self.t_start, self.t_end, t)
        n_chars = int(progress * len(self.text))
        visible = self.text[:n_chars]

        # Blinking cursor
        if self.cursor and n_chars < len(self.text):
            if int(t * 2) % 2 == 0:
                visible += "|"

        if self.max_width:
            avg_char = self.font_size * 0.6
            chars = max(1, int(self.max_width / avg_char))
            visible = "\n".join(textwrap.wrap(visible, chars))

        img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.text((self.x, self.y), visible,
               font=self._font, fill=(*self.color, 255),
               anchor=self.anchor)
        return img


# ── FadeInText ────────────────────────────────────────────────────────────────

class FadeInText(Layer):
    """Text fades in from transparent."""
    z_index = 50

    def __init__(self, text: str, x: float, y: float,
                 t_start: float, t_end: float,
                 font_size: int = 36,
                 color: Tuple[int, int, int] = (255, 255, 255),
                 anchor: str = "lt",
                 easing: str = "ease_out",
                 hold: bool = True,
                 t_fade_out_start: Optional[float] = None,
                 t_fade_out_end: Optional[float] = None,
                 max_width: Optional[int] = None):
        self.text = text
        self.x = x
        self.y = y
        self.t_start = t_start
        self.t_end = t_end
        self.font_size = font_size
        self.color = color
        self.anchor = anchor
        self.easing = easing
        self.hold = hold
        self.t_fade_out_start = t_fade_out_start
        self.t_fade_out_end = t_fade_out_end
        self.max_width = max_width
        self._font = _load_font(font_size)

    def is_active(self, frame_index, fps):
        t = frame_index / fps
        if t < self.t_start:
            return False
        if self.t_fade_out_end and t > self.t_fade_out_end:
            return False
        if not self.hold and t > self.t_end:
            return False
        return True

    def render_frame(self, frame_index, fps, canvas_size):
        t = frame_index / fps
        alpha = alpha_at(self.t_start, self.t_end, t, self.easing)

        if self.t_fade_out_start and self.t_fade_out_end and t >= self.t_fade_out_start:
            fade_out = 1.0 - alpha_at(self.t_fade_out_start, self.t_fade_out_end, t)
            alpha = min(alpha, fade_out)

        text = self.text
        if self.max_width:
            avg_char = self.font_size * 0.6
            chars = max(1, int(self.max_width / avg_char))
            text = "\n".join(textwrap.wrap(text, chars))

        img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.text((self.x, self.y), text,
               font=self._font, fill=(*self.color, int(alpha * 255)),
               anchor=self.anchor)
        return img


# ── SlideInText ───────────────────────────────────────────────────────────────

class SlideInText(Layer):
    """Text slides in from a direction."""
    z_index = 50

    def __init__(self, text: str, x: float, y: float,
                 t_start: float, t_end: float,
                 font_size: int = 36,
                 color: Tuple[int, int, int] = (255, 255, 255),
                 anchor: str = "lt",
                 direction: str = "bottom",
                 slide_distance: float = 40.0,
                 easing: str = "ease_out"):
        self.text = text
        self.x = x
        self.y = y
        self.t_start = t_start
        self.t_end = t_end
        self.font_size = font_size
        self.color = color
        self.anchor = anchor
        self.direction = direction
        self.slide_distance = slide_distance
        self.easing = easing
        self._font = _load_font(font_size)

    def is_active(self, frame_index, fps):
        return frame_index / fps >= self.t_start

    def render_frame(self, frame_index, fps, canvas_size):
        t = frame_index / fps
        progress = alpha_at(self.t_start, self.t_end, t, self.easing)
        offset = (1.0 - progress) * self.slide_distance

        dx, dy = 0.0, 0.0
        if self.direction == "bottom":
            dy = offset
        elif self.direction == "top":
            dy = -offset
        elif self.direction == "left":
            dx = -offset
        elif self.direction == "right":
            dx = offset

        img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.text((self.x + dx, self.y + dy), self.text,
               font=self._font,
               fill=(*self.color, int(progress * 255)),
               anchor=self.anchor)
        return img
