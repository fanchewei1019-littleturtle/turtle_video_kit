# -*- coding: utf-8 -*-
"""
Timeline — manages the relationship between real time and frame numbers.
Also provides a FrameRange helper for layers that only exist for a window of time.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Timeline:
    fps: float = 30.0
    duration: float = 10.0  # seconds

    @property
    def total_frames(self) -> int:
        return int(self.duration * self.fps)

    def time_at(self, frame: int) -> float:
        return frame / self.fps

    def frame_at(self, time: float) -> int:
        return int(time * self.fps)

    def frames_range(self, t_start: float, t_end: float):
        """Iterate frame indices for a time window."""
        return range(self.frame_at(t_start), self.frame_at(t_end) + 1)


@dataclass
class FrameRange:
    """
    Mixin/helper for layers that are only active during [t_start, t_end].
    Use `is_in_range(frame, fps)` to guard render_frame.
    """
    t_start: float = 0.0
    t_end: Optional[float] = None  # None = "until end of scene"

    def is_in_range(self, frame_index: int, fps: float,
                    scene_duration: Optional[float] = None) -> bool:
        t = frame_index / fps
        end = self.t_end if self.t_end is not None else float("inf")
        return self.t_start <= t <= end

    def local_t(self, frame_index: int, fps: float) -> float:
        """Normalized time 0→1 within this layer's active window."""
        t = frame_index / fps
        if self.t_end is None or self.t_end <= self.t_start:
            return 0.0
        return max(0.0, min(1.0, (t - self.t_start) / (self.t_end - self.t_start)))

    def current_time(self, frame_index: int, fps: float) -> float:
        return frame_index / fps
