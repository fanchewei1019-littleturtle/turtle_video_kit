# -*- coding: utf-8 -*-
"""
turtle_video_kit SHOWCASE DEMO
全功能炫技 — 展示每個模組的能力
"""
import sys
import math
import struct
import requests
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent.parent))

from turtle_video_kit.scene.builder import Scene, Video
from turtle_video_kit.core.canvas import Layer
from turtle_video_kit.core.keyframe import interpolate, alpha_at, EASINGS
from turtle_video_kit.anim.transitions import FadeIn, FadeOut, SlideIn, FadeTo
from turtle_video_kit.anim.morph import (ShapeMorph, ColorMorph,
    circle_polygon, rect_polygon, star_polygon, _resample)
from turtle_video_kit.anim.motion import FadeLayer, RotateAnim, ScaleAnim, Shake
from turtle_video_kit.draw.shapes import (GradientBG, Circle, Rect, Line,
    Arrow, Polygon)
from turtle_video_kit.draw.creatures import Turtle, Dog, Bird
from turtle_video_kit.draw.text import (FadeInText, Typewriter, SlideInText,
    TextLabel)
from turtle_video_kit.audio.bgm import make_bgm

OUTPUT_DIR = Path(__file__).parent / "test_output"
OUTPUT_DIR.mkdir(exist_ok=True)

WEBHOOK_URL = "https://discord.com/api/webhooks/1481265314594558114/hCGrWmn0qFAGAexuNtHkcluLcYhhvEgo2Dat4o5AjTFpveipQnn1K5h6tcmSFuUFjLMn"
W, H = 1280, 720


# ── Helpers ───────────────────────────────────────────────────────────────────

class CreatureWalker(Layer):
    """
    Animates creature x position over time.
    Inspects the creature at construction time and sets the correct facing direction
    before any frame is rendered — no mid-animation flip.
    """
    def __init__(self, creature, x_start, x_end, y, t_start, t_end,
                 easing="linear", z=20):
        self.creature = creature
        self.x_start = x_start
        self.x_end = x_end
        self.y = y
        self.t_start = t_start
        self.t_end = t_end
        self.easing = easing
        self.z_index = z
        moving_left = x_end < x_start
        # Set direction/flip on the creature ONCE at construction
        if hasattr(creature, 'direction'):
            creature.direction = "left" if moving_left else "right"
        if hasattr(creature, 'flip'):
            creature.flip = moving_left

    def is_active(self, fi, fps):
        t = fi / fps
        return self.t_start <= t <= self.t_end

    def render_frame(self, fi, fps, size):
        t = fi / fps
        self.creature.x = interpolate(self.x_start, self.x_end,
                                      self.t_start, self.t_end, t, self.easing)
        self.creature.y = self.y
        return self.creature.render_frame(fi, fps, size)


class DrawingLine(Layer):
    """A line that draws itself progressively."""
    z_index = 15

    def __init__(self, x0, y0, x1, y1, t_start, t_end,
                 color=(255,255,255), width=4):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.t_start, self.t_end = t_start, t_end
        self.color = color
        self.width = width

    def is_active(self, fi, fps):
        return fi / fps >= self.t_start

    def render_frame(self, fi, fps, size):
        t = fi / fps
        p = alpha_at(self.t_start, self.t_end, t, "ease_out")
        ex = self.x0 + (self.x1 - self.x0) * p
        ey = self.y0 + (self.y1 - self.y0) * p
        img = Image.new("RGBA", size, (0,0,0,0))
        d = ImageDraw.Draw(img)
        d.line([self.x0, self.y0, ex, ey], fill=(*self.color, 255), width=self.width)
        return img


