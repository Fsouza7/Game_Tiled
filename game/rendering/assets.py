"""Loads and slices the real art in assets/ (must run after pygame.display
is initialized, since convert_alpha() needs a display surface).

Only three tile materials exist as dedicated art in assets/Terrain/Terrain.png
(grass, dirt, a light stone brick). Tiles with no matching material (ore,
bedrock, workbench, tree trunk/planks) reuse the closest base sprite with a
color tint plus a small procedural detail (speckles, plank/bark lines) drawn
on top so they read as a distinct material rather than a flat color wash.
This is documented here and in README.md rather than pretended away.

Item icons follow the same idea: a block/ore icon reuses its tile texture
(see ItemDef.places_tile_id / icon_tile_id); a few items with no matching
tile or sprite (the pickaxes, sword, cap) get a small hand-drawn vector icon
instead of an anonymous color swatch -- see `_build_procedural_icons`.

Spikes and Trampoline reuse dedicated art from assets/Traps/ directly (real,
single-frame source images, no tint/detail pass needed); the fruit
consumables reuse assets/Items/Fruits/ the same way Apple already did.
"""
import os
import random
from typing import Dict, List, Tuple

import pygame

from game.settings import TILE_SIZE
from game.world.tile_registry import (
    GRASS_ID, DIRT_ID, STONE_ID, COAL_ORE_ID, IRON_ORE_ID, BEDROCK_ID,
    DECOR_CRATE_ID, WORKBENCH_ID, TREE_TRUNK_ID, TREE_LEAVES_ID, WOOD_PLANK_ID,
    TORCH_ID, SAND_ID, SANDSTONE_ID, SNOW_BLOCK_ID, FROZEN_DIRT_ID,
    JUNGLE_GRASS_ID, MUD_ID, CACTUS_ID, DESERT_STONE_ID, SNOW_STONE_ID,
    JUNGLE_STONE_ID, TOPAZ_ORE_ID, SAPPHIRE_ORE_ID, EMERALD_ORE_ID,
    BUSH_ID, SPIKES_ID, TRAMPOLINE_ID, FAN_ID, TRAP_SAND_ID, TRAP_MUD_ID,
    TRAP_ICE_ID, CRUMBLE_PLATFORM_ID, CHECKPOINT_ID, FURNACE_ID, CHEST_ID,
)
from game.entities import character_registry
from game.world import hazard_feature

TERRAIN_PATH = os.path.join("assets", "Terrain", "Terrain.png")
TERRAIN_CELL = 16

# (column, row) of the chosen 16x16 cell in Terrain.png for each material.
_TERRAIN_CELLS = {
    GRASS_ID: (7, 0),
    DIRT_ID: (7, 1),
    STONE_ID: (13, 5),
}

PLAYER_CHARACTER_DIR = os.path.join("assets", "MainCharacters", "NinjaFrog")
PLAYER_FRAME_SIZE = 32
PLAYER_ANIMATIONS = {
    "idle": "idle.png",
    "run": "run.png",
    "jump": "jump.png",
    "fall": "fall.png",
    "double_jump": "double_jump.png",
}

BACKGROUND_PATH = os.path.join("assets", "Background", "Blue.png")

CRATE_TEXTURE_PATH = os.path.join("assets", "Items", "Boxes", "Box1", "Idle.png")
CHEST_TEXTURE_PATH = os.path.join("assets", "Items", "Boxes", "Box2", "Idle.png")
SPIKES_TEXTURE_PATH = os.path.join("assets", "Traps", "Spikes", "Idle.png")
TRAMPOLINE_TEXTURE_PATH = os.path.join("assets", "Traps", "Trampoline", "Idle.png")
FAN_ON_PATH = os.path.join("assets", "Traps", "Fan", "on.png")
CRUMBLE_OFF_PATH = os.path.join("assets", "Traps", "Falling Platforms", "Off.png")
CRUMBLE_ON_PATH = os.path.join("assets", "Traps", "Falling Platforms", "On (32x10).png")
CHECKPOINT_NO_FLAG_PATH = os.path.join("assets", "Items", "Checkpoints", "Checkpoint", "Checkpoint (No Flag).png")
CHECKPOINT_FLAG_IDLE_PATH = os.path.join("assets", "Items", "Checkpoints", "Checkpoint", "Checkpoint (Flag Idle)(64x64).png")

