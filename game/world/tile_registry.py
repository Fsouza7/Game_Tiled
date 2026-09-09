"""Central, data-driven table of every tile in the game.

Adding a new tile means adding one entry here -- no other file needs to
change to make a new tile exist in the world (see README "Como criar novos
tiles").
"""
from typing import Dict

from game.world.tile import TileDef, TileCategory
from game.settings import (
    SPIKES_CONTACT_DAMAGE, TRAMPOLINE_BOUNCE_VELOCITY,
    TRAP_SAND_SPEED_MULTIPLIER, TRAP_MUD_SPEED_MULTIPLIER, TRAP_ICE_SPEED_MULTIPLIER,
    FAN_UPDRAFT_VELOCITY, FIRE_CONTACT_DAMAGE, ARROW_TRAP_CONTACT_DAMAGE,
)

AIR_ID = 0
GRASS_ID = 1
DIRT_ID = 2
STONE_ID = 3
COAL_ORE_ID = 4
IRON_ORE_ID = 5
BEDROCK_ID = 6
DECOR_CRATE_ID = 7
WORKBENCH_ID = 8
TREE_TRUNK_ID = 9
TREE_LEAVES_ID = 10
WOOD_PLANK_ID = 11
TORCH_ID = 12
SAND_ID = 13
SANDSTONE_ID = 14
SNOW_BLOCK_ID = 15
FROZEN_DIRT_ID = 16
JUNGLE_GRASS_ID = 17
MUD_ID = 18
CACTUS_ID = 19
DESERT_STONE_ID = 20
SNOW_STONE_ID = 21
JUNGLE_STONE_ID = 22
TOPAZ_ORE_ID = 23
SAPPHIRE_ORE_ID = 24
EMERALD_ORE_ID = 25
BUSH_ID = 26
SPIKES_ID = 27
TRAMPOLINE_ID = 28
FAN_ID = 29
TRAP_SAND_ID = 30
TRAP_MUD_ID = 31
TRAP_ICE_ID = 32
CRUMBLE_PLATFORM_ID = 33
CHECKPOINT_ID = 34
FURNACE_ID = 35
FIRE_ID = 36
ARROW_TRAP_ID = 37
CHEST_ID = 38

_TILES: Dict[int, TileDef] = {}


def _register(tile: TileDef) -> None:
    if tile.id in _TILES:
        raise ValueError(f"Duplicate tile id {tile.id} ({tile.name})")
    _TILES[tile.id] = tile


_register(TileDef(
    id=AIR_ID, name="Air", category=TileCategory.NATURAL,
    color=(0, 0, 0), solid=False, resistance=0.0, required_tool=None,
    drop_item_id=None, can_place=False, can_break=False,
    transparent=True, light_receive=True,
))

_register(TileDef(
    id=GRASS_ID, name="Grass Block", category=TileCategory.NATURAL,
    color=(86, 158, 58), solid=True, resistance=1.0, required_tool=None,
    drop_item_id="dirt_block", can_place=True, can_break=True,
))

_register(TileDef(
    id=DIRT_ID, name="Dirt", category=TileCategory.NATURAL,
    color=(118, 85, 58), solid=True, resistance=1.0, required_tool=None,
    drop_item_id="dirt_block", can_place=True, can_break=True,
))

_register(TileDef(
    id=STONE_ID, name="Stone", category=TileCategory.NATURAL,
    color=(120, 120, 128), solid=True, resistance=2.5, required_tool="pickaxe",
    drop_item_id="stone_block", can_place=True, can_break=True,
))

_register(TileDef(
    id=COAL_ORE_ID, name="Coal Ore", category=TileCategory.ORE,
    color=(58, 58, 64), solid=True, resistance=3.0, required_tool="pickaxe",
    drop_item_id="coal", can_place=False, can_break=True,
))

_register(TileDef(
    id=IRON_ORE_ID, name="Iron Ore", category=TileCategory.ORE,
    color=(196, 156, 110), solid=True, resistance=3.5, required_tool="pickaxe",
    drop_item_id="iron_ore", can_place=False, can_break=True,
))

