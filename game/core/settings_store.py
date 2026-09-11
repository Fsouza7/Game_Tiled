"""Persisted user preferences: audio volume and key bindings.

Deliberately separate from save_system.py's save slot -- preferences should
survive even with no save yet, aren't part of "one playthrough" (Restart/Load
rebuild the run but must never reset how loud the player set things, or which
keys they bound), and load once at GameApp startup rather than per-run.

`Settings`/`load`/`save` mirror save_system.py's shape (a plain data
object, pure-ish load/save around a JSON file) but tolerate a missing or
corrupt file by degrading to defaults instead of raising -- audio /
bindings are not worth ever blocking game startup over, the same
"never crash on this" precedent game/core/sfx.py and music.py already
apply to the sounds themselves.
"""
import json
import logging
import os

from game.settings import SETTINGS_FILE_PATH, MUSIC_VOLUME, SFX_VOLUME
from game.input.bindings import parse_bindings, serialize_bindings, DEFAULT_BINDINGS

logger = logging.getLogger(__name__)


class Settings:
    def __init__(self, music_volume: float = MUSIC_VOLUME, sfx_volume: float = SFX_VOLUME, bindings=None):
        self.music_volume = music_volume
        self.sfx_volume = sfx_volume
        self.bindings = parse_bindings(bindings if bindings is not None else DEFAULT_BINDINGS)


def load(path: str = SETTINGS_FILE_PATH) -> Settings:
    if not os.path.exists(path):
        return Settings()
    try:
        with open(path) as f:
            data = json.load(f)
        return Settings(
            music_volume=max(0.0, min(1.0, float(data.get("music_volume", MUSIC_VOLUME)))),
            sfx_volume=max(0.0, min(1.0, float(data.get("sfx_volume", SFX_VOLUME)))),
            bindings=data.get("bindings"),
        )
    except Exception:
        logger.warning("Failed to load settings from %s, using defaults", path, exc_info=True)
        return Settings()


def save(settings: Settings, path: str = SETTINGS_FILE_PATH) -> None:
    try:
        dirname = os.path.dirname(path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(path, "w") as f:
            json.dump({
                "music_volume": settings.music_volume,
                "sfx_volume": settings.sfx_volume,
                "bindings": serialize_bindings(settings.bindings),
            }, f)
    except Exception:
        logger.warning("Failed to save settings to %s", path, exc_info=True)
