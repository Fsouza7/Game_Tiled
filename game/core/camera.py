"""Smoothly follows a target and stays clamped to the world bounds."""
import random

from game.settings import (
    TILE_SIZE, WORLD_WIDTH_TILES, WORLD_HEIGHT_TILES,
    WINDOW_WIDTH, WINDOW_HEIGHT, CAMERA_SMOOTHING,
    CAMERA_DEFAULT_ZOOM, CAMERA_MIN_ZOOM, CAMERA_MAX_ZOOM, CAMERA_ZOOM_STEP,
)


class Camera:
    def __init__(self):
        self.x = 0.0  # world-space px of the top-left visible corner
        self.y = 0.0
        self.zoom = CAMERA_DEFAULT_ZOOM
        self._shake_magnitude_px = 0.0
        self._shake_duration_s = 0.0
        self._shake_remaining_s = 0.0
        self._shake_offset_x = 0.0
        self._shake_offset_y = 0.0

    def zoom_in(self) -> None:
        self.zoom = min(CAMERA_MAX_ZOOM, self.zoom + CAMERA_ZOOM_STEP)

    def zoom_out(self) -> None:
        self.zoom = max(CAMERA_MIN_ZOOM, self.zoom - CAMERA_ZOOM_STEP)

    def shake(self, magnitude_px: float, duration_s: float) -> None:
        """Triggers a brief screen shake (e.g. the player taking damage).
        A shake already playing is only replaced if the new one is
        stronger, rather than restarted/stacked -- otherwise a flurry of
        small hits during a fight would keep re-triggering a long weak
        shake instead of settling, reading as a nonstop wobble."""
        if magnitude_px <= 0.0:
            return
        if self._shake_remaining_s > 0.0 and magnitude_px < self._shake_magnitude_px:
            return
        self._shake_magnitude_px = magnitude_px
        self._shake_duration_s = duration_s
        self._shake_remaining_s = duration_s

    def update(self, dt: float) -> None:
        """Advances the shake's decay. Call once per frame (skip while
        paused, same as particles/notifications)."""
        if self._shake_remaining_s <= 0.0:
            self._shake_offset_x = 0.0
            self._shake_offset_y = 0.0
            return
        self._shake_remaining_s = max(0.0, self._shake_remaining_s - dt)
        ratio = self._shake_remaining_s / self._shake_duration_s if self._shake_duration_s > 0.0 else 0.0
        current_magnitude = self._shake_magnitude_px * ratio
        self._shake_offset_x = random.uniform(-current_magnitude, current_magnitude)
        self._shake_offset_y = random.uniform(-current_magnitude, current_magnitude)

    @property
    def view_width(self) -> float:
        return WINDOW_WIDTH / self.zoom

    @property
    def view_height(self) -> float:
        return WINDOW_HEIGHT / self.zoom

    def follow(self, target_center_x: float, target_center_y: float) -> None:
        desired_x = target_center_x - self.view_width / 2
        desired_y = target_center_y - self.view_height / 2

        self.x += (desired_x - self.x) * CAMERA_SMOOTHING
        self.y += (desired_y - self.y) * CAMERA_SMOOTHING

        max_x = max(0.0, WORLD_WIDTH_TILES * TILE_SIZE - self.view_width)
        max_y = max(0.0, WORLD_HEIGHT_TILES * TILE_SIZE - self.view_height)
        self.x = max(0.0, min(self.x, max_x))
        self.y = max(0.0, min(self.y, max_y))

    def world_to_screen(self, world_x: float, world_y: float):
        # Shake is purely a rendering offset -- screen_to_world (mining/
        # aim targeting) deliberately ignores it, so a shake in progress
        # never throws off what the player's click actually lands on.
        return (
            (world_x - self.x) * self.zoom + self._shake_offset_x,
            (world_y - self.y) * self.zoom + self._shake_offset_y,
        )

    def screen_to_world(self, screen_x: float, screen_y: float):
        return (
            screen_x / self.zoom + self.x,
            screen_y / self.zoom + self.y,
        )
