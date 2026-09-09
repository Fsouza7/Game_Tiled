"""Minimal debug HUD, toggled with F3."""
import pygame

from game.settings import TILE_SIZE, CHUNK_WIDTH
from game.world.world_generator import biome_at


class DebugOverlay:
    def __init__(self):
        self.enabled = False
        self.font = pygame.font.SysFont("consolas", 16)

    def toggle(self) -> None:
        self.enabled = not self.enabled

    def draw(self, window, clock, player, world, camera, enemies=(), world_clock=None, npcs=()) -> None:
        if not self.enabled:
            return
        tile_x = int(player.center_x // TILE_SIZE)
        tile_y = int(player.center_y // TILE_SIZE)
        chunk_x = tile_x // CHUNK_WIDTH
        lines = [
            f"FPS: {clock.get_fps():.0f}",
            f"Seed: {world.seed}",
            f"Pos: ({player.x:.1f}, {player.y:.1f})",
            f"Tile: ({tile_x}, {tile_y})  Chunk: {chunk_x}",
            f"Loaded chunks: {len(world.chunks)}",
            f"HP: {player.health:.0f}/{player.max_health}"
            + (" (regen)" if player.is_regenerating() else f" (regen in {player.regen_delay_remaining:.1f}s)" if player.regen_delay_remaining > 0 else ""),
            f"Zoom: {camera.zoom:.2f}",
            f"Enemies: {len(enemies)}  NPCs: {len(npcs)}",
            f"Biome: {biome_at(world.seed, tile_x).name}",
        ]
        if world_clock is not None:
            lines.append(
                f"Day {world_clock.day_count} {world_clock.clock_string()}"
                f" ({'night' if world_clock.is_night else 'day'}, ambient {world_clock.ambient_light:.2f})"
            )
        for i, line in enumerate(lines):
            surface = self.font.render(line, True, (255, 255, 0))
            window.blit(surface, (8, 8 + i * 18))