_register(TileDef(
    id=BEDROCK_ID, name="Bedrock", category=TileCategory.STRUCTURAL,
    color=(30, 30, 34), solid=True, resistance=0.0, required_tool=None,
    drop_item_id=None, can_place=False, can_break=False,
))

_register(TileDef(
    id=DECOR_CRATE_ID, name="Wooden Crate", category=TileCategory.STRUCTURAL,
    color=(150, 100, 60), solid=True, resistance=1.0, required_tool=None,
    drop_item_id="wooden_crate", can_place=True, can_break=True,
))

_register(TileDef(
    id=WORKBENCH_ID, name="Workbench", category=TileCategory.STRUCTURAL,
    color=(120, 80, 45), solid=True, resistance=1.0, required_tool=None,
    drop_item_id="workbench", can_place=True, can_break=True,
))

_register(TileDef(
    id=TREE_TRUNK_ID, name="Tree Trunk", category=TileCategory.NATURAL,
    color=(101, 67, 33), solid=True, resistance=1.2, required_tool=None,
    drop_item_id="wood", can_place=False, can_break=True,
))

_register(TileDef(
    id=TREE_LEAVES_ID, name="Tree Leaves", category=TileCategory.NATURAL,
    color=(72, 130, 48), solid=True, resistance=0.6, required_tool=None,
    drop_item_id="wood", can_place=False, can_break=True,
))

_register(TileDef(
    id=WOOD_PLANK_ID, name="Wood Plank", category=TileCategory.STRUCTURAL,
    color=(176, 132, 80), solid=True, resistance=1.0, required_tool=None,
    drop_item_id="wood_plank_block", can_place=True, can_break=True,
))

_register(TileDef(
    id=TORCH_ID, name="Torch", category=TileCategory.STRUCTURAL,
    color=(230, 170, 60), solid=False, resistance=0.3, required_tool=None,
    drop_item_id="torch", can_place=True, can_break=True,
    light_emit=14, transparent=True,
))

# --- Biome ground tiles (see game/world/biome_registry.py) ---

_register(TileDef(
    id=SAND_ID, name="Sand", category=TileCategory.NATURAL,
    color=(230, 200, 140), solid=True, resistance=0.8, required_tool=None,
    drop_item_id="sand_block", can_place=True, can_break=True,
))

_register(TileDef(
    id=SANDSTONE_ID, name="Sandstone", category=TileCategory.NATURAL,
    color=(210, 180, 130), solid=True, resistance=1.0, required_tool=None,
    drop_item_id="sandstone_block", can_place=True, can_break=True,
))

_register(TileDef(
    id=SNOW_BLOCK_ID, name="Snow", category=TileCategory.NATURAL,
    color=(235, 240, 250), solid=True, resistance=0.8, required_tool=None,
    drop_item_id="snow_block", can_place=True, can_break=True,
))

_register(TileDef(
    id=FROZEN_DIRT_ID, name="Frozen Dirt", category=TileCategory.NATURAL,
    color=(170, 190, 205), solid=True, resistance=1.0, required_tool=None,
    drop_item_id="frozen_dirt_block", can_place=True, can_break=True,
))

_register(TileDef(
    id=JUNGLE_GRASS_ID, name="Jungle Grass", category=TileCategory.NATURAL,
    color=(40, 120, 40), solid=True, resistance=1.0, required_tool=None,
    drop_item_id="jungle_grass_block", can_place=True, can_break=True,
))

_register(TileDef(
    id=MUD_ID, name="Mud", category=TileCategory.NATURAL,
    color=(70, 55, 35), solid=True, resistance=1.0, required_tool=None,
    drop_item_id="mud_block", can_place=True, can_break=True,
))

_register(TileDef(
    id=CACTUS_ID, name="Cactus", category=TileCategory.NATURAL,
    color=(60, 140, 70), solid=True, resistance=0.7, required_tool=None,
    drop_item_id="cactus_fiber", can_place=False, can_break=True,
))