SAW_ON_PATH = os.path.join("assets", "Traps", "Saw", "on.png")
SAW_CHAIN_PATH = os.path.join("assets", "Traps", "Saw", "Chain.png")
ROCK_HEAD_IDLE_PATH = os.path.join("assets", "Traps", "Rock Head", "Idle.png")
ROCK_HEAD_HIT_PATH = os.path.join("assets", "Traps", "Rock Head", "Bottom Hit (42x42).png")
SPIKE_HEAD_IDLE_PATH = os.path.join("assets", "Traps", "Spike Head", "Idle.png")
SPIKE_HEAD_HIT_PATH = os.path.join("assets", "Traps", "Spike Head", "Right Hit (54x52).png")
SPIKED_BALL_PATH = os.path.join("assets", "Traps", "Spiked Ball", "Spiked Ball.png")

DUST_PARTICLE_PATH = os.path.join("assets", "Other", "Dust Particle.png")
SHADOW_PATH = os.path.join("assets", "Other", "Shadow.png")
CONFETTI_PATH = os.path.join("assets", "Other", "Confetti (16x16).png")
CONFETTI_CELL = 16

MENU_BUTTONS_DIR = os.path.join("assets", "Menu", "Buttons", "Menu_jogo")

_FRUITS_DIR = os.path.join("assets", "Items", "Fruits")

# Static, non-tile item icons: item_id -> (path, frame_size). frame_size is
# the width of a single frame when the source file is an animation strip;
# only the first frame is used since inventory icons don't animate.
_STATIC_ICON_SOURCES = {
    "apple": (os.path.join("assets", "Items", "Fruits", "Apple", "Apple.png"), 32),
    "banana": (os.path.join(_FRUITS_DIR, "Bananas.png"), 32),
    "cherries": (os.path.join(_FRUITS_DIR, "Cherries.png"), 32),
    "kiwi": (os.path.join(_FRUITS_DIR, "Kiwi.png"), 32),
    "melon": (os.path.join(_FRUITS_DIR, "Melon.png"), 32),
    "orange": (os.path.join(_FRUITS_DIR, "Orange.png"), 32),
    "pineapple": (os.path.join(_FRUITS_DIR, "Pineapple.png"), 32),
    "strawberry": (os.path.join(_FRUITS_DIR, "Strawberry.png"), 32),
}


def _crop(sheet: pygame.Surface, x: int, y: int, w: int, h: int) -> pygame.Surface:
    surface = pygame.Surface((w, h), pygame.SRCALPHA)
    surface.blit(sheet, (0, 0), pygame.Rect(x, y, w, h))
    return surface


def _tinted(base: pygame.Surface, color: Tuple[int, int, int], alpha: int) -> pygame.Surface:
    result = base.copy()
    overlay = pygame.Surface(base.get_size(), pygame.SRCALPHA)
    overlay.fill((*color, alpha))
    result.blit(overlay, (0, 0))
    return result


def _with_speckles(base: pygame.Surface, color, count: int, radius: int, seed: int) -> pygame.Surface:
    """Scatters small dots at a fixed (seeded, so reproducible) layout --
    used to make tinted ore look like it has visible mineral flecks."""
    result = base.copy()
    w, h = result.get_size()
    rng = random.Random(seed)
    for _ in range(count):
        x = rng.randint(radius, w - radius - 1)
        y = rng.randint(radius, h - radius - 1)
        pygame.draw.circle(result, color, (x, y), radius)
    return result


def _with_horizontal_lines(base: pygame.Surface, color, ys, width: int = 1) -> pygame.Surface:
    result = base.copy()
    w = result.get_width()
    for y in ys:
        pygame.draw.line(result, color, (0, y), (w - 1, y), width)
    return result


def _with_vertical_lines(base: pygame.Surface, color, xs, width: int = 1) -> pygame.Surface:
    result = base.copy()
    h = result.get_height()
    for x in xs:
        pygame.draw.line(result, color, (x, 0), (x, h - 1), width)
    return result


