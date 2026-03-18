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


# ── Simple synthesizers ────────────────────────────────────────────────────────

def _sine_wave(freq: float, duration: float, amplitude: float = 0.3,
               sample_rate: int = 44100) -> bytes:
    n_samples = int(sample_rate * duration)
    data = [int(amplitude * math.sin(2 * math.pi * freq * i / sample_rate) * 32767)
            for i in range(n_samples)]
    return struct.pack(f"<{n_samples}h", *data)


def _triangle_wave(freq: float, duration: float, amplitude: float = 0.25,
                   sample_rate: int = 44100) -> bytes:
    """Triangle wave — warmer than sine, richer harmonics."""
    n_samples = int(sample_rate * duration)
    period = sample_rate / freq
    data = []
    for i in range(n_samples):
        phase = (i % period) / period  # 0..1
        val = (2 * abs(2 * phase - 1) - 1) * amplitude
        data.append(int(val * 32767))
    return struct.pack(f"<{n_samples}h", *data)


def _kick_drum(duration: float = 0.12, amplitude: float = 0.6,
               sample_rate: int = 44100) -> bytes:
    """Synthesized kick drum — pitch-swept sine + noise burst."""
    n_samples = int(sample_rate * duration)
    data = []
    for i in range(n_samples):
        t = i / sample_rate
        env = math.exp(-t * 30)          # fast decay
        freq = 80 + 150 * math.exp(-t * 60)  # pitch sweep 230→80 Hz
        tone = math.sin(2 * math.pi * freq * t)
        val = amplitude * env * tone
        data.append(max(-32768, min(32767, int(val * 32767))))
    return struct.pack(f"<{n_samples}h", *data)


def _snare_drum(duration: float = 0.10, amplitude: float = 0.35,
                sample_rate: int = 44100) -> bytes:
    """Synthesized snare — noise burst with fast decay."""
    import random
    n_samples = int(sample_rate * duration)
    rng = random.Random(42)
    data = []
    for i in range(n_samples):
        t = i / sample_rate
        env = math.exp(-t * 40)
        noise = rng.uniform(-1, 1)
        val = amplitude * env * noise
        data.append(max(-32768, min(32767, int(val * 32767))))
    return struct.pack(f"<{n_samples}h", *data)


def _hihat(duration: float = 0.05, amplitude: float = 0.15,
           sample_rate: int = 44100) -> bytes:
    """Open hi-hat — short high-freq noise."""
    import random
    n_samples = int(sample_rate * duration)
    rng = random.Random(7)
    data = []
    for i in range(n_samples):
        t = i / sample_rate
        env = math.exp(-t * 80)
        noise = rng.uniform(-1, 1)
        data.append(max(-32768, min(32767, int(amplitude * env * noise * 32767))))
    return struct.pack(f"<{n_samples}h", *data)


def _mix_pcm(tracks: List[bytes]) -> bytes:
    """Mix multiple PCM tracks by clamped summing."""
    if not tracks:
        return b""
    n = min(len(t) for t in tracks) // 2
    mixed = []
    for i in range(n):
        sample = sum(struct.unpack_from("<h", t, i * 2)[0] for t in tracks)
        mixed.append(max(-32768, min(32767, sample)))
    return struct.pack(f"<{n}h", *mixed)


def _pad_pcm(data: bytes, total_samples: int) -> bytes:
    """Pad PCM data with silence to reach total_samples."""
    n = len(data) // 2
    if n >= total_samples:
        return data[:total_samples * 2]
    return data + b"\x00" * ((total_samples - n) * 2)