# --- Biome-specific underground (see biome_registry.py underground_tile_id
# / exclusive_ore_tile_id) ---

_register(TileDef(
    id=DESERT_STONE_ID, name="Desert Stone", category=TileCategory.NATURAL,
    color=(150, 125, 90), solid=True, resistance=2.5, required_tool="pickaxe",
    drop_item_id="desert_stone_block", can_place=True, can_break=True,
))

_register(TileDef(
    id=SNOW_STONE_ID, name="Permafrost Stone", category=TileCategory.NATURAL,
    color=(140, 155, 168), solid=True, resistance=2.5, required_tool="pickaxe",
    drop_item_id="snow_stone_block", can_place=True, can_break=True,
))

_register(TileDef(
    id=JUNGLE_STONE_ID, name="Jungle Stone", category=TileCategory.NATURAL,
    color=(85, 110, 75), solid=True, resistance=2.5, required_tool="pickaxe",
    drop_item_id="jungle_stone_block", can_place=True, can_break=True,
))

_register(TileDef(
    id=TOPAZ_ORE_ID, name="Topaz Ore", category=TileCategory.ORE,
    color=(220, 180, 60), solid=True, resistance=3.5, required_tool="pickaxe",
    drop_item_id="topaz", can_place=False, can_break=True,
))

_register(TileDef(
    id=SAPPHIRE_ORE_ID, name="Sapphire Ore", category=TileCategory.ORE,
    color=(60, 110, 210), solid=True, resistance=3.5, required_tool="pickaxe",
    drop_item_id="sapphire", can_place=False, can_break=True,
))

_register(TileDef(
    id=EMERALD_ORE_ID, name="Emerald Ore", category=TileCategory.ORE,
    color=(50, 180, 110), solid=True, resistance=3.5, required_tool="pickaxe",
    drop_item_id="emerald", can_place=False, can_break=True,
))

# --- Berry bush: a rare surface spawn (see world_generator.py
# _place_forest_decoration) that drops one random fruit -- natural-spawn
# only, like the tree/cactus, not placeable by the player. ---

_register(TileDef(
    id=BUSH_ID, name="Berry Bush", category=TileCategory.NATURAL,
    color=(60, 120, 55), solid=True, resistance=0.5, required_tool=None,
    drop_item_id=None, can_place=False, can_break=True,
    drop_pool=("apple", "banana", "cherries", "kiwi", "melon", "orange", "pineapple", "strawberry"),
))

# --- Trampoline: the one placeable, craftable "trap"-sheet tile -- it's a
# bounce pad, not a hazard, so it stays player-built (see item_registry.py). ---

_register(TileDef(
    id=TRAMPOLINE_ID, name="Trampoline", category=TileCategory.STRUCTURAL,
    color=(90, 190, 210), solid=True, resistance=1.0, required_tool=None,
    drop_item_id="trampoline", can_place=True, can_break=True,
    bounce_velocity=TRAMPOLINE_BOUNCE_VELOCITY,
))

# --- Environmental hazards (see TileDef.contact_damage / speed_multiplier /
# updraft_velocity, handled in Player.physics_step and combat_system.py).
# None of these are player-craftable or placeable -- they're generated by
# world_generator.py (see "_place_cave_hazard"/"_place_fan_shaft"/
# "_maybe_surface_trap") the same deterministic way as ore or trees, and
# the player just finds them while exploring. Breaking Falling Platform's
# crumbled state aside, none can be mined or relocated either -- a found
# trap stays exactly where it was generated, like Saw/Rock Head/Spike Head. ---

_register(TileDef(
    id=SPIKES_ID, name="Spikes", category=TileCategory.STRUCTURAL,
    color=(150, 150, 158), solid=False, resistance=1.0, required_tool=None,
    drop_item_id=None, can_place=False, can_break=False,
    contact_damage=SPIKES_CONTACT_DAMAGE,
))

