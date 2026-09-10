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


def start_background_music() -> None:
    if not os.path.isfile(MUSIC_PATH):
        logger.warning("Background music not found at %s", MUSIC_PATH)
        return
    try:
        pygame.mixer.music.load(MUSIC_PATH)
        pygame.mixer.music.set_volume(MUSIC_VOLUME)
        pygame.mixer.music.play(loops=-1)
    except Exception:
        logger.warning("Failed to play background music at %s", MUSIC_PATH, exc_info=True)