def load_tile_textures() -> Dict[int, pygame.Surface]:
    sheet = pygame.image.load(TERRAIN_PATH).convert_alpha()
    raw_by_id = {
        tile_id: _crop(sheet, col * TERRAIN_CELL, row * TERRAIN_CELL, TERRAIN_CELL, TERRAIN_CELL)
        for tile_id, (col, row) in _TERRAIN_CELLS.items()
    }
    stone_raw = raw_by_id[STONE_ID]
    dirt_raw = raw_by_id[DIRT_ID]
    grass_raw = raw_by_id[GRASS_ID]

    textures = {
        tile_id: pygame.transform.scale(raw, (TILE_SIZE, TILE_SIZE))
        for tile_id, raw in raw_by_id.items()
    }

    # Ore: tinted stone + a handful of seeded speckles so it reads as a
    # mineral deposit rather than a flat color wash over rock.
    coal_raw = _with_speckles(_tinted(stone_raw, (25, 25, 30), 120), (10, 10, 12), count=6, radius=1, seed=1)
    iron_raw = _with_speckles(_tinted(stone_raw, (150, 100, 60), 90), (205, 150, 90), count=6, radius=1, seed=2)
    textures[COAL_ORE_ID] = pygame.transform.scale(coal_raw, (TILE_SIZE, TILE_SIZE))
    textures[IRON_ORE_ID] = pygame.transform.scale(iron_raw, (TILE_SIZE, TILE_SIZE))

    # Bedrock: heavily darkened stone -- reads as "deep, indestructible rock".
    bedrock_raw = _tinted(stone_raw, (5, 5, 8), 215)
    textures[BEDROCK_ID] = pygame.transform.scale(bedrock_raw, (TILE_SIZE, TILE_SIZE))

    # Workbench: tinted dirt + a lighter "tabletop" band and darker leg
    # lines, so the tile silhouette reads as furniture, not a plain block.
    bench_base = _tinted(dirt_raw, (120, 80, 45), 200)
    bench_base = _with_horizontal_lines(bench_base, (170, 130, 80), [3], width=2)
    bench_base = _with_vertical_lines(bench_base, (70, 45, 25), [2, 13], width=2)
    textures[WORKBENCH_ID] = pygame.transform.scale(bench_base, (TILE_SIZE, TILE_SIZE))

    # Tree trunk: tinted dirt + vertical bark-grain lines.
    trunk_base = _tinted(dirt_raw, (90, 55, 25), 190)
    trunk_base = _with_vertical_lines(trunk_base, (60, 35, 15), [4, 8, 12])
    textures[TREE_TRUNK_ID] = pygame.transform.scale(trunk_base, (TILE_SIZE, TILE_SIZE))

    # Tree leaves: the grass sprite's foliage reused directly (real art,
    # just repurposed) with a slightly darker/denser tint for canopy.
    leaves_base = _tinted(grass_raw, (30, 60, 20), 90)
    textures[TREE_LEAVES_ID] = pygame.transform.scale(leaves_base, (TILE_SIZE, TILE_SIZE))

    # Wood plank: lighter, cleaner tint than raw bark + a single seam line
    # per plank -- reads as "cut lumber" rather than a tree trunk.
    plank_base = _tinted(dirt_raw, (150, 110, 65), 200)
    plank_base = _with_horizontal_lines(plank_base, (110, 75, 40), [8])
    textures[WOOD_PLANK_ID] = pygame.transform.scale(plank_base, (TILE_SIZE, TILE_SIZE))

    crate_sheet = pygame.image.load(CRATE_TEXTURE_PATH).convert_alpha()
    textures[DECOR_CRATE_ID] = pygame.transform.scale(crate_sheet, (TILE_SIZE, TILE_SIZE))

    # Chest (Phase 7 structures loot): Box2 -- same pack as the wooden
    # crate (Box1) but never used until now, a distinct-enough color to
    # read as "different from a crate" at a glance.
    chest_sheet = pygame.image.load(CHEST_TEXTURE_PATH).convert_alpha()
    textures[CHEST_ID] = pygame.transform.scale(chest_sheet, (TILE_SIZE, TILE_SIZE))

    # Torch: no source art at all (procedural, transparent background) --
    # a slim stick with a flame, not a full block, since it's a mounted
    # decoration rather than solid terrain.
    torch_raw = pygame.Surface((TERRAIN_CELL, TERRAIN_CELL), pygame.SRCALPHA)
    pygame.draw.line(torch_raw, (120, 80, 45), (8, 15), (8, 8), width=2)
    pygame.draw.polygon(torch_raw, (255, 200, 60), [(8, 2), (11, 8), (8, 6), (5, 8)])
    pygame.draw.polygon(torch_raw, (255, 120, 40), [(8, 4), (10, 8), (8, 7), (6, 8)])
    textures[TORCH_ID] = pygame.transform.scale(torch_raw, (TILE_SIZE, TILE_SIZE))

    # --- Biome ground tiles: same tint-plus-detail technique as above,
    # reusing dirt/stone/grass as the base since no dedicated sand/snow/
    # jungle/mud art exists in the pack (see README "Como criar um bioma"). ---

    sand_base = _with_speckles(_tinted(dirt_raw, (235, 205, 140), 210), (200, 165, 100), count=5, radius=1, seed=10)
    textures[SAND_ID] = pygame.transform.scale(sand_base, (TILE_SIZE, TILE_SIZE))

    sandstone_base = _tinted(stone_raw, (205, 175, 120), 175)
    textures[SANDSTONE_ID] = pygame.transform.scale(sandstone_base, (TILE_SIZE, TILE_SIZE))

    snow_base = _with_speckles(_tinted(grass_raw, (235, 240, 250), 220), (255, 255, 255), count=4, radius=1, seed=11)
    textures[SNOW_BLOCK_ID] = pygame.transform.scale(snow_base, (TILE_SIZE, TILE_SIZE))

    frozen_dirt_base = _tinted(dirt_raw, (170, 190, 205), 190)
    textures[FROZEN_DIRT_ID] = pygame.transform.scale(frozen_dirt_base, (TILE_SIZE, TILE_SIZE))

    jungle_grass_base = _tinted(grass_raw, (30, 110, 35), 120)
    textures[JUNGLE_GRASS_ID] = pygame.transform.scale(jungle_grass_base, (TILE_SIZE, TILE_SIZE))

    mud_base = _tinted(dirt_raw, (65, 50, 30), 200)
    textures[MUD_ID] = pygame.transform.scale(mud_base, (TILE_SIZE, TILE_SIZE))

    # Cactus: procedural (transparent background) -- a simple green body
    # with two side arms and a few spine dots.
    cactus_raw = pygame.Surface((TERRAIN_CELL, TERRAIN_CELL), pygame.SRCALPHA)
    pygame.draw.rect(cactus_raw, (55, 135, 65), pygame.Rect(6, 2, 4, 13), border_radius=2)
    pygame.draw.rect(cactus_raw, (55, 135, 65), pygame.Rect(2, 6, 4, 6), border_radius=2)
    pygame.draw.rect(cactus_raw, (55, 135, 65), pygame.Rect(10, 4, 4, 6), border_radius=2)
    for px, py in ((7, 4), (7, 8), (7, 12), (3, 8), (11, 6)):
        cactus_raw.set_at((px, py), (30, 90, 40, 255))
    textures[CACTUS_ID] = pygame.transform.scale(cactus_raw, (TILE_SIZE, TILE_SIZE))

    # --- Biome-specific underground: same tinted-stone + speckle technique
    # as coal/iron ore above, one tint per biome's deep rock (see README
    # "How biomes work"). ---

    desert_stone_base = _tinted(stone_raw, (150, 125, 90), 150)
    textures[DESERT_STONE_ID] = pygame.transform.scale(desert_stone_base, (TILE_SIZE, TILE_SIZE))

    snow_stone_base = _tinted(stone_raw, (140, 155, 168), 150)
    textures[SNOW_STONE_ID] = pygame.transform.scale(snow_stone_base, (TILE_SIZE, TILE_SIZE))

    jungle_stone_base = _tinted(stone_raw, (85, 110, 75), 150)
    textures[JUNGLE_STONE_ID] = pygame.transform.scale(jungle_stone_base, (TILE_SIZE, TILE_SIZE))

    topaz_raw = _with_speckles(_tinted(stone_raw, (150, 120, 40), 110), (240, 200, 80), count=5, radius=1, seed=12)
    textures[TOPAZ_ORE_ID] = pygame.transform.scale(topaz_raw, (TILE_SIZE, TILE_SIZE))

    sapphire_raw = _with_speckles(_tinted(stone_raw, (40, 70, 140), 110), (90, 140, 230), count=5, radius=1, seed=13)
    textures[SAPPHIRE_ORE_ID] = pygame.transform.scale(sapphire_raw, (TILE_SIZE, TILE_SIZE))

    emerald_raw = _with_speckles(_tinted(stone_raw, (30, 110, 65), 110), (70, 200, 130), count=5, radius=1, seed=14)
    textures[EMERALD_ORE_ID] = pygame.transform.scale(emerald_raw, (TILE_SIZE, TILE_SIZE))

    # Berry bush: procedural (transparent background) -- a rounded leafy
    # clump with a few berry dots, no dedicated bush art in the pack.
    bush_raw = pygame.Surface((TERRAIN_CELL, TERRAIN_CELL), pygame.SRCALPHA)
    pygame.draw.ellipse(bush_raw, (55, 115, 50), pygame.Rect(1, 5, 14, 10))
    pygame.draw.ellipse(bush_raw, (70, 140, 60), pygame.Rect(3, 2, 10, 8))
    for px, py, color in (
        (4, 8, (200, 40, 60)), (9, 6, (220, 190, 60)), (11, 10, (200, 40, 60)), (6, 11, (220, 190, 60)),
    ):
        pygame.draw.circle(bush_raw, color, (px, py), 1)
    textures[BUSH_ID] = pygame.transform.scale(bush_raw, (TILE_SIZE, TILE_SIZE))

    # Spikes and Trampoline: real source art (Traps/), each already a
    # single flat frame the same way Box1/Idle.png is used for the crate.
    spikes_sheet = pygame.image.load(SPIKES_TEXTURE_PATH).convert_alpha()
    textures[SPIKES_ID] = pygame.transform.scale(spikes_sheet, (TILE_SIZE, TILE_SIZE))
    trampoline_sheet = pygame.image.load(TRAMPOLINE_TEXTURE_PATH).convert_alpha()
    textures[TRAMPOLINE_ID] = pygame.transform.scale(trampoline_sheet, (TILE_SIZE, TILE_SIZE))

    # Fan: real source art, first frame of the "on" spin strip -- like
    # Spikes/Trampoline this renders as a static tile (no per-tile animation
    # state exists for the plain id->texture cache _tile_texture uses).
    fan_sheet = pygame.image.load(FAN_ON_PATH).convert_alpha()
    fan_raw = _crop(fan_sheet, 0, 0, 24, 8)
    textures[FAN_ID] = pygame.transform.scale(fan_raw, (TILE_SIZE, TILE_SIZE))

    # Sand/Mud/Ice traps: the pack's dedicated "Sand Mud Ice (16x6)" sheet
    # has no documented cell layout, so -- same call already made for every
    # biome ground tile with no single-cell source art -- these reuse the
    # closest tinted base tile instead of guessing at an ambiguous slice.
    trap_sand_base = _with_speckles(_tinted(dirt_raw, (235, 205, 140), 210), (200, 165, 100), count=5, radius=1, seed=20)
    textures[TRAP_SAND_ID] = pygame.transform.scale(trap_sand_base, (TILE_SIZE, TILE_SIZE))
    trap_mud_base = _tinted(dirt_raw, (65, 50, 30), 205)
    textures[TRAP_MUD_ID] = pygame.transform.scale(trap_mud_base, (TILE_SIZE, TILE_SIZE))
    trap_ice_base = _tinted(stone_raw, (200, 230, 245), 190)
    textures[TRAP_ICE_ID] = pygame.transform.scale(trap_ice_base, (TILE_SIZE, TILE_SIZE))

    # Falling Platform: default/idle texture only -- the "about to crumble"
    # shake animation is loaded separately (load_crumble_shake_frames) since
    # it's a per-frame state swap the renderer special-cases, not a static
    # id->texture mapping.
    crumble_sheet = pygame.image.load(CRUMBLE_OFF_PATH).convert_alpha()
    textures[CRUMBLE_PLATFORM_ID] = pygame.transform.scale(crumble_sheet, (TILE_SIZE, TILE_SIZE))

    # Checkpoint: default/inactive ("No Flag") texture only -- the active
    # flag-waving animation is loaded separately (load_checkpoint_active_frames)
    # for the same reason as Falling Platform above.
    checkpoint_sheet = pygame.image.load(CHECKPOINT_NO_FLAG_PATH).convert_alpha()
    textures[CHECKPOINT_ID] = pygame.transform.scale(checkpoint_sheet, (TILE_SIZE, TILE_SIZE))

    # Furnace: tinted stone (like the Workbench's tinted dirt) + a dark
    # "mouth" opening and a warm ember glow -- no dedicated furnace art in
    # the pack, so this is the same tint-plus-detail technique as every
    # other structural tile with no single-cell source (see module docstring).
    furnace_base = _tinted(stone_raw, (70, 65, 70), 205)
    pygame.draw.rect(furnace_base, (30, 26, 28), pygame.Rect(4, 9, 8, 6))
    pygame.draw.rect(furnace_base, (235, 130, 40), pygame.Rect(5, 11, 6, 3))
    furnace_base = _with_horizontal_lines(furnace_base, (40, 36, 40), [2], width=1)
    textures[FURNACE_ID] = pygame.transform.scale(furnace_base, (TILE_SIZE, TILE_SIZE))

    return textures