class ParticleBurst(Layer):
    """Radial particle burst at a point."""
    z_index = 30

    def __init__(self, cx, cy, t_peak, n=20, radius=120,
                 color=(255,215,0), duration=0.8):
        self.cx, self.cy = cx, cy
        self.t_peak = t_peak
        self.t_start = t_peak
        self.t_end = t_peak + duration
        self.n = n
        self.radius = radius
        self.color = color
        self.duration = duration

    def is_active(self, fi, fps):
        t = fi / fps
        return self.t_start <= t <= self.t_end

    def render_frame(self, fi, fps, size):
        t = fi / fps
        p = (t - self.t_start) / self.duration
        fade = 1.0 - p
        img = Image.new("RGBA", size, (0,0,0,0))
        d = ImageDraw.Draw(img)
        for i in range(self.n):
            angle = 2 * math.pi * i / self.n
            r = self.radius * p
            x = self.cx + r * math.cos(angle)
            y = self.cy + r * math.sin(angle)
            pr = max(1, int(5 * (1 - p)))
            alpha = int(255 * fade)
            d.ellipse([x-pr, y-pr, x+pr, y+pr],
                      fill=(*self.color, alpha))
        return img


class SectionLabel(Layer):
    """Bottom-left section title bar."""
    z_index = 80

    def __init__(self, text, t_start, t_end,
                 color=(255,215,0), bg=(30,30,50)):
        from turtle_video_kit.draw.text import _load_font
        self.text = text
        self.t_start = t_start
        self.t_end = t_end
        self.color = color
        self.bg = bg
        self._font = _load_font(26)

    def is_active(self, fi, fps):
        t = fi / fps
        return self.t_start - 0.3 <= t <= self.t_end

    def render_frame(self, fi, fps, size):
        W, H = size
        t = fi / fps
        alpha = min(
            alpha_at(self.t_start - 0.3, self.t_start, t, "ease_out"),
            1.0 - alpha_at(self.t_end - 0.3, self.t_end, t, "ease_in")
        )
        if alpha <= 0:
            return None
        img = Image.new("RGBA", size, (0,0,0,0))
        d = ImageDraw.Draw(img)
        bar_h = 44
        d.rectangle([0, H - bar_h, W, H],
                    fill=(*self.bg, int(200 * alpha)))
        d.text((20, H - bar_h + 10), f"// {self.text}",
               font=self._font, fill=(*self.color, int(255 * alpha)))
        return img


