"""Background music playback via pygame.mixer.music (streamed, not a
Sound -- the right choice for one long looping track instead of many short
overlapping effects). Missing/corrupt file degrades to silence rather than
crashing the game, same "don't hard-fail on missing art" precedent as the
rest of game/rendering/assets.py.
"""
import logging
import os

import pygame

from game.settings import MUSIC_VOLUME

logger = logging.getLogger(__name__)

MUSIC_PATH = os.path.join("Music", "background.mp3")


def start_background_music(volume: float = MUSIC_VOLUME) -> None:
    if not os.path.isfile(MUSIC_PATH):
        logger.warning("Background music not found at %s", MUSIC_PATH)
        return
    try:
        pygame.mixer.music.load(MUSIC_PATH)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(loops=-1)
    except Exception:
        logger.warning("Failed to play background music at %s", MUSIC_PATH, exc_info=True)


def set_volume(volume: float) -> None:
    """Live-adjusts the currently playing (or not-yet-started) track's
    volume -- the Settings screen's Music Volume slider. A no-op, not a
    crash, if no mixer session is up (headless tests, no audio device)."""
    try:
        pygame.mixer.music.set_volume(volume)
    except Exception:
        logger.debug("Could not set music volume", exc_info=True)
