# -*- coding: utf-8 -*-
"""
TTS wrapper — generate speech audio and return (path, duration).
Uses edge-tts, same as existing video scripts.
"""
from __future__ import annotations
import os
import subprocess
from pathlib import Path
from typing import Tuple, Optional

EDGE_TTS = os.environ.get(
    "EDGE_TTS_PATH",
    "C:/Users/chewei/anaconda3/envs/workspace/Scripts/edge-tts.exe"
)
FFMPEG = os.environ.get(
    "FFMPEG_PATH",
    "C:/Users/chewei/ffmpeg/bin/ffmpeg.exe"
)
DEFAULT_VOICE = "zh-TW-HsiaoChenNeural"
DEFAULT_RATE = "+25%"


def _get_duration(audio_path: Path) -> float:
    """Use ffmpeg to get audio duration in seconds."""
    result = subprocess.run(
        [FFMPEG, "-i", str(audio_path), "-f", "null", "-"],
        capture_output=True, text=True, errors="replace"
    )
    for line in result.stderr.split("\n"):
        if "Duration" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            return float(h) * 3600 + float(m) * 60 + float(s)
    return 3.0


def make_tts(text: str, output_path: str,
             voice: str = DEFAULT_VOICE,
             rate: str = DEFAULT_RATE,
             force: bool = False) -> Tuple[Path, float]:
    """
    Generate TTS audio.

    Args:
        text:        The text to speak.
        output_path: Where to save the .mp3 file.
        voice:       edge-tts voice name.
        rate:        Speed adjustment (e.g. "+25%", "-10%").
        force:       Re-generate even if file already exists.

    Returns:
        (path, duration_seconds)
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not out.exists() or force:
        subprocess.run(
            [EDGE_TTS, "--voice", voice, "--text", text,
             "--rate", rate, "--write-media", str(out)],
            check=True
        )

    duration = _get_duration(out)
    return out, duration


def make_tts_batch(texts: list, output_dir: str,
                   prefix: str = "s",
                   voice: str = DEFAULT_VOICE,
                   rate: str = DEFAULT_RATE,
                   force: bool = False) -> list:
    """
    Generate TTS for a list of texts.

    Returns:
        List of (path, duration) tuples, one per text.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for i, text in enumerate(texts):
        path = out_dir / f"{prefix}{i:02d}.mp3"
        results.append(make_tts(text, str(path), voice, rate, force))
    return results


# ── Available voices ──────────────────────────────────────────────────────────
VOICES = {
    "zh-TW-female": "zh-TW-HsiaoChenNeural",
    "zh-TW-male":   "zh-TW-YunJheNeural",
    "zh-CN-female": "zh-CN-XiaoxiaoNeural",
    "en-US-female": "en-US-JennyNeural",
    "en-US-male":   "en-US-GuyNeural",
}
