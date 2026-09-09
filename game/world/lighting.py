"""Simple point-light + ambient lighting.

Deliberately NOT a full occlusion-aware flood fill (Terraria/Minecraft-style
BFS that stops at solid tiles): light sources here shine through thin walls
with a plain distance falloff. That's a real simplification -- documented in
README "How lighting works" -- traded for simplicity and speed. What it
still gets right, per the brief: light sources are tile data
(TileDef.light_emit), torches visibly light nearby areas, and light is
computed only for the visible viewport (+ a margin) every frame, never the
whole world -- cost stays flat regardless of world size.
"""
from typing import List, Tuple

from game.settings import LIGHT_RADIUS_TILES, UNDERGROUND_DARK_DEPTH_TILES, UNDERGROUND_MIN_AMBIENT
from game.world import tile_registry
from game.world.world import World

LightSource = Tuple[int, int, float]  # (tile_x, tile_y, strength 0..1)


def find_light_sources(world: World, x_start: int, x_end: int, y_start: int, y_end: int) -> List[LightSource]:
    """Scans the given (already viewport+margin-bounded) tile rectangle for
    light-emitting tiles. Cheap as long as the caller keeps the rectangle
    small -- it is not meant to be called with world-sized bounds."""
    sources = []
    for x in range(x_start, x_end + 1):
        for y in range(y_start, y_end + 1):
            tile_def = tile_registry.get(world.get_tile(x, y))
            if tile_def.light_emit > 0:
                sources.append((x, y, tile_def.light_emit / 15.0))
    return sources


def ambient_light_for_depth(depth_below_surface: float, sky_ambient: float) -> float:
    """The sky's day/night ambient fades out linearly over
    UNDERGROUND_DARK_DEPTH_TILES once below the surface (depth <= 0 is
    surface-or-above and returns sky_ambient unchanged), floored at
    UNDERGROUND_MIN_AMBIENT so caves are dark but never pure black. This is
    independent of time of day -- a cave at noon fades to the same
    near-black as one at midnight, with torches/Fire as the only real light
    down there, same as the surface at night."""
    if depth_below_surface <= 0:
        return sky_ambient
    fade = max(0.0, 1.0 - depth_below_surface / UNDERGROUND_DARK_DEPTH_TILES)
    return UNDERGROUND_MIN_AMBIENT + (sky_ambient - UNDERGROUND_MIN_AMBIENT) * fade


def light_level_at(tile_x: float, tile_y: float, light_sources: List[LightSource], ambient_light: float) -> float:
    """Brightness (0..1) at a tile position: the brighter of ambient light
    and the strongest nearby source's falloff."""
    best = ambient_light
    for source_x, source_y, strength in light_sources:
        radius = LIGHT_RADIUS_TILES * strength
        if radius <= 0:
            continue
        distance = ((tile_x - source_x) ** 2 + (tile_y - source_y) ** 2) ** 0.5
        if distance > radius:
            continue
        falloff = 1.0 - distance / radius
        contribution = strength * falloff
        if contribution > best:
            best = contribution
    return min(1.0, best)