def load_crumble_shake_frames(size: int = TILE_SIZE) -> List[pygame.Surface]:
    sheet = pygame.image.load(CRUMBLE_ON_PATH).convert_alpha()
    frame_count = sheet.get_width() // 32
    return [pygame.transform.scale(_crop(sheet, i * 32, 0, 32, 10), (size, size)) for i in range(frame_count)]


def load_checkpoint_active_frames(size: int = TILE_SIZE) -> List[pygame.Surface]:
    sheet = pygame.image.load(CHECKPOINT_FLAG_IDLE_PATH).convert_alpha()
    frame_count = sheet.get_width() // 64
    return [pygame.transform.scale(_crop(sheet, i * 64, 0, 64, 64), (size, size)) for i in range(frame_count)]


def load_hazard_textures(size_px: int = TILE_SIZE) -> Dict[str, List[pygame.Surface]]:
    """Sprite frames for the moving hazards (Saw/Rock Head/Spike Head/
    Spiked Ball), keyed by hazard_feature kind. Each is a real source-art
    animation strip (Spiked Ball is a single static sprite, duplicated into
    a 2-entry idle+hit list so it fits `Renderer._draw_hazard_sprite`'s
    "last frame is the impact frame" convention); scaled to that hazard's
    own rect size (hazard_feature width/height tiles), not the plain tile
    size -- these aren't tile-grid entries."""

    def _frames(path: str, frame_w: int, frame_h: int, out_size: int) -> List[pygame.Surface]:
        sheet = pygame.image.load(path).convert_alpha()
        count = sheet.get_width() // frame_w
        return [pygame.transform.scale(_crop(sheet, i * frame_w, 0, frame_w, frame_h), (out_size, out_size)) for i in range(count)]

    saw_size = int(round(size_px * 0.9))
    rock_head_size = int(round(size_px * 1.0))
    spike_head_size = int(round(size_px * 1.1))
    spiked_ball_size = int(round(size_px * 0.8))

    saw_frames = _frames(SAW_ON_PATH, 38, 38, saw_size)
    rock_head_idle = _frames(ROCK_HEAD_IDLE_PATH, 42, 42, rock_head_size)
    rock_head_hit = _frames(ROCK_HEAD_HIT_PATH, 42, 42, rock_head_size)[:1]
    spike_head_idle = _frames(SPIKE_HEAD_IDLE_PATH, 54, 52, spike_head_size)
    spike_head_hit = _frames(SPIKE_HEAD_HIT_PATH, 54, 52, spike_head_size)[:1]
    spiked_ball = _frames(SPIKED_BALL_PATH, 28, 28, spiked_ball_size)

    chain_link = pygame.image.load(SAW_CHAIN_PATH).convert_alpha()

    return {
        hazard_feature.SAW: saw_frames,
        hazard_feature.ROCK_HEAD: rock_head_idle + rock_head_hit,
        hazard_feature.SPIKE_HEAD: spike_head_idle + spike_head_hit,
        hazard_feature.SPIKED_BALL: spiked_ball + spiked_ball,
        "saw_chain_link": [chain_link],
    }