_register(TileDef(
    id=FAN_ID, name="Fan", category=TileCategory.STRUCTURAL,
    color=(200, 200, 210), solid=False, resistance=1.0, required_tool=None,
    drop_item_id=None, can_place=False, can_break=False,
    updraft_velocity=FAN_UPDRAFT_VELOCITY,
))

_register(TileDef(
    id=TRAP_SAND_ID, name="Loose Sand", category=TileCategory.STRUCTURAL,
    color=(230, 200, 140), solid=True, resistance=0.8, required_tool=None,
    drop_item_id=None, can_place=False, can_break=False,
    speed_multiplier=TRAP_SAND_SPEED_MULTIPLIER,
))

_register(TileDef(
    id=TRAP_MUD_ID, name="Sticky Mud", category=TileCategory.STRUCTURAL,
    color=(75, 58, 38), solid=True, resistance=0.8, required_tool=None,
    drop_item_id=None, can_place=False, can_break=False,
    speed_multiplier=TRAP_MUD_SPEED_MULTIPLIER,
))

_register(TileDef(
    id=TRAP_ICE_ID, name="Slick Ice", category=TileCategory.STRUCTURAL,
    color=(190, 225, 240), solid=True, resistance=0.8, required_tool=None,
    drop_item_id=None, can_place=False, can_break=False,
    speed_multiplier=TRAP_ICE_SPEED_MULTIPLIER,
))

_register(TileDef(
    id=CRUMBLE_PLATFORM_ID, name="Falling Platform", category=TileCategory.STRUCTURAL,
    color=(150, 130, 100), solid=True, resistance=1.0, required_tool=None,
    drop_item_id=None, can_place=False, can_break=False,
))

_register(TileDef(
    id=FIRE_ID, name="Fire", category=TileCategory.STRUCTURAL,
    color=(220, 110, 50), solid=False, resistance=1.0, required_tool=None,
    drop_item_id=None, can_place=False, can_break=False,
    contact_damage=FIRE_CONTACT_DAMAGE, light_emit=10, transparent=True,
))

_register(TileDef(
    id=ARROW_TRAP_ID, name="Arrow Trap", category=TileCategory.STRUCTURAL,
    color=(150, 130, 90), solid=False, resistance=1.0, required_tool=None,
    drop_item_id=None, can_place=False, can_break=False,
    contact_damage=ARROW_TRAP_CONTACT_DAMAGE,
))

# --- Checkpoint and Furnace: real player-built stations, unaffected by the
# hazard changes above. ---

_register(TileDef(
    id=CHECKPOINT_ID, name="Checkpoint", category=TileCategory.STRUCTURAL,
    color=(210, 190, 90), solid=False, resistance=1.0, required_tool=None,
    drop_item_id="checkpoint", can_place=True, can_break=True,
))

_register(TileDef(
    id=FURNACE_ID, name="Furnace", category=TileCategory.STRUCTURAL,
    color=(90, 85, 90), solid=True, resistance=1.5, required_tool=None,
    drop_item_id="furnace", can_place=True, can_break=True,
))

# --- Chest: a lootable tile found inside procedurally generated structures
# (Phase 7, see game/world/structures.py) -- like the hazards above, it's
# not player-craftable/placeable, only found while exploring. Reuses the
# existing drop_pool mechanism (Bush's "one of several possible drops")
# for its loot instead of a whole new loot-table system. ---

_register(TileDef(
    id=CHEST_ID, name="Chest", category=TileCategory.STRUCTURAL,
    color=(140, 95, 45), solid=True, resistance=1.2, required_tool=None,
    drop_item_id=None, can_place=False, can_break=True,
    drop_pool=("iron_bar", "topaz", "sapphire", "emerald", "iron_pickaxe", "wood_sword", "wood_helmet"),
))


def get(tile_id: int) -> TileDef:
    return _TILES[tile_id]


def all_tiles() -> Dict[int, TileDef]:
    return dict(_TILES)
