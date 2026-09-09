"""Smoothly follows a target and stays clamped to the world bounds."""
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

    def zoom_in(self) -> None:
        self.zoom = min(CAMERA_MAX_ZOOM, self.zoom + CAMERA_ZOOM_STEP)

    def zoom_out(self) -> None:
        self.zoom = max(CAMERA_MIN_ZOOM, self.zoom - CAMERA_ZOOM_STEP)

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
        return (
            (world_x - self.x) * self.zoom,
            (world_y - self.y) * self.zoom,
        )

    def screen_to_world(self, screen_x: float, screen_y: float):
        return (
            screen_x / self.zoom + self.x,
            screen_y / self.zoom + self.y,
        )
