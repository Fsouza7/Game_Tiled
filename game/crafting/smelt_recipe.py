"""Smelting recipe schema: ore + fuel -> bar, over time. Separate from
RecipeDef (crafting/recipe.py) because a smelt is a *started-then-later-
collected* transaction (see furnace_system.py), not an instant one."""
from dataclasses import dataclass


@dataclass(frozen=True)
class SmeltRecipeDef:
    id: str
    name: str
    ore_item_id: str
    ore_quantity: int
    fuel_item_id: str
    fuel_quantity: int
    bar_item_id: str
    bar_quantity: int
    smelt_time_s: float

    # Duck-type as a RecipeDef-alike so the crafting screen's generic
    # ingredient/discovery/station-badge code (recipe.py's shape) works on
    # smelt recipes without a parallel implementation -- the only place
    # that treats them differently is *what a click does* (start a timed
    # job via furnace_system.start_smelt, not an instant craft).
    @property
    def ingredients(self):
        return ((self.ore_item_id, self.ore_quantity), (self.fuel_item_id, self.fuel_quantity))

    @property
    def result_item_id(self) -> str:
        return self.bar_item_id

    @property
    def result_quantity(self) -> int:
        return self.bar_quantity

    @property
    def station_tile_id(self) -> int:
        from game.world.tile_registry import FURNACE_ID
        return FURNACE_ID
