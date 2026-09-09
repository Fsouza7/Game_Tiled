"""Forces a headless SDL backend so the test suite runs without a display
(CI machines, this environment, etc.). Must run before pygame.init() is
ever called, so it lives in conftest and is imported before test modules.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
