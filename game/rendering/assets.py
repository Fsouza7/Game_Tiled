"""Loads and slices the real art in assets/ (must run after pygame.display
is initialized, since convert_alpha() needs a display surface).

Grass/dirt (assets/Tiles/Tileset Outside.png) and stone (Tileset Inside.png)
are the only tile materials with dedicated art -- one representative 32px
cell each, not the full neighbor-aware autotiling both sheets have the
pieces for. Tiles with no matching material of their own (ore, bedrock,
workbench, tree trunk/planks) reuse the closest of those three base
sprites with a color tint plus a small procedural detail (speckles,
plank/bark lines) drawn on top so they read as a distinct material rather
than a flat color wash. This is documented here and in README.md rather
than pretended away.

Item icons follow the same idea: a block icon reuses its tile texture (see
ItemDef.places_tile_id / icon_tile_id); the one item with no matching
tile/sprite and no entry in the user-supplied icon sheet below (the arrow)
gets a small hand-drawn vector icon instead of an anonymous color swatch --
see `_build_procedural_icons`.

Spikes and Trampoline reuse dedicated art from assets/Traps/ directly (real,
single-frame source images, no tint/detail pass needed); the fruit
consumables reuse assets/Items/Fruits/ the same way Apple already did.

The background is a user-supplied 4-layer parallax pack
(BACKGROUND_LAYER_PATHS, assets/Backgrounds/) instead of a flat tiled
color; trees (TREE_ID) render as a real sprite from assets/Tiles/Trees.png
instead of stacked tile blocks -- see README "How the parallax background
works" / "How trees work" for both.

A user-supplied 512x867 icon sheet (assets/Items/#2 - Transparent Icons &
Drop Shadow.png, a 16-column x 32px-cell grid of ~350 hand-drawn fantasy
RPG icons) covers most other items -- see `_SHEET_ICON_CELLS` for direct
single-icon matches (Wood Sword, ores, boss items, ...), and
`_PICKAXE_BASE_CELL`/`_INGOT_BASE_CELL`/`_ARMOR_BASE_CELLS`/`_CROWN_BASE_CELL`
for real sheet shapes recolored per tier with `_colorize` (pickaxes, bars,
armor sets, the Crown of the Slime King) instead of vector-drawn tiers.
Sliced by `_load_sheet_item_icons` and layered on top of the procedural
icons in `load_static_item_icons`, so a sheet icon always wins over a
vector one for the same key.
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
    PERSONAL_CHEST_ID, DOOR_CLOSED_ID, DOOR_OPEN_ID, BED_ID,
)
from game.entities import character_registry
from game.world import hazard_feature

# TERRAIN_CELL (16px) is still used below for the handful of tiles built
# from scratch as blank canvases (torch/cactus/bush) -- unrelated to the
# tilesets below, which are native 32px and used as-is.
TERRAIN_CELL = 16

# User-supplied dedicated tilesets (32px cells, an (row, col) grid) --
# replaced the single mixed-theme Terrain.png this project started with,
# which only had a grass/dirt/stone cell usable for this game anyway (see
# README "Art reuse"). Outside covers the surface (grass-topped dirt,
# plain dirt); Inside covers underground stone.
TILESET_OUTSIDE_PATH = os.path.join("assets", "Tiles", "Tileset Outside.png")
TILESET_INSIDE_PATH = os.path.join("assets", "Tiles", "Tileset Inside.png")
TILESET_CELL = 32

# (row, col) of the chosen 32x32 cell for each material -- a single
# representative cell per tile id, the same "one fixed texture regardless
# of neighbors" approach the old Terrain.png cells used (not a full
# neighbor-aware autotile system, even though both sheets include the
# pieces for one).
_OUTSIDE_TILESET_CELLS = {
    GRASS_ID: (0, 4),
    DIRT_ID: (1, 4),
}
_INSIDE_TILESET_CELLS = {
    STONE_ID: (1, 5),
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

# Layered parallax background (user-supplied), back to front. Each PNG is
# a full 320x320 tile: Sky is opaque and covers the whole canvas; the other
# three have a transparent top half and an opaque silhouette (clouds /
# distant rock peaks / nearer grassy peaks) along the bottom, meant to be
# stacked and each scrolled at its own speed for a depth effect -- see
# Renderer._draw_background and settings.BACKGROUND_LAYER_PARALLAX.
BACKGROUND_LAYER_PATHS = {
    "sky": os.path.join("assets", "Backgrounds", "Sky.png"),
    "clouds": os.path.join("assets", "Backgrounds", "Clouds.png"),
    "rock_mountains": os.path.join("assets", "Backgrounds", "Rock Mountains.png"),
    "grass_mountains": os.path.join("assets", "Backgrounds", "Grass Mountains.png"),
}

CRATE_TEXTURE_PATH = os.path.join("assets", "Items", "Boxes", "Box1", "Idle.png")
CHEST_TEXTURE_PATH = os.path.join("assets", "Items", "Boxes", "Box2", "Idle.png")
PERSONAL_CHEST_TEXTURE_PATH = os.path.join("assets", "Items", "Boxes", "Box3", "Idle.png")
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

ENEMIES_DIR = os.path.join("assets", "Enemies")
BAT_PATH = os.path.join(ENEMIES_DIR, "Bat.png")
BAT_CELL = 48  # 240x192 = 5 x 4 cells -- almost-static poses, unused
MINI_BAT_PATH = os.path.join(ENEMIES_DIR, "mini bat.png")
MINI_BAT_CELL = 32  # 224x128 = 7 x 4 cells; row 0 hover, row 1 dive
SLIME_IDLE_PATH = os.path.join(ENEMIES_DIR, "Mini_Slime_Idle.png")
SLIME_WALK_PATH = os.path.join(ENEMIES_DIR, "Mini_Slime_Walk.png")
SLIME_HURT_PATH = os.path.join(ENEMIES_DIR, "Mini_Slime_Hurt.png")
SLIME_FRAME = 32
SCORPION_DIR = os.path.join(ENEMIES_DIR, "Scorpian")
SCORPION_IDLE_PATH = os.path.join(SCORPION_DIR, "Idel.png")
SCORPION_WALK_PATH = os.path.join(SCORPION_DIR, "Walk.png")
SCORPION_ATTACK_PATH = os.path.join(SCORPION_DIR, "Attack.png")
SCORPION_FRAME = 32
DUSKWING_SPRITE_SIZE = 64  # 2x the 32px mini-bat cells, keeps the flap crisp
SLIME_SPRITE_SIZE = 48
SLIME_KING_SPRITE_SIZE = 96
MOSQUITO_PATH = os.path.join(ENEMIES_DIR, "mosquito.png")
MOSQUITO_CELL = 48  # 240x96 = 5 x 2 cells; row 0 flap (col 4 empty), row 1 splat
SWAMP_MOSQUITO_SPRITE_SIZE = 64
FROST_HOPPER_SPRITE_SIZE = SLIME_SPRITE_SIZE

FLYING_HEAD_PATH = os.path.join("assets", "flying-head.png")
FLYING_HEAD_CELL = 64  # 768x320 sheet = 12 x 5 cells
IRON_GUARDIAN_SPRITE_SIZE = 64
SCORPION_SPRITE_SIZE = 48
EYEBALL_PATH = os.path.join(ENEMIES_DIR, "Eyeball.png")
EYEBALL_CELL = 48  # 288x96 sheet = 6 x 2 cells; row 0 idle, row 1 chase (cols 4-5 splat)
CRAWLER_SPRITE_SIZE = 48

# --- UI reskin (user-supplied pack in assets/validar/UI, a top-down
# survival asset pack). The character/enemy/nature art in that pack is
# top-down and thematically a zombie shooter, so none of it fits this
# side-view fantasy-mining game -- see README "How the UI theme works" --
# but its UI chrome (health bar, wood-plank buttons, panel frames, item
# slots) is plain 2D art with no perspective to clash, so it reskins every
# panel/button/slot in the game. ---
_VALIDAR_UI_DIR = os.path.join("assets", "validar", "UI")
HP_BAR_FRAME_PATH = os.path.join(_VALIDAR_UI_DIR, "HP", "HP-Bar.png")
HP_BAR_FILL_PATH = os.path.join(_VALIDAR_UI_DIR, "HP", "HP.png")
UI_PANEL_TEXTURE_PATH = os.path.join(_VALIDAR_UI_DIR, "Inventory", "Inventory_1.png")
UI_CELL_TEXTURE_PATH = os.path.join(_VALIDAR_UI_DIR, "Inventory", "Inventory-Cell.png")
UI_CELL_CHOSEN_TEXTURE_PATH = os.path.join(_VALIDAR_UI_DIR, "Inventory", "Inventory-Chosen.png")
_UI_BUTTON_DIR = os.path.join(_VALIDAR_UI_DIR, "Menu", "Main Menu")
_UI_BUTTON_FILES = {
    "play": ("Play_Not-Pressed.png", "Play_Pressed.png"),
    "load": ("Load_Not-Pressed.png", "Load_Pressed.png"),
    "save": ("Save_Not-Pressed.png", "Save_Pressed.png"),
    "settings": ("Settings_Not-Pressed.png", "Settings_Pressed.png"),
    "quit": ("Quit_Not-Pressed.png", "Quit_Pressed.png"),
    "blank": ("Blank_Not-Pressed.png", "Blank_Pressed.png"),
}

_FRUITS_DIR = os.path.join("assets", "Items", "Fruits")

# A user-supplied 16x27 grid of hand-drawn item icons (32px cells, see
# assets/Items/#2 - Transparent Icons & Drop Shadow.png), (row, col). Keyed
# by the same icon_key/item_id used elsewhere, so `load_static_item_icons`
# can just overlay these on top of the procedural ones -- real art wins
# where both exist for the same key.
ITEM_ICON_SHEET_PATH = os.path.join("assets", "Items", "#2 - Transparent Icons & Drop Shadow.png")
ITEM_ICON_SHEET_CELL = 32

# Items with one unambiguous single-icon match -- cropped as-is, no tinting.
_SHEET_ICON_CELLS = {
    "wood_sword": (5, 0),
    "wood_bow": (6, 3),
    "grapple_hook": (16, 0),  # a bent fishing hook, from the sheet's fishing-tackle row
    "slime_gel": (0, 1),
    "feather": (17, 10),
    "coin": (12, 7),
    # Ores previously borrowed their own tile's texture as a placeholder
    # icon (see item_registry.py) -- these loose-ore-chunk icons read more
    # like something you'd actually carry than a reused block texture.
    "coal": (20, 2),
    "iron_ore": (20, 12),
    "topaz": (20, 8),
    "sapphire": (20, 6),
    "emerald": (20, 7),
    # Boss items previously had no icon at all (flat category swatch).
    "slime_core_idol": (18, 2),   # glowing green orb -- a summoning totem
    "slime_king_core": (17, 4),   # a rare-looking gem, distinct from the ore gems above
    # Already the right natural color as-is (a plain wood-brown rod).
    "summon_rod_wood": (6, 7),
    # Row 9 is the sheet's unused potion/flask row; (9, 0) is the classic
    # red round flask (don't reuse slime_core_idol's green orb at 18,2).
    "healing_potion": (9, 0),
    # Same feather cell as the duskwing drop it crafts from -- a charm
    # made of feathers should look like feathers, not another tinted ring.
    "feather_charm": (17, 10),
}

# Same real shape, recolored -- these don't fit _TIER_COLORS's wood/iron/
# steel/arcane naming (only one non-wood tier each), so handled directly
# rather than folded into the loops below.
_SUMMON_ROD_IRON_CELL = (6, 7)          # same plain rod as summon_rod_wood, tinted iron-gray
_ARCANE_STAFF_CELL = (6, 8)             # a gemmed wand, tinted arcane purple

# Equipment/tool/bar sets where the sheet only has *one* shape per slot, but
# the game needs several tinted tiers of it -- recolored per tier with
# _colorize instead of getting a flat vector fill (_build_procedural_icons
# used to draw all of these; removed there once covered here).
_TIER_COLORS = {
    "wood": (150, 110, 65),
    "stone": (150, 150, 158),
    "iron": (170, 170, 178),
    "steel": (120, 130, 145),
    "arcane": (150, 100, 210),
    # The itemization pass's post-Arcane endgame tier -- a deeper, more
    # saturated violet-black than arcane so the two read as clearly
    # different tiers side by side, not just a lighter/darker copy.
    "voidsteel": (75, 35, 115),
}
_PICKAXE_BASE_CELL = (10, 2)
_PICKAXE_TIERS = ("wood", "stone", "iron", "steel", "arcane")  # -> "<tier>_pickaxe"

# Same real sword/bow shapes as wood_sword/wood_bow's own (natural-color,
# see _SHEET_ICON_CELLS) cells, recolored per tier -- the itemization pass
# filled in Iron/Steel/Arcane/Voidsteel swords and Iron/Steel bows, which
# had no icons of their own yet (see item_registry.py's icon_key on each).
_SWORD_BASE_CELL = (5, 0)
_SWORD_TIERS = ("iron", "steel", "arcane", "voidsteel")  # -> "<tier>_sword" (wood_sword has its own direct cell above)
_BOW_BASE_CELL = (6, 3)
_BOW_TIERS = ("iron", "steel")  # -> "<tier>_bow" (wood_bow has its own direct cell above)

_INGOT_BASE_CELL = (17, 3)
_BAR_COLORS = {
    "iron_bar": (170, 170, 178),
    "steel_bar": (120, 130, 145),
    "topaz_bar": (210, 170, 60),
    "sapphire_bar": (60, 100, 200),
    "emerald_bar": (50, 160, 95),
    "arcane_bar": (140, 90, 210),
    "voidsteel_bar": _TIER_COLORS["voidsteel"],
}
# A plain raw-stone-chunk shape (distinct from the ore-pile icons already
# used for coal/iron_ore/the three gems -- Voidstone needed to read as its
# own thing, not a recolor of coal's identical pile shape), recolored void.
_VOID_ORE_CELL = (17, 1)

# slot suffix -> base cell; combined with tier as f"{tier}_{slot}" (matches
# item_registry.py's naming, e.g. "wood_helmet"/"iron_armor"). Arcane only
# has a helmet (the Crown of the Slime King is head-slot too, but gets its
# own distinct base/tint below rather than reusing this helmet shape).
_ARMOR_BASE_CELLS = {
    "helmet": (7, 4),
    "armor": (7, 7),
    "greaves": (7, 10),
    "boots": (8, 3),
}
_ARMOR_TIERS = ("wood", "iron", "steel")  # arcane_helmet handled separately below

_CROWN_BASE_CELL = (7, 3)  # a paladin-style helm, recolored gold/red for royalty
_CROWN_COLOR = (225, 180, 70)

# Jewelry row (accessory slot items) -- a gold ring, a gemmed necklace and
# a beaded bracelet, each recolored per item so multiple accessories can
# share one shape family instead of needing a unique cell each.
_ACCESSORY_RING_CELL = (8, 5)
_ACCESSORY_AMULET_CELL = (8, 6)
_ACCESSORY_BRACELET_CELL = (8, 7)


def _load_sheet_item_icons() -> Dict[str, pygame.Surface]:
    sheet = pygame.image.load(ITEM_ICON_SHEET_PATH).convert_alpha()
    cell = ITEM_ICON_SHEET_CELL

    def crop_cell(row: int, col: int) -> pygame.Surface:
        return _crop(sheet, col * cell, row * cell, cell, cell)

    icons = {key: crop_cell(row, col) for key, (row, col) in _SHEET_ICON_CELLS.items()}

    pickaxe_base = crop_cell(*_PICKAXE_BASE_CELL)
    for tier in _PICKAXE_TIERS:
        icons[f"{tier}_pickaxe"] = _colorize(pickaxe_base, _TIER_COLORS[tier])

    ingot_base = crop_cell(*_INGOT_BASE_CELL)
    for item_id, color in _BAR_COLORS.items():
        icons[item_id] = _colorize(ingot_base, color)

    for slot, base_cell in _ARMOR_BASE_CELLS.items():
        base = crop_cell(*base_cell)
        for tier in _ARMOR_TIERS:
            icons[f"{tier}_{slot}"] = _colorize(base, _TIER_COLORS[tier])
    icons["arcane_helmet"] = _colorize(crop_cell(*_ARMOR_BASE_CELLS["helmet"]), _TIER_COLORS["arcane"])

    icons["slime_king_crown"] = _colorize(crop_cell(*_CROWN_BASE_CELL), _CROWN_COLOR)
    icons["summon_rod_iron"] = _colorize(crop_cell(*_SUMMON_ROD_IRON_CELL), _TIER_COLORS["iron"])
    icons["arcane_staff"] = _colorize(crop_cell(*_ARCANE_STAFF_CELL), _TIER_COLORS["arcane"])

    # --- Itemization pass: sprites for every item that previously fell
    # back to a flat category-color swatch (see item_registry.py's
    # icon_key on each -- these dict keys match those exactly). Same
    # "one real shape, recolored per tier" technique as everything above. ---

    sword_base = crop_cell(*_SWORD_BASE_CELL)
    for tier in _SWORD_TIERS:
        icons[f"{tier}_sword"] = _colorize(sword_base, _TIER_COLORS[tier])

    bow_base = crop_cell(*_BOW_BASE_CELL)
    for tier in _BOW_TIERS:
        icons[f"{tier}_bow"] = _colorize(bow_base, _TIER_COLORS[tier])

    rod_base = crop_cell(*_SUMMON_ROD_IRON_CELL)  # same plain-rod shape as summon_rod_wood/iron above
    for tier in ("steel", "arcane", "voidsteel"):
        icons[f"summon_rod_{tier}"] = _colorize(rod_base, _TIER_COLORS[tier])

    # Arcane armor completion (arcane_helmet already registered above) --
    # note the body slot's item id is "arcane_body", not "arcane_armor"
    # (unlike every other tier's f"{tier}_armor" naming), so this can't
    # join the generic _ARMOR_TIERS loop.
    icons["arcane_body"] = _colorize(crop_cell(*_ARMOR_BASE_CELLS["armor"]), _TIER_COLORS["arcane"])
    icons["arcane_greaves"] = _colorize(crop_cell(*_ARMOR_BASE_CELLS["greaves"]), _TIER_COLORS["arcane"])
    icons["arcane_boots"] = _colorize(crop_cell(*_ARMOR_BASE_CELLS["boots"]), _TIER_COLORS["arcane"])

    # Voidsteel's full armor set -- slot names match _ARMOR_BASE_CELLS
    # exactly (helmet/armor/greaves/boots), so this one's a clean loop.
    for slot, base_cell in _ARMOR_BASE_CELLS.items():
        icons[f"voidsteel_{slot}"] = _colorize(crop_cell(*base_cell), _TIER_COLORS["voidsteel"])

    icons["voidstone"] = _colorize(crop_cell(*_VOID_ORE_CELL), _TIER_COLORS["voidsteel"])

    # Slime King's farmable side-grade weapon/armor -- tinted the same
    # royal gold/red as the existing Crown so the three read as one set.
    icons["slime_king_fang"] = _colorize(sword_base, _CROWN_COLOR)
    icons["slime_king_bulwark"] = _colorize(crop_cell(*_ARMOR_BASE_CELLS["armor"]), _CROWN_COLOR)

    # Accessories: ring/amulet/bracelet shapes, recolored per item instead
    # of each needing its own unique cell.
    ring_base = crop_cell(*_ACCESSORY_RING_CELL)
    amulet_base = crop_cell(*_ACCESSORY_AMULET_CELL)
    bracelet_base = crop_cell(*_ACCESSORY_BRACELET_CELL)
    icons["warriors_charm"] = _colorize(ring_base, _TIER_COLORS["steel"])
    icons["summoners_trinket"] = _colorize(amulet_base, (120, 205, 135))  # slime-green, matches its "faintly glowing" description
    icons["swift_anklet"] = _colorize(bracelet_base, (140, 220, 230))     # a light, breezy cyan for "swift"
    icons["arcane_anklet"] = _colorize(bracelet_base, _TIER_COLORS["arcane"])
    icons["voidstone_amulet"] = _colorize(amulet_base, _TIER_COLORS["voidsteel"])
    # Gem-bar rings: one gold-ring shape, recolored per bar so Topaz /
    # Sapphire / Emerald Bars have a use besides the Arcane Bar recipe.
    icons["topaz_ring"] = _colorize(ring_base, _BAR_COLORS["topaz_bar"])
    icons["sapphire_ring"] = _colorize(ring_base, _BAR_COLORS["sapphire_bar"])
    icons["emerald_ring"] = _colorize(ring_base, _BAR_COLORS["emerald_bar"])
    # Desert body armor sits between wood (brown) and iron; cactus-green
    # on the same chestpiece silhouette as every other body slot.
    icons["cactus_jerkin"] = _colorize(crop_cell(*_ARMOR_BASE_CELLS["armor"]), (80, 145, 60))

    # Biome exclusive-mob drops -- reuse known sheet shapes (slime-gel blob,
    # feather) recolored rather than guessing unused nearby cells. wing_charm
    # is the mosquito_wing craft, same amulet silhouette as other accessories.
    icons["frost_shard"] = _colorize(crop_cell(0, 1), (140, 210, 245))
    icons["mosquito_wing"] = _colorize(crop_cell(17, 10), (90, 170, 80))
    icons["wing_charm"] = _colorize(amulet_base, (110, 190, 70))

    return icons

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


def _colorize(base: pygame.Surface, color: Tuple[int, int, int]) -> pygame.Surface:
    """Recolors a sprite by its own per-pixel luminosity (grayscale
    brightness) rather than `_tinted`'s flat alpha wash -- shifts the whole
    icon to `color` while keeping its real shading/highlights, so one real
    sheet icon shape (see _SHEET_TIER_BASE_CELLS) can stand in for several
    tinted tiers the same way `_build_procedural_icons`'s flat-fill
    silhouettes used to, but with real pixel-art linework instead of a
    vector shape. Pure pygame (get_at/set_at) rather than numpy, since
    numpy isn't a declared project dependency (see requirements.txt) --
    fine at icon-load time, a handful of 32x32 sprites."""
    w, h = base.get_size()
    result = pygame.Surface((w, h), pygame.SRCALPHA)
    cr, cg, cb = color
    for y in range(h):
        for x in range(w):
            r, g, b, a = base.get_at((x, y))
            if a == 0:
                continue
            luminosity = min(1.0, (0.299 * r + 0.587 * g + 0.114 * b) / 255.0 * 1.15)
            result.set_at((x, y), (int(cr * luminosity), int(cg * luminosity), int(cb * luminosity), a))
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
    outside_sheet = pygame.image.load(TILESET_OUTSIDE_PATH).convert_alpha()
    inside_sheet = pygame.image.load(TILESET_INSIDE_PATH).convert_alpha()
    raw_by_id = {
        tile_id: _crop(outside_sheet, col * TILESET_CELL, row * TILESET_CELL, TILESET_CELL, TILESET_CELL)
        for tile_id, (row, col) in _OUTSIDE_TILESET_CELLS.items()
    }
    raw_by_id.update({
        tile_id: _crop(inside_sheet, col * TILESET_CELL, row * TILESET_CELL, TILESET_CELL, TILESET_CELL)
        for tile_id, (row, col) in _INSIDE_TILESET_CELLS.items()
    })
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
    # Coordinates are doubled from their original values (was tuned against
    # a 16px raw tile; dirt_raw is now the tileset's native 32px).
    bench_base = _tinted(dirt_raw, (120, 80, 45), 200)
    bench_base = _with_horizontal_lines(bench_base, (170, 130, 80), [6], width=2)
    bench_base = _with_vertical_lines(bench_base, (70, 45, 25), [4, 26], width=2)
    textures[WORKBENCH_ID] = pygame.transform.scale(bench_base, (TILE_SIZE, TILE_SIZE))

    # Tree trunk/leaves: legacy textures (see tile_registry.py -- these two
    # tile ids are no longer generated, kept only so an old save's leftover
    # tile still renders instead of falling back to a flat swatch).
    trunk_base = _tinted(dirt_raw, (90, 55, 25), 190)
    trunk_base = _with_vertical_lines(trunk_base, (60, 35, 15), [8, 16, 24])
    textures[TREE_TRUNK_ID] = pygame.transform.scale(trunk_base, (TILE_SIZE, TILE_SIZE))

    leaves_base = _tinted(grass_raw, (30, 60, 20), 90)
    textures[TREE_LEAVES_ID] = pygame.transform.scale(leaves_base, (TILE_SIZE, TILE_SIZE))

    # Wood plank: lighter, cleaner tint than raw bark + a single seam line
    # per plank -- reads as "cut lumber" rather than a tree trunk.
    plank_base = _tinted(dirt_raw, (150, 110, 65), 200)
    plank_base = _with_horizontal_lines(plank_base, (110, 75, 40), [16])
    textures[WOOD_PLANK_ID] = pygame.transform.scale(plank_base, (TILE_SIZE, TILE_SIZE))

    crate_sheet = pygame.image.load(CRATE_TEXTURE_PATH).convert_alpha()
    textures[DECOR_CRATE_ID] = pygame.transform.scale(crate_sheet, (TILE_SIZE, TILE_SIZE))

    # Chest (Phase 7 structures loot): Box2 -- same pack as the wooden
    # crate (Box1) but never used until now, a distinct-enough color to
    # read as "different from a crate" at a glance.
    chest_sheet = pygame.image.load(CHEST_TEXTURE_PATH).convert_alpha()
    textures[CHEST_ID] = pygame.transform.scale(chest_sheet, (TILE_SIZE, TILE_SIZE))

    # Personal Chest: Box3, the remaining box in the pack, so it doesn't
    # read as the world-loot Chest (Box2) or the decorative crate (Box1).
    personal_chest_sheet = pygame.image.load(PERSONAL_CHEST_TEXTURE_PATH).convert_alpha()
    textures[PERSONAL_CHEST_ID] = pygame.transform.scale(personal_chest_sheet, (TILE_SIZE, TILE_SIZE))

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
    # other structural tile with no single-cell source (see module
    # docstring). Coordinates doubled, same reason as the Workbench above.
    furnace_base = _tinted(stone_raw, (70, 65, 70), 205)
    pygame.draw.rect(furnace_base, (30, 26, 28), pygame.Rect(8, 18, 16, 12))
    pygame.draw.rect(furnace_base, (235, 130, 40), pygame.Rect(10, 22, 12, 6))
    furnace_base = _with_horizontal_lines(furnace_base, (40, 36, 40), [4], width=1)
    textures[FURNACE_ID] = pygame.transform.scale(furnace_base, (TILE_SIZE, TILE_SIZE))

    # Wood door (closed): plank-tinted dirt + frame, two panels, a knob --
    # no dedicated door art in the pack, same tint-plus-detail as Workbench.
    door_closed = _tinted(dirt_raw, (120, 80, 45), 200)
    pygame.draw.rect(door_closed, (70, 45, 25), pygame.Rect(2, 1, 28, 31), width=2)
    pygame.draw.rect(door_closed, (155, 115, 70), pygame.Rect(6, 5, 20, 10))
    pygame.draw.rect(door_closed, (155, 115, 70), pygame.Rect(6, 17, 20, 11))
    pygame.draw.rect(door_closed, (90, 60, 35), pygame.Rect(6, 5, 20, 10), width=1)
    pygame.draw.rect(door_closed, (90, 60, 35), pygame.Rect(6, 17, 20, 11), width=1)
    pygame.draw.line(door_closed, (90, 60, 35), (6, 16), (25, 16), width=2)
    pygame.draw.circle(door_closed, (200, 170, 80), (24, 18), 2)
    textures[DOOR_CLOSED_ID] = pygame.transform.scale(door_closed, (TILE_SIZE, TILE_SIZE))

    # Open door: the same frame with the panels punched out to a darker
    # interior so the tile reads as a gap rather than a second wood block.
    door_open = door_closed.copy()
    pygame.draw.rect(door_open, (28, 20, 14), pygame.Rect(6, 4, 20, 25))
    pygame.draw.rect(door_open, (70, 45, 25), pygame.Rect(2, 1, 6, 31))
    textures[DOOR_OPEN_ID] = pygame.transform.scale(door_open, (TILE_SIZE, TILE_SIZE))

    # Bed: plank-tinted base + a mattress and pillow (TileDef.color is the
    # old flat maroon swatch -- the mattress reuses that hue so it still
    # reads as "the bed tile" next to wood plank flooring).
    bed_base = _tinted(dirt_raw, (140, 100, 60), 190)
    pygame.draw.rect(bed_base, (70, 45, 25), pygame.Rect(1, 20, 30, 11))
    pygame.draw.rect(bed_base, (180, 60, 70), pygame.Rect(2, 10, 28, 14))
    pygame.draw.rect(bed_base, (210, 90, 95), pygame.Rect(2, 10, 28, 4))
    pygame.draw.rect(bed_base, (230, 220, 210), pygame.Rect(3, 6, 10, 6))
    bed_base = _with_horizontal_lines(bed_base, (90, 60, 35), [22], width=1)
    textures[BED_ID] = pygame.transform.scale(bed_base, (TILE_SIZE, TILE_SIZE))

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


def load_ui_theme() -> Dict[str, object]:
    """The validar-pack reskin's raw art, loaded once. `panel` and `cell`/
    `cell_chosen` are 9-sliceable/scalable frames (see Renderer.
    _draw_nine_slice) -- everything else is drawn at native size and
    scaled as a whole. `hp_bar_fill_track` is the (x, y, w, h) rect within
    `hp_bar_frame`, in the frame's own native pixels, where the proportional
    fill strip belongs -- measured directly from the source art's alpha
    channel (the frame's hollow interior), not guessed."""
    buttons = {}
    for key, (not_pressed, pressed) in _UI_BUTTON_FILES.items():
        buttons[key] = (
            pygame.image.load(os.path.join(_UI_BUTTON_DIR, not_pressed)).convert_alpha(),
            pygame.image.load(os.path.join(_UI_BUTTON_DIR, pressed)).convert_alpha(),
        )
    return {
        "hp_bar_frame": pygame.image.load(HP_BAR_FRAME_PATH).convert_alpha(),
        "hp_bar_fill": pygame.image.load(HP_BAR_FILL_PATH).convert_alpha(),
        "hp_bar_fill_track": (13, 4, 40, 4),
        "panel": pygame.image.load(UI_PANEL_TEXTURE_PATH).convert_alpha(),
        "cell": pygame.image.load(UI_CELL_TEXTURE_PATH).convert_alpha(),
        "cell_chosen": pygame.image.load(UI_CELL_CHOSEN_TEXTURE_PATH).convert_alpha(),
        "buttons": buttons,
    }


def _build_procedural_icons(size: int = 32) -> Dict[str, pygame.Surface]:
    """A hand-drawn vector icon for the one item with neither a matching
    tile/sprite nor a usable match in the user-supplied icon sheet (see
    ITEM_ICON_SHEET_PATH above) -- a simple shape beats an anonymous color
    swatch."""
    icons: Dict[str, pygame.Surface] = {}

    def new_surface():
        return pygame.Surface((size, size), pygame.SRCALPHA)

    # Arrow: a shaft with a triangular head and fletching.
    surf = new_surface()
    pygame.draw.line(surf, (120, 90, 50), (size * 0.15, size * 0.85), (size * 0.75, size * 0.25), width=3)
    pygame.draw.polygon(surf, (150, 150, 158), [
        (size * 0.75, size * 0.25), (size * 0.55, size * 0.35), (size * 0.65, size * 0.15),
    ])
    pygame.draw.line(surf, (200, 60, 60), (size * 0.15, size * 0.85), (size * 0.3, size * 0.65), width=3)
    pygame.draw.line(surf, (200, 60, 60), (size * 0.15, size * 0.85), (size * 0.35, size * 0.8), width=3)
    icons["arrow"] = surf

    return icons


def load_static_item_icons() -> Dict[str, pygame.Surface]:
    icons = {}
    for item_id, (path, frame_size) in _STATIC_ICON_SOURCES.items():
        sheet = pygame.image.load(path).convert_alpha()
        frame = _crop(sheet, 0, 0, frame_size, min(frame_size, sheet.get_height()))
        icons[item_id] = frame
    icons.update(_build_procedural_icons())
    icons.update(_load_sheet_item_icons())
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


def load_background_layers() -> Dict[str, pygame.Surface]:
    return {name: pygame.image.load(path).convert_alpha() for name, path in BACKGROUND_LAYER_PATHS.items()}


TREE_SPRITE_SHEET_PATH = os.path.join("assets", "Tiles", "Trees.png")
TREE_SPRITE_WIDTH = 64   # 2 tiles
TREE_SPRITE_HEIGHT = 96  # 3 tiles


def load_tree_sprites() -> List[pygame.Surface]:
    """The two full-tree sprites TREE_ID renders as (see Renderer._draw_world's
    TREE_ID special case) -- a 128x96 sheet, two 64x96 trees side by side,
    no gap between them."""
    sheet = pygame.image.load(TREE_SPRITE_SHEET_PATH).convert_alpha()
    count = sheet.get_width() // TREE_SPRITE_WIDTH
    return [_crop(sheet, i * TREE_SPRITE_WIDTH, 0, TREE_SPRITE_WIDTH, TREE_SPRITE_HEIGHT) for i in range(count)]


def _horizontal_strip(path: str, frame_w: int, frame_h: int = None) -> List[pygame.Surface]:
    sheet = pygame.image.load(path).convert_alpha()
    frame_h = frame_h or sheet.get_height()
    count = sheet.get_width() // frame_w
    return [_crop(sheet, i * frame_w, 0, frame_w, frame_h) for i in range(count)]


def _grid_row(path: str, cell: int, row: int, count: int) -> List[pygame.Surface]:
    sheet = pygame.image.load(path).convert_alpha()
    return [_crop(sheet, col * cell, row * cell, cell, cell) for col in range(count)]


def _scale_facing(frames: List[pygame.Surface], target_size: int) -> Dict[str, List[pygame.Surface]]:
    scaled = [pygame.transform.scale(frame, (target_size, target_size)) for frame in frames]
    return {
        "right": scaled,
        "left": [pygame.transform.flip(frame, True, False) for frame in scaled],
    }


def _animation_table(states: Dict[str, List[pygame.Surface]], target_size: int) -> Dict[Tuple[str, str], List[pygame.Surface]]:
    table: Dict[Tuple[str, str], List[pygame.Surface]] = {}
    for state, frames in states.items():
        facing = _scale_facing(frames, target_size)
        table[(state, "right")] = facing["right"]
        table[(state, "left")] = facing["left"]
    return table


def load_duskwing_animations(target_size: int) -> Dict[Tuple[str, str], List[pygame.Surface]]:
    """mini bat.png: row 0 cols 0-2 is a real wing flap (col 3 folds the
    wings -- skip it). Row 1 is the diving chase. Bat.png's 48px sheet is
    three near-identical poses so it reads as a frozen sprite."""
    hover = _grid_row(MINI_BAT_PATH, MINI_BAT_CELL, 0, 3)
    dive = _grid_row(MINI_BAT_PATH, MINI_BAT_CELL, 1, 4)
    hit = [_tinted(hover[0], (255, 40, 40), 180)]
    return _animation_table({"idle": hover, "chase": dive, "hit": hit}, target_size)


def load_slime_animations(target_size: int) -> Dict[Tuple[str, str], List[pygame.Surface]]:
    idle = _horizontal_strip(SLIME_IDLE_PATH, SLIME_FRAME)
    walk = _horizontal_strip(SLIME_WALK_PATH, SLIME_FRAME)
    hurt = _horizontal_strip(SLIME_HURT_PATH, SLIME_FRAME)
    hit = [hurt[1]] if len(hurt) > 1 else hurt[:1]
    return _animation_table({"idle": idle, "chase": walk, "hit": hit}, target_size)


def load_scorpion_animations(target_size: int) -> Dict[Tuple[str, str], List[pygame.Surface]]:
    idle = _horizontal_strip(SCORPION_IDLE_PATH, SCORPION_FRAME)
    walk = _horizontal_strip(SCORPION_WALK_PATH, SCORPION_FRAME)
    hit = _horizontal_strip(SCORPION_ATTACK_PATH, SCORPION_FRAME)
    return _animation_table({"idle": idle, "chase": walk, "hit": hit}, target_size)


def load_frost_hopper_animations(target_size: int) -> Dict[Tuple[str, str], List[pygame.Surface]]:
    """Mini_Slime sheets recolored icy -- a Snow hopper, not a second slime
    loader. Tinting after the crop keeps the hop cycle identical without
    sharing load_slime_animations (other agents may also wrap those sheets)."""
    ice = (130, 210, 255)
    idle = [_tinted(frame, ice, 150) for frame in _horizontal_strip(SLIME_IDLE_PATH, SLIME_FRAME)]
    walk = [_tinted(frame, ice, 150) for frame in _horizontal_strip(SLIME_WALK_PATH, SLIME_FRAME)]
    hurt = _horizontal_strip(SLIME_HURT_PATH, SLIME_FRAME)
    hit_src = hurt[1] if len(hurt) > 1 else hurt[0]
    hit = [_tinted(hit_src, ice, 150)]
    return _animation_table({"idle": idle, "chase": walk, "hit": hit}, target_size)


def load_swamp_mosquito_animations(target_size: int) -> Dict[Tuple[str, str], List[pygame.Surface]]:
    """mosquito.png: 48px cells, row 0 cols 0-3 is a wing flap (col 4 empty).
    Row 1 is a death splat, not a chase cycle, so chase reuses the flap and
    hit is a red-tinted idle frame -- same shape as duskwing."""
    flap = _grid_row(MOSQUITO_PATH, MOSQUITO_CELL, 0, 4)
    hover = flap[:3]
    hit = [_tinted(hover[0], (255, 40, 40), 180)]
    return _animation_table({"idle": hover, "chase": flap, "hit": hit}, target_size)


def load_crawler_animations(target_size: int) -> Dict[Tuple[str, str], List[pygame.Surface]]:
    """Eyeball.png: 288x96, 48px cells, 6 columns x 2 rows. Row 0 is a
    look-around idle (all 6). Row 1 cols 0-3 is an angry chase; cols 4-5
    are a death splat, skipped. Hit is a red-tinted idle frame -- same
    shape as duskwing."""
    idle = _grid_row(EYEBALL_PATH, EYEBALL_CELL, 0, 6)
    chase = _grid_row(EYEBALL_PATH, EYEBALL_CELL, 1, 4)
    hit = [_tinted(idle[0], (255, 40, 40), 180)]
    return _animation_table({"idle": idle, "chase": chase, "hit": hit}, target_size)


def load_enemy_animations() -> Dict[str, Dict[Tuple[str, str], List[pygame.Surface]]]:
    """Per-enemy-id tables from assets/Enemies."""
    return {
        "duskwing": load_duskwing_animations(DUSKWING_SPRITE_SIZE),
        "slime": load_slime_animations(SLIME_SPRITE_SIZE),
        "slime_king": load_slime_animations(SLIME_KING_SPRITE_SIZE),
        "scorpion": load_scorpion_animations(SCORPION_SPRITE_SIZE),
        "frost_hopper": load_frost_hopper_animations(FROST_HOPPER_SPRITE_SIZE),
        "swamp_mosquito": load_swamp_mosquito_animations(SWAMP_MOSQUITO_SPRITE_SIZE),
        "crawler": load_crawler_animations(CRAWLER_SPRITE_SIZE),
    }


def _sheet_with_black_as_transparent(path: str) -> pygame.Surface:
    """flying-head.png is an 8-bit sheet on solid black, no alpha channel.
    Punch exact black out so the sprite's silhouette isn't a black box."""
    sheet = pygame.image.load(path).convert()
    sheet.set_colorkey((0, 0, 0))
    return sheet.convert_alpha()


def load_iron_guardian_animations(target_size: int) -> Dict[Tuple[str, str], List[pygame.Surface]]:
    """flying-head.png: row 0 is a slow flap (idle), row 2 a faster flap
    (chase) -- no dedicated Iron Guardian art exists, and this sheet was
    otherwise sitting unused (an older Duskwing pass moved to Bat.png
    instead), so the Summoner's second-tier minion reuses it."""
    sheet = _sheet_with_black_as_transparent(FLYING_HEAD_PATH)
    cell = FLYING_HEAD_CELL

    def row(index: int, count: int) -> List[pygame.Surface]:
        return [_crop(sheet, col * cell, index * cell, cell, cell) for col in range(count)]

    idle = row(0, 6)
    chase = row(2, 9)
    return _animation_table({"idle": idle, "chase": chase}, target_size)


def _recolor_animation_table(
    table: Dict[Tuple[str, str], List[pygame.Surface]],
    color: Tuple[int, int, int],
) -> Dict[Tuple[str, str], List[pygame.Surface]]:
    """One flying-head table, recolored per summon so Twig/Steel/Arcane/
    Void aren't a second flat ellipse -- `_colorize` keeps the flap
    shading the way item-tier icons already do."""
    return {key: [_colorize(frame, color) for frame in frames] for key, frames in table.items()}


def load_summon_animations() -> Dict[str, Dict[Tuple[str, str], List[pygame.Surface]]]:
    """Per-summon-id tables, same shape as load_enemy_animations. Iron
    Guardian keeps the natural flying-head colors; every other summon is
    that same flap recolored to its own hue."""
    iron = load_iron_guardian_animations(IRON_GUARDIAN_SPRITE_SIZE)
    return {
        "iron_guardian": iron,
        "twig_sprite": _recolor_animation_table(iron, (90, 180, 70)),       # twig green
        "steel_colossus": _recolor_animation_table(iron, (110, 125, 150)),  # steel blue-gray
        "arcane_familiar": _recolor_animation_table(iron, (150, 100, 210)), # arcane purple
        "void_wraith": _recolor_animation_table(iron, (70, 25, 110)),       # void dark purple
    }
