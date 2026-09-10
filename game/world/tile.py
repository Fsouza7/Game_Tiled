"""Tile definitions: the data schema shared by every block type in the world."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class TileCategory(Enum):
    NATURAL = "natural"
    ORE = "ore"
    STRUCTURAL = "structural"


@dataclass(frozen=True)
class TileDef:
    id: int
    name: str
    category: TileCategory
    color: Tuple[int, int, int]  # placeholder texture until real art exists
    solid: bool
    resistance: float  # "hit points" a tool must overcome to break the tile
    required_tool: Optional[str]  # e.g. "pickaxe"; None = breakable by hand
    drop_item_id: Optional[str]  # item id granted on break; None = no drop
    can_place: bool
    can_break: bool
    light_emit: int = 0  # 0-15, reserved for the future lighting system
    light_receive: bool = True
    transparent: bool = False
    # A tile that drops one random item from a pool instead of one fixed
    # item (e.g. a berry bush yielding a random fruit) -- takes priority
    # over drop_item_id when set. See World.try_break_tile.
    drop_pool: Optional[Tuple[str, ...]] = None
    # How many of drop_item_id/drop_pool's pick a single break grants (on
    # top of Player.mining_drop_quantity's usual +1 fortune bonus) -- 1 for
    # every ordinary tile; the Tree tile sets this higher since it now
    # represents a whole tree felled in one break, not one of several
    # stacked trunk/leaf tiles each dropping separately (see World.
    # try_break_tile and Tree's docstring in tile_registry.py).
    break_quantity: int = 1
    # Interactive-tile hooks, both opt-in (0 = inert), handled in
    # Player.physics_step: contact_damage hurts the player on overlap
    # (a placeable hazard, e.g. Spikes); bounce_velocity launches the
    # player upward instead of coming to rest on landing (e.g. Trampoline).
    contact_damage: float = 0.0
    bounce_velocity: float = 0.0
    # Multiplies the player's horizontal move speed while standing on this
    # tile (Sand/Mud slow you down, Ice speeds you up); 1.0 = no effect.
    # See Player._ground_speed_multiplier.
    speed_multiplier: float = 1.0
    # Continuous upward push (px/tick) applied while the player is within
    # FAN_RANGE_TILES directly above this tile (a Fan); 0 = no effect.
    # See Player._fan_updraft.
    updraft_velocity: float = 0.0