def load_particle_textures() -> Dict[str, List[pygame.Surface]]:
    dust = pygame.image.load(DUST_PARTICLE_PATH).convert_alpha()
    confetti_sheet = pygame.image.load(CONFETTI_PATH).convert_alpha()
    confetti_count = confetti_sheet.get_width() // CONFETTI_CELL
    confetti_frames = [
        _crop(confetti_sheet, i * CONFETTI_CELL, 0, CONFETTI_CELL, CONFETTI_CELL)
        for i in range(confetti_count)
    ]
    return {"dust": [dust], "confetti": confetti_frames}


def load_shadow_texture() -> pygame.Surface:
    return pygame.image.load(SHADOW_PATH).convert_alpha()


def load_menu_button_icons() -> Dict[str, pygame.Surface]:
    names = {"play": "Play.png", "settings": "Settings.png", "restart": "Restart.png", "close": "Close.png", "back": "Back.png"}
    icons = {key: pygame.image.load(os.path.join(MENU_BUTTONS_DIR, filename)).convert_alpha() for key, filename in names.items()}
    # No Save/Load art exists in the pack (Phase 7) -- hand-drawn vector
    # icons, same precedent as _build_procedural_icons uses for missing
    # tool/weapon art.
    icons["save"] = _build_save_icon()
    icons["load"] = _build_load_icon()
    return icons


