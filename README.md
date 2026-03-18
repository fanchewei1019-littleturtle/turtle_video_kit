# turtle_video_kit

A modular animation & video production toolkit for littleturtle AI.

## Demo

[![turtle_video_kit showcase](assets/demo_preview.gif)](https://github.com/fanchewei1019-littleturtle/turtle_video_kit/releases/download/v0.2.0/turtle_video_kit_showcase_v4.mp4)

> Click the GIF to download the full 33-second showcase video.
> Shape Morphing · Easing Curves · Programmatic Creatures · Text Animations · Motion Effects · Transitions · BGM Synthesis

## Philosophy

Not a one-click video maker — a **composable toolkit** where every element is independently tweakable.
Need a fade-out? Add `FadeOut()`. Need a circle morphing into a square? Add `ShapeMorph()`. Need a walking turtle? Use `creatures.Turtle()`.

## Structure

```
turtle_video_kit/
├── core/          # Canvas, Timeline, Keyframe interpolation, Renderer
├── anim/          # Transitions, Morphing, Motion, Effects
├── draw/          # Shapes, Creatures (programmatic animals), Text animation
├── audio/         # TTS wrapper, BGM synthesis
├── scene/         # Scene builder — assembles layers into a video
└── assets/        # Shared fonts, OpenMoji PNGs, creature sprites
```

## Quick Example

```python
from turtle_video_kit.core.canvas import Canvas
from turtle_video_kit.draw import shapes, creatures
from turtle_video_kit.anim import morph, transitions, motion
from turtle_video_kit.scene.builder import Scene

# Create a 5-second 1280x720 scene at 30fps
scene = Scene(width=1280, height=720, fps=30, duration=5.0)

# Add a circle that morphs into a square over 1.5s, then fades out
circle = shapes.Circle(cx=640, cy=360, r=80, color="#FFD700")
square = shapes.Rect(cx=640, cy=360, w=160, h=160, color="#FFD700")
scene.add(morph.ShapeMorph(circle, square, start=0.5, end=2.0, easing="ease_in_out"))
scene.add(transitions.FadeOut(start=4.0, end=5.0))

# Add a turtle walking across the screen
turtle = creatures.Turtle(x=50, y=600, scale=1.0)
scene.add(motion.MoveTo(turtle, target_x=1200, start=0, end=5.0, easing="linear"))

# Render
scene.render("output.mp4")
```

## Asset Integration

```python
from turtle_video_kit.draw.assets import AssetManager

am = AssetManager()
am.load_local("my_logo.png")           # local file
am.fetch_openmoji("rocket")            # auto-download from OpenMoji
am.fetch_unsplash("mountain landscape") # fetch free photo from Unsplash
```

## Requirements

- Python 3.9+
- Pillow, numpy, pydub, requests
- ffmpeg (in PATH or configured)
- edge-tts (for TTS)
