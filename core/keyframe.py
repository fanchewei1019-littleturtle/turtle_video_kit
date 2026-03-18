# -*- coding: utf-8 -*-
"""
Keyframe interpolation — the math behind all animations.
Every animated property uses this to compute its value at any given time.
"""
import math


# ── Easing Functions ──────────────────────────────────────────────────────────

def linear(t: float) -> float:
    return t

def ease_in(t: float) -> float:
    return t * t

def ease_out(t: float) -> float:
    return t * (2 - t)

def ease_in_out(t: float) -> float:
    return t * t * (3 - 2 * t)

def bounce_out(t: float) -> float:
    if t < 1 / 2.75:
        return 7.5625 * t * t
    elif t < 2 / 2.75:
        t -= 1.5 / 2.75
        return 7.5625 * t * t + 0.75
    elif t < 2.5 / 2.75:
        t -= 2.25 / 2.75
        return 7.5625 * t * t + 0.9375
    else:
        t -= 2.625 / 2.75
        return 7.5625 * t * t + 0.984375

def elastic_out(t: float) -> float:
    if t == 0 or t == 1:
        return t
    return (2 ** (-10 * t)) * math.sin((t - 0.075) * (2 * math.pi) / 0.3) + 1

def spring(t: float) -> float:
    """Slight overshoot and settle."""
    c = 1.70158
    t -= 1
    return t * t * ((c + 1) * t + c) + 1

EASINGS = {
    "linear": linear,
    "ease_in": ease_in,
    "ease_out": ease_out,
    "ease_in_out": ease_in_out,
    "bounce": bounce_out,
    "elastic": elastic_out,
    "spring": spring,
}


# ── Keyframe Interpolator ─────────────────────────────────────────────────────

def interpolate(value_start, value_end, t_start: float, t_end: float,
                current_time: float, easing: str = "linear"):
    """
    Interpolate between value_start and value_end based on current_time.
    Works for scalars, tuples (e.g. colors/positions), and lists.

    Returns value_start if current_time < t_start,
            value_end   if current_time > t_end,
            interpolated value in between.
    """
    if current_time <= t_start:
        return value_start
    if current_time >= t_end:
        return value_end

    raw_t = (current_time - t_start) / (t_end - t_start)
    t = EASINGS.get(easing, linear)(raw_t)

    if isinstance(value_start, (int, float)):
        return value_start + (value_end - value_start) * t

    if isinstance(value_start, (tuple, list)):
        result = tuple(
            s + (e - s) * t for s, e in zip(value_start, value_end)
        )
        # Preserve int tuples (e.g. RGBA colors)
        if isinstance(value_start[0], int):
            result = tuple(int(round(v)) for v in result)
        return type(value_start)(result)

    return value_start


def alpha_at(t_start: float, t_end: float, current_time: float,
             easing: str = "ease_in_out") -> float:
    """Convenience: returns 0.0→1.0 alpha for a fade-in window."""
    return interpolate(0.0, 1.0, t_start, t_end, current_time, easing)
