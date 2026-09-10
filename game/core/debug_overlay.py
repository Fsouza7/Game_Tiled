"""Minimal debug HUD, toggled with F3. Separately, F4 toggles debug_mode
(GameApp) -- the F5-F11 cheats (see GameApp's debug_* methods) -- shown
here as a shortcut reminder whenever it's on, regardless of F3."""
import pygame

from game.settings import TILE_SIZE, CHUNK_WIDTH
from game.world.world_generator import biome_at

_DEBUG_MODE_SHORTCUTS = (
    "F5 unlock all recipes",
    "F6 reveal map",
    "F7 full heal + coins",
    "F8 spawn all bosses",
    "F9 spawn all enemies",
    "F10 teleport to cursor",
    "F11 teleport to spawn",
)
# Clears the always-on top-left Combat Lv HUD panel (16,16 -> roughly
# (.., 62), see Renderer._draw_combat_level_bar) so neither this overlay
# nor the debug-mode banner below sits underneath it.
_TOP_MARGIN = 68


class DebugOverlay:
    def __init__(self):
        self.enabled = False
        self.font = pygame.font.SysFont("consolas", 16)

    def toggle(self) -> None:
        self.enabled = not self.enabled

    def draw(self, window, clock, player, world, camera, enemies=(), world_clock=None, npcs=(), debug_mode: bool = False) -> None:
        if debug_mode:
            self._draw_debug_mode_banner(window)
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
        top = _TOP_MARGIN + (18 * (len(_DEBUG_MODE_SHORTCUTS) + 1) if debug_mode else 0)
        for i, line in enumerate(lines):
            surface = self.font.render(line, True, (255, 255, 0))
            window.blit(surface, (8, top + i * 18))

    def _draw_debug_mode_banner(self, window) -> None:
        lines = ["DEBUG MODE (F4 to turn off)"] + list(_DEBUG_MODE_SHORTCUTS)
        for i, line in enumerate(lines):
            color = (255, 90, 90) if i == 0 else (255, 200, 90)
            surface = self.font.render(line, True, color)
            window.blit(surface, (8, _TOP_MARGIN + i * 18))
