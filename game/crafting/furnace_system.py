"""Furnace mechanics: ore + fuel -> a timed smelt job -> a collected bar.

Unlike crafting_system.craft() (instant), starting a smelt consumes ore/fuel
immediately but the bar isn't granted until `smelt_time_s` has passed --
"put ore in to burn", not "click for an instant bar". Jobs are keyed by the
specific furnace tile they were started at (`nearest_station_tile`), so
multiple placed furnaces can smelt in parallel. Kept independent of
GameApp/Player so it's unit-testable with just an Inventory and a World.

Two ways to start a smelt:
  - start_smelt() -- instant, one-shot: consumes exactly one recipe's worth
    of ore/fuel straight out of the player's inventory and begins a job
    right away. Still here for callers that want a single smelt with no
    setup.
  - The furnace queue (deposit_fuel/deposit_ore + update()'s auto-restart
    below) -- the Furnace screen's actual interaction: the player deposits
    a *stack* of ore and fuel into the furnace's own 2-slot input hopper
    (see FurnaceManager.input_at), and update() keeps consuming one
    recipe's worth at a time and starting the next job automatically as
    long as both slots have enough, so "insert ore + coal, walk away, come
    back to bars" works without babysitting each individual smelt.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from game.crafting.smelt_recipe import SmeltRecipeDef
from game.crafting import smelt_registry
from game.inventory.inventory import Inventory, transfer_stack
from game.items import item_registry
from game.settings import TILE_SIZE, STATION_SEARCH_RADIUS_TILES
from game.world.world import World
from game.world import tile_registry

# The furnace's own input hopper: 2 slots, fuel then ore (see
# FURNACE_FUEL_SLOT/FURNACE_ORE_SLOT below) -- not a generic-size Inventory,
# always exactly these two so index-based access below stays meaningful.
FURNACE_FUEL_SLOT = 0
FURNACE_ORE_SLOT = 1
FURNACE_INPUT_SLOTS = 2


def nearest_station_tile(world: World, center_x_px: float, center_y_px: float, station_tile_id: int) -> Optional[Tuple[int, int]]:
    """Like crafting_system.is_near_station, but returns the closest
    matching tile's position instead of just whether one exists -- the
    furnace needs an actual tile identity to key jobs by."""
    center_tx = int(center_x_px // TILE_SIZE)
    center_ty = int(center_y_px // TILE_SIZE)
    radius = STATION_SEARCH_RADIUS_TILES
    best_pos = None
    best_dist = None
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if world.get_tile(center_tx + dx, center_ty + dy) != station_tile_id:
                continue
            dist = dx * dx + dy * dy
            if best_dist is None or dist < best_dist:
                best_pos = (center_tx + dx, center_ty + dy)
                best_dist = dist
    return best_pos


@dataclass
class FurnaceJob:
    bar_item_id: str
    quantity: int
    remaining_s: float
    total_s: float


class FurnaceManager:
    def __init__(self):
        self.jobs: Dict[Tuple[int, int], FurnaceJob] = {}
        # Each furnace's own 2-slot input hopper (FURNACE_FUEL_SLOT/
        # FURNACE_ORE_SLOT) -- created lazily the first time a furnace at
        # that position is deposited into (see input_at), so an unused
        # furnace never needs an entry here.
        self.inputs: Dict[Tuple[int, int], Inventory] = {}

    def job_at(self, pos: Tuple[int, int]) -> Optional[FurnaceJob]:
        return self.jobs.get(pos)

    def nearby_job(self, world: World, center_x_px: float, center_y_px: float) -> Optional[FurnaceJob]:
        pos = nearest_station_tile(world, center_x_px, center_y_px, tile_registry.FURNACE_ID)
        return None if pos is None else self.jobs.get(pos)

    def input_at(self, pos: Tuple[int, int]) -> Inventory:
        """Gets (creating if needed) the furnace queue's input hopper at
        `pos`. Always exactly FURNACE_INPUT_SLOTS slots: index
        FURNACE_FUEL_SLOT holds fuel, FURNACE_ORE_SLOT holds ore."""
        storage = self.inputs.get(pos)
        if storage is None:
            storage = Inventory(size=FURNACE_INPUT_SLOTS)
            self.inputs[pos] = storage
        return storage

    def nearby_input(self, world: World, center_x_px: float, center_y_px: float) -> Optional[Inventory]:
        """Like input_at, but resolved from player position the way the
        Furnace screen opens -- None if no furnace is actually in range
        (never silently creates a hopper for a furnace that isn't there)."""
        pos = nearest_station_tile(world, center_x_px, center_y_px, tile_registry.FURNACE_ID)
        return None if pos is None else self.input_at(pos)

    def _deposit_to_slot(self, pos: Tuple[int, int], source: Inventory, source_index: int, slot_index: int, valid_item_ids: set) -> int:
        """Moves as much as fits of source.slots[source_index] into the
        furnace input hopper's `slot_index`, provided the item is one this
        slot accepts (valid_item_ids) and the slot isn't already holding a
        different item. Returns how many actually moved."""
        if source_index < 0 or source_index >= len(source.slots):
            return 0
        source_slot = source.slots[source_index]
        if source_slot.is_empty or source_slot.item_id not in valid_item_ids:
            return 0

        dest_slot = self.input_at(pos).slots[slot_index]
        if not dest_slot.is_empty and dest_slot.item_id != source_slot.item_id:
            return 0  # slot is holding a different fuel/ore -- withdraw it first

        max_stack = item_registry.get(source_slot.item_id).max_stack
        space = max_stack - dest_slot.quantity if not dest_slot.is_empty else max_stack
        moved = min(space, source_slot.quantity)
        if moved <= 0:
            return 0

        if dest_slot.is_empty:
            dest_slot.item_id = source_slot.item_id
        dest_slot.quantity += moved
        source_slot.quantity -= moved
        if source_slot.quantity <= 0:
            source_slot.item_id = None
            source_slot.quantity = 0
        return moved

    def deposit_fuel(self, pos: Tuple[int, int], source: Inventory, source_index: int) -> int:
        return self._deposit_to_slot(pos, source, source_index, FURNACE_FUEL_SLOT, smelt_registry.all_fuel_item_ids())

    def deposit_ore(self, pos: Tuple[int, int], source: Inventory, source_index: int) -> int:
        return self._deposit_to_slot(pos, source, source_index, FURNACE_ORE_SLOT, smelt_registry.all_ore_item_ids())

    def withdraw_fuel(self, pos: Tuple[int, int], dest: Inventory) -> int:
        return transfer_stack(self.input_at(pos), FURNACE_FUEL_SLOT, dest)

    def withdraw_ore(self, pos: Tuple[int, int], dest: Inventory) -> int:
        return transfer_stack(self.input_at(pos), FURNACE_ORE_SLOT, dest)

    def start_smelt(self, recipe: SmeltRecipeDef, inventory: Inventory, world: World, player_center_x: float, player_center_y: float) -> bool:
        pos = nearest_station_tile(world, player_center_x, player_center_y, tile_registry.FURNACE_ID)
        if pos is None or pos in self.jobs:
            return False  # no furnace nearby, or it's already smelting something
        if inventory.count_item(recipe.ore_item_id) < recipe.ore_quantity:
            return False
        if inventory.count_item(recipe.fuel_item_id) < recipe.fuel_quantity:
            return False

        inventory.remove_item(recipe.ore_item_id, recipe.ore_quantity)
        inventory.remove_item(recipe.fuel_item_id, recipe.fuel_quantity)
        self.jobs[pos] = FurnaceJob(
            bar_item_id=recipe.bar_item_id, quantity=recipe.bar_quantity,
            remaining_s=recipe.smelt_time_s, total_s=recipe.smelt_time_s,
        )
        return True

    def update(self, dt: float) -> List[Tuple[str, int]]:
        """Advances every active job; returns (item_id, quantity) for each
        one that finished this call -- the caller (GameApp) grants those to
        the player's inventory, since FurnaceManager has no Player
        reference of its own.

        After clearing finished jobs, tries to auto-start the next one for
        every furnace that has an input hopper (self.inputs) and isn't
        already busy -- this is what makes depositing a stack of ore/fuel
        into the Furnace screen a real queue instead of a single smelt:
        as long as both slots hold enough for another batch, the furnace
        just keeps going on its own."""
        completed = []
        done_positions = []
        for pos, job in self.jobs.items():
            job.remaining_s -= dt
            if job.remaining_s <= 0.0:
                completed.append((job.bar_item_id, job.quantity))
                done_positions.append(pos)
        for pos in done_positions:
            del self.jobs[pos]

        for pos in self.inputs:
            if pos not in self.jobs:
                self._try_autostart(pos)

        return completed

    def _try_autostart(self, pos: Tuple[int, int]) -> bool:
        storage = self.inputs[pos]
        fuel_slot = storage.slots[FURNACE_FUEL_SLOT]
        ore_slot = storage.slots[FURNACE_ORE_SLOT]
        if fuel_slot.is_empty or ore_slot.is_empty:
            return False

        recipe = smelt_registry.recipe_for_ore(ore_slot.item_id)
        if recipe is None or fuel_slot.item_id != recipe.fuel_item_id:
            return False
        if ore_slot.quantity < recipe.ore_quantity or fuel_slot.quantity < recipe.fuel_quantity:
            return False

        ore_slot.quantity -= recipe.ore_quantity
        if ore_slot.quantity <= 0:
            ore_slot.item_id = None
            ore_slot.quantity = 0
        fuel_slot.quantity -= recipe.fuel_quantity
        if fuel_slot.quantity <= 0:
            fuel_slot.item_id = None
            fuel_slot.quantity = 0

        self.jobs[pos] = FurnaceJob(
            bar_item_id=recipe.bar_item_id, quantity=recipe.bar_quantity,
            remaining_s=recipe.smelt_time_s, total_s=recipe.smelt_time_s,
        )
        return True
