# -*- coding: utf-8 -*-
"""
AssetManager — unified interface for loading local assets and fetching web assets.
Handles: local files, OpenMoji PNG icons, Unsplash photos, existing project assets.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Optional, Dict, Tuple

import requests
from PIL import Image

# ── Asset store paths ─────────────────────────────────────────────────────────
ASSET_ROOT = Path(__file__).parent.parent / "assets"
OPENMOJI_DIR = ASSET_ROOT / "openmoji"
CACHE_DIR = ASSET_ROOT / ".cache"
EXISTING_ASSETS_MAP = {
    "turtle":   "C:/Users/chewei/Desktop/littleturtle/projects/diagram_style/assets/turtle_transparent.png",
    "brain":    "C:/Users/chewei/Desktop/littleturtle/projects/diagram_style/assets/brain.png",
    "rocket":   "C:/Users/chewei/Desktop/littleturtle/projects/diagram_style/assets/rocket.png",
    "computer": "C:/Users/chewei/Desktop/littleturtle/projects/diagram_style/assets/computer.png",
    "book":     "C:/Users/chewei/Desktop/littleturtle/projects/diagram_style/assets/book.png",
    "check":    "C:/Users/chewei/Desktop/littleturtle/projects/diagram_style/assets/check.png",
    "cross":    "C:/Users/chewei/Desktop/littleturtle/projects/diagram_style/assets/cross.png",
    "gear":     "C:/Users/chewei/Desktop/littleturtle/projects/diagram_style/assets/gear.png",
    "person":   "C:/Users/chewei/Desktop/littleturtle/projects/diagram_style/assets/person.png",
    "sparkle":  "C:/Users/chewei/Desktop/littleturtle/projects/diagram_style/assets/sparkle.png",
    "document": "C:/Users/chewei/Desktop/littleturtle/projects/diagram_style/assets/document.png",
}

# OpenMoji emoji name → hex code mapping (common ones)
OPENMOJI_NAMES: Dict[str, str] = {
    "turtle":    "1F422",
    "robot":     "1F916",
    "rocket":    "1F680",
    "brain":     "1F9E0",
    "sparkle":   "2728",
    "star":      "2B50",
    "fire":      "1F525",
    "check":     "2705",
    "cross":     "274C",
    "gear":      "2699",
    "book":      "1F4D6",
    "computer":  "1F4BB",
    "person":    "1F9D1",
    "heart":     "2764",
    "lightning": "26A1",
    "magnifier": "1F50D",
    "camera":    "1F4F7",
    "music":     "1F3B5",
    "dog":       "1F436",
    "cat":       "1F431",
    "bird":      "1F426",
    "fish":      "1F41F",
    "flower":    "1F33C",
    "tree":      "1F333",
    "sun":       "2600",
    "moon":      "1F319",
    "cloud":     "2601",
    "rainbow":   "1F308",
}

OPENMOJI_BASE_URL = "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72"


class AssetManager:
    """
    Load and cache assets from various sources.

    Usage:
        am = AssetManager()
        img = am.get("turtle")              # from existing project assets
        img = am.fetch_openmoji("rocket")   # download from OpenMoji
        img = am.load_local("my_logo.png")  # any local file
        img = am.fetch_url("https://...")   # arbitrary URL
    """

    def __init__(self):
        OPENMOJI_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def get(self, name: str, size: Optional[Tuple[int, int]] = None) -> Optional[Image.Image]:
        """
        Get an asset by name. Checks existing project assets first,
        then tries OpenMoji download.
        """
        # 1. Check existing project assets
        if name in EXISTING_ASSETS_MAP:
            path = Path(EXISTING_ASSETS_MAP[name])
            if path.exists():
                img = Image.open(path).convert("RGBA")
                return img.resize(size, Image.LANCZOS) if size else img

        # 2. Try OpenMoji
        img = self.fetch_openmoji(name, size)
        if img:
            return img

        return None

    def fetch_openmoji(self, name: str,
                       size: Optional[Tuple[int, int]] = None) -> Optional[Image.Image]:
        """Download an OpenMoji icon by name or emoji character."""
        hex_code = self._resolve_openmoji_code(name)
        if not hex_code:
            print(f"[AssetManager] Unknown OpenMoji name: {name}")
            return None

        cache_path = OPENMOJI_DIR / f"{hex_code}.png"
        if not cache_path.exists():
            for variant in [hex_code, hex_code.replace("-FE0F", "")]:
                url = f"{OPENMOJI_BASE_URL}/{variant}.png"
                try:
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200:
                        cache_path.write_bytes(r.content)
                        print(f"[AssetManager] Downloaded OpenMoji: {name} ({variant})")
                        break
                except Exception:
                    continue
            else:
                print(f"[AssetManager] Could not download OpenMoji: {name}")
                return None

        img = Image.open(cache_path).convert("RGBA")
        return img.resize(size, Image.LANCZOS) if size else img

    def load_local(self, path: str,
                   size: Optional[Tuple[int, int]] = None) -> Optional[Image.Image]:
        """Load any local image file."""
        p = Path(path)
        if not p.exists():
            print(f"[AssetManager] File not found: {path}")
            return None
        img = Image.open(p).convert("RGBA")
        return img.resize(size, Image.LANCZOS) if size else img

    def fetch_url(self, url: str,
                  size: Optional[Tuple[int, int]] = None) -> Optional[Image.Image]:
        """Download an image from any URL, with local cache."""
        cache_key = hashlib.md5(url.encode()).hexdigest()
        cache_path = CACHE_DIR / f"{cache_key}.png"
        if not cache_path.exists():
            try:
                r = requests.get(url, timeout=15,
                                 headers={"User-Agent": "turtle-video-kit/1.0"})
                r.raise_for_status()
                cache_path.write_bytes(r.content)
                print(f"[AssetManager] Downloaded: {url}")
            except Exception as e:
                print(f"[AssetManager] Failed to download {url}: {e}")
                return None
        img = Image.open(cache_path).convert("RGBA")
        return img.resize(size, Image.LANCZOS) if size else img

    def list_existing(self) -> Dict[str, str]:
        """List all pre-mapped existing assets."""
        return {k: v for k, v in EXISTING_ASSETS_MAP.items()
                if Path(v).exists()}

    def _resolve_openmoji_code(self, name: str) -> Optional[str]:
        """Resolve a name or emoji character to an OpenMoji hex code."""
        if name in OPENMOJI_NAMES:
            return OPENMOJI_NAMES[name]
        # Try treating it as an emoji character
        try:
            codes = [f"{ord(c):X}" for c in name if ord(c) > 127]
            if codes:
                return "-".join(codes)
        except Exception:
            pass
        return None


# Module-level singleton
_default_manager = None

def get_asset(name: str, size: Optional[Tuple[int, int]] = None) -> Optional[Image.Image]:
    """Convenience function — use the default AssetManager."""
    global _default_manager
    if _default_manager is None:
        _default_manager = AssetManager()
    return _default_manager.get(name, size)
