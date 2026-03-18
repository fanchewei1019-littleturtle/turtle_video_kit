# -*- coding: utf-8 -*-
"""
Demo — showcase turtle_video_kit capabilities.
Renders a 6-second clip featuring:
  - Gradient background morphing color
  - Circle morphing into square
  - A walking turtle
  - Typewriter title
  - Fade in/out transitions
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # projects root

from turtle_video_kit.scene.builder import Scene
from turtle_video_kit.core.keyframe import interpolate
from turtle_video_kit.anim.transitions import FadeIn, FadeOut, SlideIn
from turtle_video_kit.anim.morph import ShapeMorph, circle_polygon, rect_polygon
from turtle_video_kit.anim.motion import FadeLayer, MoveTo, ScaleAnim
from turtle_video_kit.draw.shapes import GradientBG, Circle, Rect, Arrow
from turtle_video_kit.draw.text import FadeInText, Typewriter, SlideInText
from turtle_video_kit.draw.creatures import Turtle, Bird


OUTPUT_DIR = Path(__file__).parent / "test_output"
OUTPUT_DIR.mkdir(exist_ok=True)


def make_demo():
    print("Building demo scene...")
    scene = Scene(width=1280, height=720, fps=30, duration=6.0,
                  background=(20, 25, 35))

    # ── Background gradient ───────────────────────────────────────────────
    scene.add(GradientBG(
        color_top=(20, 25, 40),
        color_bottom=(40, 20, 60)
    ))

    # ── Circle → Square morph ─────────────────────────────────────────────
    circle_pts = circle_polygon(640, 320, 90)
    square_pts = rect_polygon(640, 320, 180, 180)

    morph = ShapeMorph(
        circle_pts, square_pts,
        t_start=1.5, t_end=3.0,
        fill=(255, 215, 0),
        outline=(255, 180, 0),
        outline_width=3,
        easing="ease_in_out"
    )
    scene.add(morph)

    # ── Walking turtle ────────────────────────────────────────────────────
    turtle = Turtle(x=-80, y=580, scale=0.9, walk_cycle=True, direction="right")
    walking = MoveTo(turtle,
                     x_start=-80, y_start=580,
                     x_end=1360, y_end=580,
                     t_start=0.5, t_end=5.5,
                     easing="linear")
    # Note: MoveTo shifts the whole canvas — for creature movement we set x directly
    # Instead, animate turtle.x manually via a custom layer wrapper
    scene.add(TurtleWalker(turtle, x_start=-80, x_end=1360, t_start=0.5, t_end=5.5))

    # ── Flying bird ───────────────────────────────────────────────────────
    from turtle_video_kit.draw.creatures import Bird
    bird = Bird(x=200, y=150, scale=0.7, flap_speed=2.5)
    scene.add(BirdFlyer(bird, x_start=1400, x_end=-100, y=150,
                        t_start=1.0, t_end=5.0))

    # ── Title text ────────────────────────────────────────────────────────
    scene.add(Typewriter(
        "turtle_video_kit",
        x=640, y=120,
        t_start=0.3, t_end=1.5,
        font_size=64,
        color=(255, 255, 255),
        anchor="mm"
    ))

    scene.add(FadeInText(
        "模組化動畫工具庫",
        x=640, y=200,
        t_start=1.2, t_end=2.0,
        font_size=36,
        color=(200, 200, 255),
        anchor="mm",
        easing="ease_out"
    ))

    # Morph label
    scene.add(FadeInText(
        "圓形 → 正方形 (morphing)",
        x=640, y=440,
        t_start=1.5, t_end=2.2,
        font_size=28,
        color=(255, 215, 0),
        anchor="mm",
        t_fade_out_start=3.5, t_fade_out_end=4.0
    ))

    # ── Slide-in feature list ─────────────────────────────────────────────
    features = [
        ("Keyframe 插值 + Easing", 2.8),
        ("Shape Morphing", 3.1),
        ("Creature 動畫角色", 3.4),
        ("Transition 轉場效果", 3.7),
    ]
    for i, (text, t) in enumerate(features):
        scene.add(SlideInText(
            f"✦ {text}",
            x=200, y=300 + i * 45,
            t_start=t, t_end=t + 0.4,
            font_size=28,
            color=(180, 220, 180),
            direction="left",
            easing="ease_out"
        ))

    # ── Transitions ───────────────────────────────────────────────────────
    scene.add(FadeIn(t_start=0.0, t_end=0.5))
    scene.add(FadeOut(t_start=5.3, t_end=6.0))

    # ── Render ────────────────────────────────────────────────────────────
    output = OUTPUT_DIR / "demo.mp4"

    def progress(frame, total):
        pct = frame / total * 100
        bar = "#" * int(pct / 5) + "." * (20 - int(pct / 5))
        print(f"\r  [{bar}] {pct:.0f}%  ({frame}/{total})", end="", flush=True)

    print(f"\nRendering {scene}...")
    scene.render(str(output), on_progress=progress, preview_every=30)
    print(f"\nDone → {output}")
    return output


# ── Helpers for creature movement ────────────────────────────────────────────

from turtle_video_kit.core.canvas import Layer
from turtle_video_kit.core.keyframe import interpolate
from PIL import Image

class TurtleWalker(Layer):
    """Moves a Turtle's x position over time."""
    z_index = 20

    def __init__(self, turtle, x_start, x_end, t_start, t_end, easing="linear"):
        self.turtle = turtle
        self.x_start = x_start
        self.x_end = x_end
        self.t_start = t_start
        self.t_end = t_end
        self.easing = easing

    def is_active(self, frame_index, fps):
        return True

    def render_frame(self, frame_index, fps, canvas_size):
        t = frame_index / fps
        self.turtle.x = interpolate(self.x_start, self.x_end,
                                    self.t_start, self.t_end, t, self.easing)
        return self.turtle.render_frame(frame_index, fps, canvas_size)


class BirdFlyer(Layer):
    """Moves a Bird across the screen."""
    z_index = 22

    def __init__(self, bird, x_start, x_end, y, t_start, t_end, easing="linear"):
        self.bird = bird
        self.x_start = x_start
        self.x_end = x_end
        self.y = y
        self.t_start = t_start
        self.t_end = t_end
        self.easing = easing

    def is_active(self, frame_index, fps):
        t = frame_index / fps
        return self.t_start <= t <= self.t_end

    def render_frame(self, frame_index, fps, canvas_size):
        t = frame_index / fps
        self.bird.x = interpolate(self.x_start, self.x_end,
                                   self.t_start, self.t_end, t, self.easing)
        self.bird.y = self.y
        return self.bird.render_frame(frame_index, fps, canvas_size)


if __name__ == "__main__":
    make_demo()
