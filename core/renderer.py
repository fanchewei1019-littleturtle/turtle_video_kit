# -*- coding: utf-8 -*-
"""
Renderer — takes a Canvas + Timeline and writes frames to an mp4 via ffmpeg.
Handles Windows path quirks automatically.
"""
from __future__ import annotations
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Callable

from PIL import Image

from .canvas import Canvas
from .timeline import Timeline


# Default ffmpeg path — override via env var FFMPEG_PATH or pass explicitly
FFMPEG_DEFAULT = os.environ.get(
    "FFMPEG_PATH",
    "C:/Users/chewei/ffmpeg/bin/ffmpeg.exe"
)


class Renderer:
    def __init__(self, canvas: Canvas, timeline: Timeline,
                 ffmpeg_path: str = FFMPEG_DEFAULT):
        self.canvas = canvas
        self.timeline = timeline
        self.ffmpeg = ffmpeg_path

    def render(self, output_path: str,
               audio_path: Optional[str] = None,
               on_progress: Optional[Callable[[int, int], None]] = None,
               preview_every: int = 0) -> Path:
        """
        Render all frames and encode to mp4.

        Args:
            output_path:    destination .mp4 file
            audio_path:     optional audio file to mix in
            on_progress:    callback(frame, total) for progress reporting
            preview_every:  save a preview PNG every N frames (0 = disabled)
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        total = self.timeline.total_frames

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            frames_dir = tmp / "frames"
            frames_dir.mkdir()

            # ── Render frames ────────────────────────────────────────────
            for i in range(total):
                frame = self.canvas.render(i, self.timeline.fps)
                frame_path = frames_dir / f"frame_{i:06d}.png"
                frame.save(str(frame_path))

                if on_progress:
                    on_progress(i + 1, total)

                if preview_every and i % preview_every == 0:
                    preview_path = output.parent / f"preview_{i:06d}.jpg"
                    frame.save(str(preview_path), quality=85)

            # ── Encode with ffmpeg ───────────────────────────────────────
            self._encode(frames_dir, output, audio_path)

        return output

    def render_preview(self, time: float, output_path: str = "preview.jpg") -> Path:
        """Render a single frame at a given time for quick inspection."""
        frame_idx = self.timeline.frame_at(time)
        frame = self.canvas.render(frame_idx, self.timeline.fps)
        out = Path(output_path)
        frame.save(str(out), quality=90)
        return out

    def _encode(self, frames_dir: Path, output: Path,
                audio_path: Optional[str] = None):
        """Run ffmpeg to encode frames → mp4, with optional audio."""
        input_pattern = str(frames_dir / "frame_%06d.png")
        fps_str = str(self.timeline.fps)

        if audio_path:
            cmd = [
                self.ffmpeg, "-y",
                "-framerate", fps_str,
                "-i", input_pattern,
                "-i", audio_path,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-crf", "18",
                "-preset", "fast",
                "-c:a", "aac",
                "-shortest",
                str(output)
            ]
        else:
            cmd = [
                self.ffmpeg, "-y",
                "-framerate", fps_str,
                "-i", input_pattern,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-crf", "18",
                "-preset", "fast",
                str(output)
            ]

        result = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")