def _overlay_pcm(base: bytes, overlay: bytes, offset_samples: int) -> bytes:
    """Overlay one PCM track onto another at a sample offset."""
    base_arr = list(struct.unpack(f"<{len(base)//2}h", base))
    ov_arr   = list(struct.unpack(f"<{len(overlay)//2}h", overlay))
    for i, s in enumerate(ov_arr):
        idx = offset_samples + i
        if 0 <= idx < len(base_arr):
            base_arr[idx] = max(-32768, min(32767, base_arr[idx] + s))
    return struct.pack(f"<{len(base_arr)}h", *base_arr)


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
             tempo_bpm: float = 90.0,
             amplitude: float = 0.18,
             fade_in: float = 2.0,
             fade_out: float = 3.0,
             with_beat: bool = True) -> Path:
    """
    Generate a lively background music track with chord arpeggios,
    optional percussion beat, and smooth fade in/out.

    Args:
        duration:    Total length in seconds.
        style:       One of: lofi_chill, upbeat, melancholy, mysterious
        tempo_bpm:   Beats per minute (default 90).
        amplitude:   Chord volume (0.0–1.0).
        fade_in:     Fade in duration at start (seconds).
        fade_out:    Fade out duration at end (seconds).
        with_beat:   If True, add kick+snare+hihat percussion pattern.
    """
    BGM_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        output_path = str(BGM_CACHE_DIR / f"bgm_{style}_{int(duration)}s_v2.wav")

    out = Path(output_path)
    sample_rate = 44100
    total_samples = int(duration * sample_rate)
    beat_dur = 60.0 / tempo_bpm          # seconds per beat
    bar_dur  = beat_dur * 4               # 4/4 time
    progression = PROGRESSIONS.get(style, PROGRESSIONS["lofi_chill"])

    # ── Layer 1: Arpeggiated chords (triangle wave, more warmth) ─────────────
    chord_data = b"\x00" * (total_samples * 2)
    note_dur = beat_dur / 2              # eighth note arpeggios
    elapsed = 0.0
    chord_idx = 0
    note_in_chord = 0

    while elapsed < duration:
        chord_idx = int(elapsed / bar_dur) % len(progression)
        chord = progression[chord_idx]
        note_key = chord[note_in_chord % len(chord)]
        note_in_chord += 1

        if note_key in _NOTES:
            freq = _NOTES[note_key]
            seg = min(note_dur, duration - elapsed)
            # Slight note envelope: ramp up 5ms, decay tail
            note_pcm = _triangle_wave(freq, seg, amplitude * 0.8, sample_rate)
            # Apply note-level envelope
            n = len(note_pcm) // 2
            env_data = list(struct.unpack(f"<{n}h", note_pcm))
            ramp = min(n, int(0.005 * sample_rate))
            for j in range(ramp):
                env_data[j] = int(env_data[j] * j / ramp)
            note_pcm = struct.pack(f"<{n}h", *env_data)
            offset = int(elapsed * sample_rate)
            chord_data = _overlay_pcm(chord_data, note_pcm, offset)

        elapsed += note_dur

    # ── Layer 2: Bass line (one octave below root, sine) ─────────────────────
    bass_data = b"\x00" * (total_samples * 2)
    elapsed = 0.0
    while elapsed < duration:
        chord_idx = int(elapsed / bar_dur) % len(progression)
        root_key = progression[chord_idx][0]
        if root_key in _NOTES:
            bass_freq = _NOTES[root_key] / 2.0   # one octave down
            seg = min(bar_dur, duration - elapsed)
            bass_pcm = _sine_wave(bass_freq, seg, amplitude * 0.6, sample_rate)
            offset = int(elapsed * sample_rate)
            bass_data = _overlay_pcm(bass_data, bass_pcm, offset)
        elapsed += bar_dur

    # ── Layer 3: Percussion (kick, snare, hihat) ──────────────────────────────
    perc_data = b"\x00" * (total_samples * 2)
    if with_beat:
        kick  = _kick_drum(0.12,  0.5,  sample_rate)
        snare = _snare_drum(0.10, 0.28, sample_rate)
        hihat = _hihat(0.05,      0.12, sample_rate)

        beat = 0.0
        while beat < duration:
            beat_in_bar = int(round((beat % bar_dur) / beat_dur)) % 4
            t_offset = int(beat * sample_rate)
            # Kick on beats 0, 2
            if beat_in_bar in (0, 2):
                perc_data = _overlay_pcm(perc_data, kick, t_offset)
            # Snare on beats 1, 3
            if beat_in_bar in (1, 3):
                perc_data = _overlay_pcm(perc_data, snare, t_offset)
            # Hi-hat every eighth note
            perc_data = _overlay_pcm(perc_data, hihat, t_offset)
            beat += beat_dur / 2  # eighth note grid

    # ── Mix all layers ────────────────────────────────────────────────────────
    all_pcm = _mix_pcm([chord_data, bass_data, perc_data])

    # ── Apply fade in / fade out envelope ────────────────────────────────────
    total_s = len(all_pcm) // 2
    data = list(struct.unpack(f"<{total_s}h", all_pcm))

    fade_in_samples  = int(fade_in  * sample_rate)
    fade_out_samples = int(fade_out * sample_rate)
    fade_out_start   = max(0, total_s - fade_out_samples)

    for i in range(min(fade_in_samples, total_s)):
        data[i] = int(data[i] * (i / fade_in_samples))

    for i in range(fade_out_start, total_s):
        factor = 1.0 - (i - fade_out_start) / fade_out_samples
        data[i] = int(data[i] * max(0.0, factor))

    all_pcm = struct.pack(f"<{total_s}h", *data)

    _write_wav(out, all_pcm, sample_rate)
    print(f"[BGM] Generated {style} BGM ({tempo_bpm}bpm, fade_in={fade_in}s, fade_out={fade_out}s) → {out}")
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