def _build_save_icon(size: int = 32) -> pygame.Surface:
    """A floppy disk: body outline, a notched top-right corner, a metal
    slider near the top, a label rectangle near the bottom."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    color = (220, 220, 225)
    body = pygame.Rect(size * 0.15, size * 0.12, size * 0.7, size * 0.76)
    pygame.draw.rect(surf, color, body, width=3, border_radius=3)
    pygame.draw.rect(surf, color, (size * 0.35, size * 0.16, size * 0.3, size * 0.2))
    pygame.draw.rect(surf, color, (size * 0.28, size * 0.55, size * 0.44, size * 0.28), width=2)
    return surf


def _build_load_icon(size: int = 32) -> pygame.Surface:
    """A downward arrow into a tray: the classic "load/import" glyph."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    color = (220, 220, 225)
    pygame.draw.line(surf, color, (size * 0.5, size * 0.1), (size * 0.5, size * 0.55), width=4)
    pygame.draw.polygon(surf, color, [
        (size * 0.3, size * 0.45), (size * 0.7, size * 0.45), (size * 0.5, size * 0.72),
    ])
    pygame.draw.line(surf, color, (size * 0.18, size * 0.85), (size * 0.82, size * 0.85), width=4)
    return surf


def _build_procedural_icons(size: int = 32) -> Dict[str, pygame.Surface]:
    """Small hand-drawn vector icons for items that have neither a matching
    tile nor sprite art in assets/ (no tool/weapon/armor icons exist in the
    pack). Simple shapes beat an anonymous color swatch."""
    icons: Dict[str, pygame.Surface] = {}

    def new_surface():
        return pygame.Surface((size, size), pygame.SRCALPHA)

    # Pickaxes: a handle plus a curved head; color varies by tier.
    for item_id, head_color, handle_color in (
        ("wood_pickaxe", (150, 110, 65), (100, 70, 40)),
        ("stone_pickaxe", (150, 150, 158), (100, 70, 40)),
    ):
        surf = new_surface()
        pygame.draw.line(surf, handle_color, (size * 0.25, size * 0.85), (size * 0.75, size * 0.2), width=4)
        pygame.draw.arc(
            surf, head_color,
            pygame.Rect(size * 0.35, size * 0.05, size * 0.55, size * 0.55),
            start_angle=3.6, stop_angle=6.0, width=6,
        )
        icons[item_id] = surf

    # Sword: a blade with a crossguard and grip.
    surf = new_surface()
    pygame.draw.line(surf, (190, 190, 200), (size * 0.5, size * 0.1), (size * 0.5, size * 0.65), width=5)
    pygame.draw.line(surf, (120, 90, 50), (size * 0.3, size * 0.65), (size * 0.7, size * 0.65), width=4)
    pygame.draw.line(surf, (90, 65, 35), (size * 0.5, size * 0.65), (size * 0.5, size * 0.9), width=4)
    icons["wood_sword"] = surf

    # Wood helmet: a simple dome, wood-toned.
    surf = new_surface()
    pygame.draw.arc(
        surf, (150, 110, 65),
        pygame.Rect(size * 0.15, size * 0.25, size * 0.7, size * 0.6),
        start_angle=3.14159, stop_angle=6.28318, width=7,
    )
    pygame.draw.line(surf, (150, 110, 65), (size * 0.15, size * 0.55), (size * 0.85, size * 0.55), width=5)
    icons["wood_helmet"] = surf

    # Wood armor: a chestpiece silhouette (torso + shoulder studs).
    surf = new_surface()
    pygame.draw.polygon(surf, (150, 110, 65), [
        (size * 0.5, size * 0.12), (size * 0.82, size * 0.28), (size * 0.72, size * 0.9),
        (size * 0.28, size * 0.9), (size * 0.18, size * 0.28),
    ])
    pygame.draw.circle(surf, (100, 70, 40), (int(size * 0.28), int(size * 0.3)), int(size * 0.08))
    pygame.draw.circle(surf, (100, 70, 40), (int(size * 0.72), int(size * 0.3)), int(size * 0.08))
    pygame.draw.line(surf, (100, 70, 40), (size * 0.5, size * 0.2), (size * 0.5, size * 0.85), width=2)
    icons["wood_armor"] = surf

    # Bow: a curved limb plus a taut string.
    surf = new_surface()
    pygame.draw.arc(
        surf, (140, 95, 55),
        pygame.Rect(size * 0.2, size * 0.05, size * 0.6, size * 0.9),
        start_angle=-1.3, stop_angle=1.3, width=5,
    )
    pygame.draw.line(surf, (220, 220, 220), (size * 0.62, size * 0.12), (size * 0.62, size * 0.88), width=2)
    icons["wood_bow"] = surf

    # Arrow: a shaft with a triangular head and fletching.
    surf = new_surface()
    pygame.draw.line(surf, (120, 90, 50), (size * 0.15, size * 0.85), (size * 0.75, size * 0.25), width=3)
    pygame.draw.polygon(surf, (150, 150, 158), [
        (size * 0.75, size * 0.25), (size * 0.55, size * 0.35), (size * 0.65, size * 0.15),
    ])
    pygame.draw.line(surf, (200, 60, 60), (size * 0.15, size * 0.85), (size * 0.3, size * 0.65), width=3)
    pygame.draw.line(surf, (200, 60, 60), (size * 0.15, size * 0.85), (size * 0.35, size * 0.8), width=3)
    icons["arrow"] = surf

    # Slime gel: a small green droplet with a highlight.
    surf = new_surface()
    pygame.draw.ellipse(surf, (100, 210, 120), pygame.Rect(size * 0.2, size * 0.3, size * 0.6, size * 0.55))
    pygame.draw.polygon(surf, (100, 210, 120), [
        (size * 0.5, size * 0.1), (size * 0.35, size * 0.4), (size * 0.65, size * 0.4),
    ])
    pygame.draw.ellipse(surf, (200, 250, 210), pygame.Rect(size * 0.3, size * 0.4, size * 0.15, size * 0.12))
    icons["slime_gel"] = surf

    # Feather: an elongated leaf shape with a center quill line.
    surf = new_surface()
    pygame.draw.ellipse(surf, (225, 225, 235), pygame.Rect(size * 0.35, size * 0.1, size * 0.3, size * 0.75))
    pygame.draw.line(surf, (150, 90, 170), (size * 0.5, size * 0.15), (size * 0.5, size * 0.85), width=2)
    icons["feather"] = surf

    # Bars (furnace output): a classic trapezoid ingot silhouette, one color
    # per metal, with a lighter highlight band so it doesn't read as a flat
    # swatch. No dedicated bar/ingot art exists in the pack.
    for item_id, base_color, highlight_color in (
        ("iron_bar", (170, 170, 178), (215, 215, 222)),
        ("topaz_bar", (210, 170, 60), (240, 205, 110)),
        ("sapphire_bar", (60, 100, 200), (110, 150, 235)),
        ("emerald_bar", (50, 160, 95), (100, 210, 140)),
    ):
        surf = new_surface()
        pygame.draw.polygon(surf, base_color, [
            (size * 0.2, size * 0.68), (size * 0.32, size * 0.32), (size * 0.68, size * 0.32), (size * 0.8, size * 0.68),
        ])
        pygame.draw.line(surf, highlight_color, (size * 0.34, size * 0.4), (size * 0.66, size * 0.4), width=2)
        pygame.draw.polygon(surf, (0, 0, 0), [
            (size * 0.2, size * 0.68), (size * 0.32, size * 0.32), (size * 0.68, size * 0.32), (size * 0.8, size * 0.68),
        ], width=1)
        icons[item_id] = surf

    # Iron Pickaxe: same shape as the wood/stone pickaxes above, iron-toned.
    surf = new_surface()
    pygame.draw.line(surf, (100, 70, 40), (size * 0.25, size * 0.85), (size * 0.75, size * 0.2), width=4)
    pygame.draw.arc(
        surf, (190, 190, 198),
        pygame.Rect(size * 0.35, size * 0.05, size * 0.55, size * 0.55),
        start_angle=3.6, stop_angle=6.0, width=6,
    )
    icons["iron_pickaxe"] = surf

    return icons