class EasingGraph(Layer):
    """Draws easing curves animating in."""
    z_index = 12

    def __init__(self, t_start, t_end):
        self.t_start = t_start
        self.t_end = t_end
        from turtle_video_kit.draw.text import _load_font
        self._font = _load_font(18)

    def is_active(self, fi, fps):
        return fi / fps >= self.t_start

    def render_frame(self, fi, fps, size):
        t = fi / fps
        progress = alpha_at(self.t_start, self.t_end, t, "ease_out")
        img = Image.new("RGBA", size, (0,0,0,0))
        d = ImageDraw.Draw(img)

        curves = [
            ("ease_out",    (100, 200), (255, 100, 150)),
            ("ease_in_out", (280, 200), (100, 200, 255)),
            ("bounce",      (460, 200), (100, 255, 150)),
            ("elastic",     (640, 200), (255, 150, 50)),
            ("spring",      (820, 200), (200, 100, 255)),
        ]
        gw, gh = 120, 80
        for name, (ox, oy), col in curves:
            fn = EASINGS[name]
            pts = []
            n = int(40 * progress)
            for i in range(max(2, n)):
                px = i / 39
                py = fn(px)
                sx = ox + px * gw
                sy = oy + gh - py * gh
                pts.append((sx, sy))
            if len(pts) >= 2:
                d.line(pts, fill=(*col, 200), width=3)
            d.rectangle([ox, oy - 5, ox + gw, oy + gh + 5],
                        outline=(*col, 80), width=1)
            d.text((ox + gw//2, oy + gh + 12), name,
                   font=self._font, fill=(*col, int(200 * progress)),
                   anchor="mt")
        return img


# ── SCENE 1: 開場 + Typewriter + Gradient (4s) ───────────────────────────────
def scene_intro() -> Scene:
    s = Scene(W, H, fps=30, duration=4.0, background=(10, 10, 20))

    s.add(ColorMorph((10,10,20), (20,15,40), 0, 4.0))

    # Grid lines bg
    s.add(GridLines(0, 4.0))

    s.add(Typewriter("turtle_video_kit", W//2, H//2 - 60,
                     t_start=0.4, t_end=2.0,
                     font_size=72, color=(255,215,0), anchor="mm"))

    s.add(FadeInText("SHOWCASE DEMO", W//2, H//2 + 20,
                     t_start=1.6, t_end=2.4,
                     font_size=36, color=(180,180,255), anchor="mm"))

    s.add(FadeInText("全功能展示", W//2, H//2 + 70,
                     t_start=2.0, t_end=2.8,
                     font_size=28, color=(150,150,200), anchor="mm"))

    # Particle burst on title appear
    s.add(ParticleBurst(W//2, H//2 - 60, t_peak=2.0, n=24,
                        radius=140, color=(255,215,0)))

    s.add(FadeIn(0, 0.5))
    s.add(FadeOut(3.5, 4.0, color=(10,10,20)))
    s.add(SectionLabel("INTRO", 0.5, 3.5))
    return s


class GridLines(Layer):
    z_index = 1
    def __init__(self, t_start, t_end):
        self.t_start, self.t_end = t_start, t_end

    def is_active(self, fi, fps):
        return True

    def render_frame(self, fi, fps, size):
        W, H = size
        t = fi / fps
        alpha = int(30 * alpha_at(self.t_start, self.t_start + 1.0, t))
        img = Image.new("RGBA", size, (0,0,0,0))
        d = ImageDraw.Draw(img)
        for x in range(0, W, 80):
            d.line([x, 0, x, H], fill=(100,100,200,alpha), width=1)
        for y in range(0, H, 80):
            d.line([0, y, W, y], fill=(100,100,200,alpha), width=1)
        return img


# ── SCENE 2: Easing 曲線 + ShapeMorph (5s) ───────────────────────────────────
def scene_morph() -> Scene:
    s = Scene(W, H, fps=30, duration=5.0, background=(15, 12, 30))

    s.add(GradientBG((15,12,30), (30,20,50)))

    # Title
    s.add(SlideInText("Shape Morphing", W//2, 60,
                      t_start=0.2, t_end=0.8,
                      font_size=44, color=(255,215,0), anchor="mm",
                      direction="top"))

    # Easing graph at top
    s.add(EasingGraph(t_start=0.3, t_end=1.5))

    # Shape morphs: each morph only visible in its own time window
    # Use FadeLayer to control visibility, preventing stacking
    cx_m, cy_m = 220, 430
    shapes = [
        circle_polygon(cx_m, cy_m, 90),
        rect_polygon(cx_m, cy_m, 180, 180),
        star_polygon(cx_m, cy_m, 90, 45, 5),
        _resample(circle_polygon(cx_m, cy_m, 90, n=3), 64),  # triangle
        circle_polygon(cx_m, cy_m, 90),
    ]
    labels_m = ["circle", "square", "star", "triangle", "circle"]
    t_step = 0.8
    for i in range(len(shapes) - 1):
        ts = 0.5 + i * t_step
        te = ts + t_step
        morph_layer = ShapeMorph(shapes[i], shapes[i+1],
                                 t_start=ts, t_end=te,
                                 fill=(255,100,100), outline=(255,200,200),
                                 easing="ease_in_out")
        # Wrap in FadeLayer so this morph disappears when the next one takes over
        s.add(FadeLayer(morph_layer, 1.0, 1.0, ts, ts,
                        hold_after=False if i < len(shapes)-2 else True))

    # Label: show current shape name, then "→ next"
    for i in range(len(labels_m) - 1):
        ts = 0.5 + i * t_step
        te = ts + t_step
        # Current shape label (shown at start of window)
        s.add(FadeInText(labels_m[i], cx_m, cy_m - 110,
                         t_start=ts, t_end=ts + 0.25,
                         t_fade_out_start=ts + 0.3, t_fade_out_end=ts + 0.5,
                         font_size=28, color=(255, 220, 180), anchor="mm"))
        # Arrow label during morph
        s.add(FadeInText(f"→ {labels_m[i+1]}",
                         cx_m, cy_m + 115,
                         t_start=ts + 0.3, t_end=ts + 0.6,
                         t_fade_out_start=te - 0.2, t_fade_out_end=te,
                         font_size=24, color=(255,180,180), anchor="mm"))

    # ColorMorph: background slowly shifts
    s.add(ColorMorph((15,12,30), (10,30,25), 1.5, 4.5))

    # Right side: multiple morphs simultaneously
    offsets = [(580, 430), (780, 430), (980, 430)]
    colors_r = [(100,200,255), (150,255,150), (255,150,255)]
    delays   = [0.3, 0.6, 0.9]
    for (ox, oy), col, delay in zip(offsets, colors_r, delays):
        cp = circle_polygon(ox, oy, 55)
        rp = rect_polygon(ox, oy, 110, 110)
        sp = star_polygon(ox, oy, 55, 25, 6)
        s.add(ShapeMorph(cp, sp, 1.0+delay, 2.5+delay,
                         fill=col, easing="elastic"))
        s.add(ShapeMorph(sp, rp, 2.5+delay, 3.5+delay,
                         fill=col, easing="bounce"))

    s.add(FadeIn(0, 0.3, color=(10,10,20)))
    s.add(FadeOut(4.6, 5.0, color=(10,10,20)))
    s.add(SectionLabel("EASING + SHAPE MORPHING", 0.3, 4.6))
    return s


# ── SCENE 3: Creatures (5s) ───────────────────────────────────────────────────
def scene_creatures() -> Scene:
    s = Scene(W, H, fps=30, duration=5.0, background=(30, 50, 30))

    s.add(GradientBG((20,40,20), (50,80,40)))

    # Ground line
    s.add(Rect(W//2, H-30, W, 60, color=(40,70,30), t_start=0))

    s.add(SlideInText("Programmatic Creatures", W//2, 60,
                      t_start=0.2, t_end=0.8,
                      font_size=44, color=(255,240,150), anchor="mm",
                      direction="top"))

    # Turtle walks across
    turtle = Turtle(scale=1.2, walk_cycle=True, direction="right")
    s.add(CreatureWalker(turtle, -120, W+120, H-120, 0.3, 4.8,
                         easing="linear", z=20))

    # Dog slides in from right, stops in middle (facing left = towards viewer)
    dog = Dog(scale=1.0, wag=True)
    s.add(CreatureWalker(dog, W+100, W//2+100, H-110, 0.6, 2.0,
                         easing="ease_out", z=21))
    # Once stopped, keep it still (same start/end x so no direction conflict)
    class StillCreature(Layer):
        z_index = 21
        def __init__(self, creature, x, y, t_start):
            self.creature = creature
            self.x = x
            self.y = y
            self.t_start = t_start
        def is_active(self, fi, fps):
            return fi / fps >= self.t_start
        def render_frame(self, fi, fps, size):
            self.creature.x = self.x
            self.creature.y = self.y
            return self.creature.render_frame(fi, fps, size)
    s.add(StillCreature(dog, W//2+100, H-110, t_start=2.0))

    # Birds flying in formation
    for i, (y_off, delay) in enumerate([(150, 0.5), (120, 0.8), (180, 1.1)]):
        bird = Bird(scale=0.8, flap_speed=2.5+i*0.3,
                    color=(80+i*30, 120+i*20, 200-i*30))
        s.add(CreatureWalker(bird, W+80, -80, y_off, delay, 4.5,
                             easing="linear", z=22))

    # Labels pop in
    labels = [
        ("Turtle — walk cycle + blink", 200, H-170, 1.0),
        ("Dog — wag tail", W//2+100, H-160, 2.2),
        ("Birds — flap formation", W//2, 220, 1.5),
    ]
    for text, lx, ly, lt in labels:
        s.add(FadeInText(text, lx, ly, t_start=lt, t_end=lt+0.5,
                         font_size=22, color=(255,255,200), anchor="mm"))

    # Particle burst when dog arrives
    s.add(ParticleBurst(W//2+100, H-110, t_peak=2.0, n=16,
                        color=(255,220,100), radius=80))

    s.add(FadeIn(0, 0.3, color=(10,10,20)))
    s.add(FadeOut(4.6, 5.0, color=(10,10,20)))
    s.add(SectionLabel("PROGRAMMATIC CREATURES", 0.3, 4.6))
    return s


# ── SCENE 4: Text Animations (4s) ────────────────────────────────────────────
def scene_text() -> Scene:
    s = Scene(W, H, fps=30, duration=4.0, background=(10, 15, 35))

    s.add(GradientBG((10,15,35), (25,10,45)))

    s.add(SlideInText("Text Animations", W//2, 60,
                      t_start=0.2, t_end=0.8,
                      font_size=44, color=(150,255,200), anchor="mm",
                      direction="top"))

    # Typewriter
    s.add(FadeInText("Typewriter:", 60, 140, t_start=0.3, t_end=0.6,
                     font_size=26, color=(180,180,180)))
    s.add(Typewriter("小烏龜 AI 助手，準備完畢！",
                     220, 140, t_start=0.6, t_end=2.0,
                     font_size=32, color=(255,240,100), cursor=True))

    # Slide from each direction
    directions_text = [
        ("left",   "從左滑入 ←",   200, 240),
        ("right",  "→ 從右滑入",   700, 290),
        ("top",    "從上落下",      400, 340),
        ("bottom", "從下升起",      600, 390),
    ]
    for i, (direc, text, tx, ty) in enumerate(directions_text):
        s.add(FadeInText(f"SlideIn {direc}:", tx - 150 if direc in ("left","top") else tx-180,
                         ty, t_start=1.2+i*0.2, t_end=1.4+i*0.2,
                         font_size=20, color=(150,150,150)))
        s.add(SlideInText(text, tx, ty, t_start=1.4+i*0.2, t_end=1.8+i*0.2,
                          font_size=28, color=(100,200,255),
                          direction=direc, slide_distance=50))

    # Fade in sequence
    words = ["模", "組", "化", "·", "可", "組", "合", "·", "易", "修", "改"]
    for i, w in enumerate(words):
        s.add(FadeInText(w, 80 + i * 105, 480, t_start=2.0+i*0.08, t_end=2.3+i*0.08,
                         font_size=40, color=(255, 150+i*8, 100+i*10),
                         anchor="mm", easing="ease_out"))

    # Shadow text
    s.add(TextLabel("shadow + outline", W//2, 570, font_size=36,
                    color=(255,255,255), shadow=True,
                    shadow_color=(100,50,200), shadow_offset=(4,4), anchor="mm",
                    t_start=2.8))

    s.add(FadeIn(0, 0.3, color=(10,10,20)))
    s.add(FadeOut(3.6, 4.0, color=(10,10,20)))
    s.add(SectionLabel("TEXT ANIMATIONS", 0.3, 3.6))
    return s


# ── SCENE 5: Motion + Effects (5s) ───────────────────────────────────────────
def scene_motion() -> Scene:
    s = Scene(W, H, fps=30, duration=5.0, background=(20, 10, 30))

    s.add(GradientBG((20,10,30), (10,20,40)))

    s.add(SlideInText("Motion + Effects", W//2, 60,
                      t_start=0.2, t_end=0.8,
                      font_size=44, color=(255,150,255), anchor="mm",
                      direction="top"))

    # RotateAnim — spinning star
    star_pts = star_polygon(200, 320, 80, 35, 6)
    star_layer = Polygon(star_pts, color=(255,200,50), alpha=220)
    s.add(RotateAnim(star_layer, 0, 360, 0.5, 4.5, center=(200,320),
                     easing="linear"))
    s.add(FadeInText("RotateAnim", 200, 430, t_start=0.5, t_end=1.0,
                     font_size=22, color=(255,200,50), anchor="mm"))

    # ScaleAnim — pulsing circle
    pulse_circle = Circle(450, 320, 70, color=(100,200,255), alpha=200)
    s.add(ScaleAnim(pulse_circle, 0.5, 1.2, 0.8, 2.0, anchor=(0.35,0.44),
                    easing="elastic"))
    s.add(ScaleAnim(pulse_circle, 1.2, 0.8, 2.0, 3.0, anchor=(0.35,0.44),
                    easing="ease_in_out"))
    s.add(FadeInText("ScaleAnim", 450, 430, t_start=1.0, t_end=1.4,
                     font_size=22, color=(100,200,255), anchor="mm"))

    # FadeLayer — ghost shape
    ghost = Rect(700, 320, 130, 130, color=(200,100,255),
                 radius=20, outline=(255,150,255), outline_width=3)
    s.add(FadeLayer(ghost, 0.0, 1.0, 1.0, 2.0, easing="ease_in"))
    s.add(FadeLayer(ghost, 1.0, 0.0, 3.0, 4.0, easing="ease_out", hold_after=False))
    s.add(FadeInText("FadeLayer", 700, 430, t_start=1.5, t_end=1.9,
                     font_size=22, color=(200,100,255), anchor="mm"))

    # Shake effect
    shake_rect = Rect(950, 320, 130, 90, color=(255,80,80),
                      outline=(255,150,150), outline_width=3, radius=10)
    s.add(Shake(shake_rect, t_start=2.5, t_end=3.8, intensity=10, frequency=18))
    s.add(FadeInText("Shake", 950, 430, t_start=2.2, t_end=2.6,
                     font_size=22, color=(255,80,80), anchor="mm"))

    # Drawing lines
    for i, (x0,y0,x1,y1,col) in enumerate([
        (80, 520, 400, 520, (255,200,100)),
        (80, 560, 600, 560, (100,255,200)),
        (80, 600, 800, 600, (200,100,255)),
    ]):
        s.add(DrawingLine(x0,y0,x1,y1, 3.5+i*0.2, 4.2+i*0.2,
                          color=col, width=4))

    # Arrows
    s.add(Arrow(W//2-100, 640, W//2+100, 640, color=(255,255,100), width=4,
                t_start=4.0))
    s.add(FadeInText("Arrow + Lines", W//2, 680, t_start=4.2, t_end=4.5,
                     font_size=22, color=(255,255,100), anchor="mm"))

    # Particle bursts
    s.add(ParticleBurst(200, 320, t_peak=0.5, n=18, color=(255,215,0)))
    s.add(ParticleBurst(700, 320, t_peak=1.0, n=18, color=(200,100,255)))
    s.add(ParticleBurst(950, 320, t_peak=2.5, n=18, color=(255,80,80)))

    s.add(FadeIn(0, 0.3, color=(10,10,20)))
    s.add(FadeOut(4.6, 5.0, color=(10,10,20)))
    s.add(SectionLabel("MOTION + EFFECTS", 0.3, 4.6))
    return s


# ── SCENE 6: Transitions showcase (6s, 3 clear acts) ─────────────────────────
def scene_transitions() -> Scene:
    s = Scene(W, H, fps=30, duration=6.0, background=(15, 25, 15))
    s.add(GradientBG((15,25,15), (25,40,25)))

    # ── Act 1 (0–2.2s): 5 named boxes fade in one by one ─────────────────────
    s.add(SlideInText("Transitions", W//2, 55,
                      t_start=0.2, t_end=0.7,
                      font_size=44, color=(150,255,150), anchor="mm",
                      direction="top"))

    boxes = [
        (160,  330, (100,200,120), "FadeIn"),
        (380,  330, (100,150,220), "SlideIn"),
        (600,  330, (220,160,80),  "FadeTo"),
        (820,  330, (180,100,220), "FadeOut"),
        (1040, 330, (220,100,140), "ZoomPulse"),
    ]
    for i, (bx, by, col, label) in enumerate(boxes):
        box = Rect(bx, by, 170, 110, color=col, radius=14,
                   outline=(255,255,255), outline_width=2)
        s.add(FadeLayer(box, 0.0, 1.0, 0.4 + i*0.22, 0.8 + i*0.22))
        s.add(FadeInText(label, bx, by + 80,
                         t_start=0.8 + i*0.22, t_end=1.1 + i*0.22,
                         font_size=20, color=(230,230,230), anchor="mm"))

    # ── Act 2 (2.4–4.2s): Live SlideIn demo — panel sweeps & reveals ──────────
    # Boxes fade out first
    for i, (bx, by, col, _) in enumerate(boxes):
        box_fade = Rect(bx, by, 170, 110, color=col, radius=14)
        s.add(FadeLayer(box_fade, 1.0, 0.0, 2.0, 2.4, hold_after=False))

    # Dark panel slides in from left (z=850), covers screen, holds, retreats
    s.add(SlideIn(2.4, 2.9, 3.6, color=(20, 60, 50), direction="left"))

    # Text ON TOP of the panel (z_index must be > 850)
    class TopText(Layer):
        z_index = 901
        def __init__(self, text, x, y, t_start, t_end, font_size=44,
                     color=(255,255,255)):
            from turtle_video_kit.draw.text import _load_font
            self.text = text
            self.x, self.y = x, y
            self.t_start, self.t_end = t_start, t_end
            self.color = color
            self._font = _load_font(font_size)
        def is_active(self, fi, fps):
            t = fi / fps
            return self.t_start <= t <= self.t_end
        def render_frame(self, fi, fps, size):
            from PIL import Image, ImageDraw
            from turtle_video_kit.core.keyframe import alpha_at
            t = fi / fps
            a = min(alpha_at(self.t_start, self.t_start+0.3, t),
                    1.0 - alpha_at(self.t_end-0.3, self.t_end, t))
            img = Image.new("RGBA", size, (0,0,0,0))
            d = ImageDraw.Draw(img)
            d.text((self.x, self.y), self.text, font=self._font,
                   fill=(*self.color, int(a*255)), anchor="mm")
            return img

    s.add(TopText("SlideIn  — 面板從左掃入", W//2, H//2 - 30,
                  t_start=2.9, t_end=3.5, font_size=38, color=(200,255,200)))
    s.add(TopText("panel 完全覆蓋畫面", W//2, H//2 + 30,
                  t_start=3.0, t_end=3.5, font_size=26, color=(150,220,150)))

    # ── Act 3 (4.0–5.6s): FadeTo demo — clean flash then recover ─────────────
    s.add(FadeInText("FadeTo — 畫面閃黑再回來", W//2, H//2,
                     t_start=4.0, t_end=4.4,
                     font_size=34, color=(255,255,180), anchor="mm"))
    # FadeTo black at 4.6, recover by 5.1
    s.add(FadeTo(4.6, 4.9, (15,25,15), (0,0,0), easing="ease_in"))
    s.add(FadeTo(4.9, 5.2, (0,0,0), (15,25,15), easing="ease_out"))

    s.add(FadeIn(0, 0.4, color=(10,10,20)))
    s.add(FadeOut(5.5, 6.0))
    s.add(SectionLabel("TRANSITIONS", 0.3, 5.5))
    return s


# ── SCENE 7: 結尾 (4s) ───────────────────────────────────────────────────────
def scene_outro() -> Scene:
    s = Scene(W, H, fps=30, duration=4.0, background=(10, 10, 20))

    s.add(ColorMorph((10,10,20), (5,5,15), 0, 4.0))
    s.add(GridLines(0, 4.0))

    # Title at top — well above the feature list
    s.add(FadeInText("turtle_video_kit", W//2, 70,
                     t_start=0.1, t_end=0.5,
                     font_size=52, color=(255,215,0), anchor="mm"))
    s.add(ParticleBurst(W//2, 70, t_peak=0.5, n=24,
                        color=(255,215,0), radius=160))

    # Divider line
    s.add(DrawingLine(100, 115, W-100, 115, 0.5, 0.9,
                      color=(255,215,0), width=2))

    # Feature list below divider — 2 columns layout
    col1 = [
        "Keyframe  |  7 Easings",
        "ShapeMorph  |  ColorMorph",
        "Typewriter  |  SlideIn",
        "RotateAnim  |  ScaleAnim",
    ]
    col2 = [
        "Turtle  |  Dog  |  Bird",
        "FadeIn  |  FadeOut  |  FadeTo",
        "Shake  |  ParticleBurst",
        "BGM Synth  |  AssetManager",
    ]
    for i, feat in enumerate(col1):
        s.add(FadeInText(feat, W//4, 180 + i*80,
                         t_start=0.6+i*0.1, t_end=0.9+i*0.1,
                         font_size=22, color=(180,200,255), anchor="mm"))
    for i, feat in enumerate(col2):
        s.add(FadeInText(feat, W*3//4, 180 + i*80,
                         t_start=0.7+i*0.1, t_end=1.0+i*0.1,
                         font_size=22, color=(200,255,180), anchor="mm"))

    # Bottom tagline
    s.add(SlideInText("v0.1.0  |  by littleturtle", W//2, H - 60,
                      t_start=1.8, t_end=2.2,
                      font_size=24, color=(150,150,180), anchor="mm",
                      direction="bottom"))

    s.add(FadeIn(0, 0.3, color=(10,10,20)))
    s.add(FadeOut(3.5, 4.0))
    return s


# ── Build + Render + Discord ──────────────────────────────────────────────────

def send_to_discord(video_path: Path, message: str):
    print(f"\nSending to Discord...")
    with open(video_path, "rb") as f:
        response = requests.post(
            WEBHOOK_URL,
            data={"content": message},
            files={"file": (video_path.name, f, "video/mp4")}
        )
    if response.status_code in (200, 204):
        print("Discord: sent!")
    else:
        print(f"Discord error: {response.status_code} {response.text[:200]}")


def main():
    print("=== turtle_video_kit SHOWCASE DEMO ===\n")

    # Generate BGM
    print("[1/9] Generating BGM...")
    bgm_path = make_bgm(27.0, style="lofi_chill", amplitude=0.12, fade_out=3.0)

    # Build scenes
    print("[2/9] Building scenes...")
    scenes_data = [
        ("INTRO",        scene_intro,       4.0),
        ("MORPH",        scene_morph,       5.0),
        ("CREATURES",    scene_creatures,   5.0),
        ("TEXT",         scene_text,        4.0),
        ("MOTION",       scene_motion,      5.0),
        ("TRANSITIONS",  scene_transitions, 4.0),
        ("OUTRO",        scene_outro,       3.5),
    ]

    video = Video()
    for i, (name, builder, _) in enumerate(scenes_data):
        print(f"[{i+3}/9] Rendering scene: {name}...")
        scene = builder()
        tmp_out = OUTPUT_DIR / f"showcase_{name.lower()}.mp4"
        total = scene.timeline.total_frames

        def make_progress(scene_name):
            def progress(frame, total):
                pct = frame / total * 100
                bar = "#" * int(pct / 5) + "." * (20 - int(pct / 5))
                print(f"\r  {scene_name} [{bar}] {pct:.0f}%", end="", flush=True)
            return progress

        scene.render(str(tmp_out), on_progress=make_progress(name))
        print()
        video.append(scene)

    # Final render with BGM
    print("\n[9/9] Concatenating + mixing BGM...")
    final_output = OUTPUT_DIR / "turtle_video_kit_showcase.mp4"

    # Render all scenes to individual files and concat
    import subprocess, tempfile
    FFMPEG = "C:/Users/chewei/ffmpeg/bin/ffmpeg.exe"

    scene_files = []
    for name, _, _ in scenes_data:
        scene_files.append(OUTPUT_DIR / f"showcase_{name.lower()}.mp4")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        concat_list = tmp_path / "concat.txt"
        with open(concat_list, "w") as f:
            for sf in scene_files:
                f.write(f"file '{sf.as_posix()}'\n")

        # Concat video
        concat_out = tmp_path / "concat.mp4"
        subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0",
                        "-i", str(concat_list), "-c", "copy", str(concat_out)],
                       capture_output=True)

        # Mix with BGM
        subprocess.run([
            FFMPEG, "-y",
            "-i", str(concat_out),
            "-i", str(bgm_path),
            "-filter_complex", "[1:a]volume=0.25[bgm];[bgm]aloop=loop=-1:size=2e+09[loop];[loop]atrim=duration=27[trimmed]",
            "-map", "0:v", "-map", "[trimmed]",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-shortest",
            str(final_output)
        ], capture_output=True)

    if not final_output.exists() or final_output.stat().st_size < 100000:
        print("ERROR: final output missing or too small, check ffmpeg concat")
        return

    file_size = final_output.stat().st_size / 1024 / 1024
    print(f"\nDone! Output: {final_output} ({file_size:.1f} MB)")

    # Send to Discord — exactly once
    send_to_discord(final_output,
        "**turtle_video_kit Showcase Demo**\n"
        "全功能炫技展示 — Morphing / Creatures / Text / Motion / Transitions / BGM\n"
        "`v0.1.0` | by littleturtle")


if __name__ == "__main__":
    main()
