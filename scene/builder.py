# -*- coding: utf-8 -*-
"""
Scene builder — assembles layers, audio, and timing into a renderable scene.
"""
from __future__ import annotations
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, Callable

from ..core.canvas import Canvas, Layer
from ..core.timeline import Timeline
from ..core.renderer import Renderer, FFMPEG_DEFAULT


class Scene:
    """
    A complete video scene with layers and optional audio.

    Usage:
        scene = Scene(width=1280, height=720, fps=30, duration=5.0)
        scene.add(FadeIn(0, 0.5))
        scene.add(TextLabel("Hello", 640, 360))
        scene.render("output.mp4")
    """

    def __init__(self, width: int = 1280, height: int = 720,
                 fps: float = 30.0, duration: float = 5.0,
                 background: Tuple[int, int, int] = (229, 234, 228),
                 ffmpeg_path: str = FFMPEG_DEFAULT):
        self.timeline = Timeline(fps=fps, duration=duration)
        self.canvas = Canvas(width, height, background)
        self.ffmpeg = ffmpeg_path
        self._audio_path: Optional[str] = None

    @property
    def width(self) -> int:
        return self.canvas.width

    @property
    def height(self) -> int:
        return self.canvas.height

    @property
    def fps(self) -> float:
        return self.timeline.fps

    @property
    def duration(self) -> float:
        return self.timeline.duration

    @duration.setter
    def duration(self, value: float):
        self.timeline.duration = value

    def add(self, layer: Layer) -> "Scene":
        """Add a layer. Returns self for chaining."""
        self.canvas.add(layer)
        return self

    def remove(self, layer: Layer) -> "Scene":
        self.canvas.remove(layer)
        return self

    def set_audio(self, audio_path: str) -> "Scene":
        """Set the audio track for this scene."""
        self._audio_path = audio_path
        return self

    def preview(self, time: float = 0.0, output: str = "preview.jpg") -> Path:
        """Render a single frame for quick visual inspection."""
        renderer = Renderer(self.canvas, self.timeline, self.ffmpeg)
        return renderer.render_preview(time, output)

    def render(self, output_path: str,
               on_progress: Optional[Callable[[int, int], None]] = None,
               preview_every: int = 0) -> Path:
        """Render all frames and encode to mp4."""
        renderer = Renderer(self.canvas, self.timeline, self.ffmpeg)
        return renderer.render(
            output_path,
            audio_path=self._audio_path,
            on_progress=on_progress,
            preview_every=preview_every,
        )

    def __repr__(self):
        return (f"Scene({self.width}x{self.height}, {self.fps}fps, "
                f"{self.duration}s, {len(self.canvas._layers)} layers)")


# ── Multi-scene concatenation ─────────────────────────────────────────────────

class Video:
    """
    Concatenate multiple Scene objects into one final mp4.

    Usage:
        video = Video()
        video.append(scene1)
        video.append(scene2)
        video.export("final.mp4")
    """

    def __init__(self, ffmpeg_path: str = FFMPEG_DEFAULT):
        self.scenes: List[Scene] = []
        self.ffmpeg = ffmpeg_path

    def append(self, scene: Scene) -> "Video":
        self.scenes.append(scene)
        return self

    def export(self, output_path: str,
               temp_dir: Optional[str] = None,
               on_scene_start: Optional[Callable[[int, Scene], None]] = None) -> Path:
        """
        Render each scene to a temp file, then concatenate.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(temp_dir or tmp)
            scene_files = []

            for i, scene in enumerate(self.scenes):
                if on_scene_start:
                    on_scene_start(i, scene)

                scene_out = tmp_path / f"scene_{i:03d}.mp4"
                print(f"[Video] Rendering scene {i+1}/{len(self.scenes)} ...")
                scene.render(str(scene_out))
                scene_files.append(scene_out)

            # Write concat list
            concat_list = tmp_path / "concat.txt"
            with open(concat_list, "w") as f:
                for sf in scene_files:
                    f.write(f"file '{sf.as_posix()}'\n")

            # Concatenate
            cmd = [
                self.ffmpeg, "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_list),
                "-c", "copy",
                str(out)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg concat failed:\n{result.stderr}")

        print(f"[Video] Done → {out}")
        return out
