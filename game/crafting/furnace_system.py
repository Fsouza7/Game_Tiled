"""Furnace mechanics: ore + fuel -> a timed smelt job -> a collected bar.

Unlike crafting_system.craft() (instant), starting a smelt consumes ore/fuel
immediately but the bar isn't granted until `smelt_time_s` has passed --
"put ore in to burn", not "click for an instant bar". Jobs are keyed by the
specific furnace tile they were started at (`nearest_station_tile`), so
multiple placed furnaces can smelt in parallel. Kept independent of
GameApp/Player so it's unit-testable with just an Inventory and a World.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from game.crafting.smelt_recipe import SmeltRecipeDef
from game.inventory.inventory import Inventory
from game.settings import TILE_SIZE, STATION_SEARCH_RADIUS_TILES
from game.world.world import World
from game.world import tile_registry


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

    def job_at(self, pos: Tuple[int, int]) -> Optional[FurnaceJob]:
        return self.jobs.get(pos)

    def nearby_job(self, world: World, center_x_px: float, center_y_px: float) -> Optional[FurnaceJob]:
        pos = nearest_station_tile(world, center_x_px, center_y_px, tile_registry.FURNACE_ID)
        return None if pos is None else self.jobs.get(pos)

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
        reference of its own."""
        completed = []
        done_positions = []
        for pos, job in self.jobs.items():
            job.remaining_s -= dt
            if job.remaining_s <= 0.0:
                completed.append((job.bar_item_id, job.quantity))
                done_positions.append(pos)
        for pos in done_positions:
            del self.jobs[pos]
        return completed
