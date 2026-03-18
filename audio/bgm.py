# -*- coding: utf-8 -*-
"""
BGM synthesis — generate simple lo-fi background music with pydub.
No external files needed. Can also mix in a local audio file.
"""
from __future__ import annotations
import math
import os
import struct
import wave
from pathlib import Path
from typing import Optional, List, Tuple

BGM_CACHE_DIR = Path(__file__).parent.parent / "assets" / "bgm_cache"


# ── Simple sine-wave synthesizer (no pydub dependency) ───────────────────────

def _sine_wave(freq: float, duration: float, amplitude: float = 0.3,
               sample_rate: int = 44100) -> bytes:
    """Generate raw PCM bytes for a sine wave tone."""
    n_samples = int(sample_rate * duration)
    data = []
    for i in range(n_samples):
        t = i / sample_rate
        val = amplitude * math.sin(2 * math.pi * freq * t)
        # 16-bit signed PCM
        data.append(int(val * 32767))
    return struct.pack(f"<{n_samples}h", *data)


def _mix_pcm(tracks: List[bytes]) -> bytes:
    """Mix multiple PCM tracks by averaging samples."""
    if not tracks:
        return b""
    n = min(len(t) for t in tracks) // 2
    mixed = []
    for i in range(n):
        sample = sum(
            struct.unpack_from("<h", t, i * 2)[0] for t in tracks
        ) // len(tracks)
        mixed.append(max(-32768, min(32767, sample)))
    return struct.pack(f"<{n}h", *mixed)


def _write_wav(path: Path, pcm: bytes, sample_rate: int = 44100):
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)


# ── Chord progressions ────────────────────────────────────────────────────────

# Frequencies of notes (A4 = 440 Hz)
_NOTES = {
    "C3": 130.81, "D3": 146.83, "E3": 164.81, "F3": 174.61,
    "G3": 196.00, "A3": 220.00, "B3": 246.94,
    "C4": 261.63, "D4": 293.66, "E4": 329.63, "F4": 349.23,
    "G4": 392.00, "A4": 440.00, "B4": 493.88,
    "C5": 523.25, "D5": 587.33, "E5": 659.25,
}

PROGRESSIONS = {
    "lofi_chill": [
        ["C4", "E4", "G4"],     # Cmaj
        ["A3", "C4", "E4"],     # Am
        ["F3", "A3", "C4"],     # Fmaj
        ["G3", "B3", "D4"],     # Gmaj
    ],
    "upbeat": [
        ["C4", "E4", "G4"],
        ["G3", "B3", "D4"],
        ["A3", "C4", "E4"],
        ["F3", "A3", "C4"],
    ],
    "melancholy": [
        ["A3", "C4", "E4"],
        ["F3", "A3", "C4"],
        ["C4", "E4", "G4"],
        ["G3", "B3", "D4"],
    ],
    "mysterious": [
        ["D4", "F4", "A4"],
        ["B3", "D4", "F4"],
        ["G3", "B3", "D4"],
        ["A3", "C4", "E4"],
    ],
}


def make_bgm(duration: float, style: str = "lofi_chill",
             output_path: Optional[str] = None,
             tempo_bpm: float = 80.0,
             amplitude: float = 0.15,
             fade_out: float = 2.0) -> Path:
    """
    Generate a looping background music track.

    Args:
        duration:     Total length in seconds.
        style:        One of: lofi_chill, upbeat, melancholy, mysterious
        output_path:  Where to save. Auto-generated if None.
        tempo_bpm:    Beats per minute.
        amplitude:    Volume (0.0–1.0).
        fade_out:     Fade out duration at the end (seconds).

    Returns:
        Path to generated .wav file.
    """
    BGM_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        output_path = str(BGM_CACHE_DIR / f"bgm_{style}_{int(duration)}s.wav")

    out = Path(output_path)

    chord_duration = 60.0 / tempo_bpm * 4  # one chord per bar
    progression = PROGRESSIONS.get(style, PROGRESSIONS["lofi_chill"])
    sample_rate = 44100

    all_pcm = b""
    elapsed = 0.0

    while elapsed < duration:
        chord = progression[int(elapsed / chord_duration) % len(progression)]
        remaining = duration - elapsed
        seg_dur = min(chord_duration, remaining)

        tracks = [_sine_wave(_NOTES[note], seg_dur, amplitude, sample_rate)
                  for note in chord if note in _NOTES]
        mixed = _mix_pcm(tracks) if tracks else b"\x00" * int(seg_dur * sample_rate * 2)
        all_pcm += mixed
        elapsed += seg_dur

    # Apply fade-out
    if fade_out > 0:
        fade_samples = int(fade_out * sample_rate)
        total_samples = len(all_pcm) // 2
        fade_start = max(0, total_samples - fade_samples)
        data = list(struct.unpack(f"<{total_samples}h", all_pcm))
        for i in range(fade_start, total_samples):
            factor = 1.0 - (i - fade_start) / fade_samples
            data[i] = int(data[i] * factor)
        all_pcm = struct.pack(f"<{total_samples}h", *data)

    _write_wav(out, all_pcm, sample_rate)
    print(f"[BGM] Generated {style} BGM → {out}")
    return out


def mix_audio(voice_path: str, bgm_path: str, output_path: str,
              bgm_volume: float = 0.3,
              ffmpeg: str = "C:/Users/chewei/ffmpeg/bin/ffmpeg.exe") -> Path:
    """
    Mix a TTS voice track with a BGM track using ffmpeg.

    Args:
        voice_path:   Main voice audio (mp3/wav).
        bgm_path:     Background music (wav).
        output_path:  Output mixed audio path.
        bgm_volume:   BGM volume relative to voice (0.0–1.0).
    """
    import subprocess
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg, "-y",
        "-i", voice_path,
        "-i", bgm_path,
        "-filter_complex",
        f"[1:a]volume={bgm_volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first[out]",
        "-map", "[out]",
        "-c:a", "aac",
        str(out)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg mix failed:\n{result.stderr}")
    return out
