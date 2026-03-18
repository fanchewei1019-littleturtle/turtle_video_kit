# -*- coding: utf-8 -*-
"""
Canvas — the per-frame drawing surface.
Manages ordered layers and composites them into a single PIL Image each frame.
"""
from __future__ import annotations
from PIL import Image, ImageDraw
from typing import List, Tuple, Optional


class Layer:
    """Base class for anything that can be drawn onto a frame."""

    # Override in subclasses
    z_index: int = 0

    def render_frame(self, frame_index: int, fps: float,
                     canvas_size: Tuple[int, int]) -> Optional[Image.Image]:
        """
        Return a PIL Image (RGBA) for this frame, or None to skip.
        The returned image will be alpha-composited onto the canvas.
        """
        raise NotImplementedError

    def is_active(self, frame_index: int, fps: float) -> bool:
        """Override to limit which frames this layer is drawn on."""
        return True


class Canvas:
    """
    A single frame compositor.
    Add Layer objects, then call render(frame_index) to get the composite image.
    """

    def __init__(self, width: int = 1280, height: int = 720,
                 background: Tuple[int, int, int] = (229, 234, 228)):
        self.width = width
        self.height = height
        self.background = background
        self._layers: List[Layer] = []

    @property
    def size(self) -> Tuple[int, int]:
        return (self.width, self.height)

    def add(self, layer: Layer) -> "Canvas":
        """Add a layer; returns self for chaining."""
        self._layers.append(layer)
        self._layers.sort(key=lambda l: l.z_index)
        return self

    def remove(self, layer: Layer) -> "Canvas":
        self._layers = [l for l in self._layers if l is not layer]
        return self

    def clear(self) -> "Canvas":
        self._layers.clear()
        return self

    def render(self, frame_index: int, fps: float = 30.0) -> Image.Image:
        """Composite all active layers and return the final RGB frame."""
        base = Image.new("RGBA", self.size, (*self.background, 255))

        for layer in self._layers:
            if not layer.is_active(frame_index, fps):
                continue
            result = layer.render_frame(frame_index, fps, self.size)
            if result is None:
                continue
            if result.mode != "RGBA":
                result = result.convert("RGBA")
            base = Image.alpha_composite(base, result)

        return base.convert("RGB")

    def blank_rgba(self) -> Image.Image:
        """Return a transparent RGBA canvas of this size."""
        return Image.new("RGBA", self.size, (0, 0, 0, 0))

    def draw_on(self, img: Image.Image) -> ImageDraw.ImageDraw:
        """Convenience: get an ImageDraw for an image."""
        return ImageDraw.Draw(img)