def load_static_item_icons() -> Dict[str, pygame.Surface]:
    icons = {}
    for item_id, (path, frame_size) in _STATIC_ICON_SOURCES.items():
        sheet = pygame.image.load(path).convert_alpha()
        frame = _crop(sheet, 0, 0, frame_size, min(frame_size, sheet.get_height()))
        icons[item_id] = frame
    icons.update(_build_procedural_icons())
    return icons


def _load_strip(path: str) -> List[pygame.Surface]:
    sheet = pygame.image.load(path).convert_alpha()
    frame_count = sheet.get_width() // PLAYER_FRAME_SIZE
    return [
        _crop(sheet, i * PLAYER_FRAME_SIZE, 0, PLAYER_FRAME_SIZE, PLAYER_FRAME_SIZE)
        for i in range(frame_count)
    ]


def load_player_animations(target_size: int, character_dir: str = PLAYER_CHARACTER_DIR) -> Dict[Tuple[str, str], List[pygame.Surface]]:
    animations: Dict[Tuple[str, str], List[pygame.Surface]] = {}
    for state_name, filename in PLAYER_ANIMATIONS.items():
        frames = _load_strip(os.path.join(character_dir, filename))
        frames = [pygame.transform.scale(f, (target_size, target_size)) for f in frames]
        animations[(state_name, "right")] = frames
        animations[(state_name, "left")] = [pygame.transform.flip(f, True, False) for f in frames]
    return animations


def load_all_character_animations(target_size: int) -> Dict[str, Dict[Tuple[str, str], List[pygame.Surface]]]:
    """Every registered playable character's animations (see
    character_registry.py), keyed by character id -- the character-select
    screen and Player rendering both need every skin available up front,
    not just the one currently selected."""
    return {
        character.id: load_player_animations(target_size, character.asset_dir)
        for character in character_registry.all_characters()
    }


def load_background_tile() -> pygame.Surface:
    return pygame.image.load(BACKGROUND_PATH).convert_alpha()
