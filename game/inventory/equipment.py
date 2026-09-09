"""Armor equipment slots: the RPG-style "paper doll" separate from the
hotbar. Equipping moves the item out of the inventory into a named slot
(one per body part); unequipping puts it back.
"""
from typing import Dict, Optional

from game.inventory.inventory import Inventory
from game.items import item_registry

SLOTS = ("head", "body", "legs", "boots", "accessory")


class Equipment:
    def __init__(self):
        self.slots: Dict[str, Optional[str]] = {slot: None for slot in SLOTS}

    def get(self, slot: str) -> Optional[str]:
        return self.slots.get(slot)

    def total_defense(self) -> float:
        defense = 0.0
        for item_id in self.slots.values():
            if item_id is not None:
                defense += item_registry.get(item_id).defense
        return defense

    def total_light_emit(self) -> int:
        """Brightest equipped item's light_emit (0-15). Worn light sources
        don't stack -- two glowing pieces still count as one lamp."""
        emit = 0
        for item_id in self.slots.values():
            if item_id is not None:
                emit = max(emit, item_registry.get(item_id).light_emit)
        return emit
        """Brightest equipped item's light_emit (0-15). Worn light sources
        don't stack -- two glowing pieces still count as one lamp."""
        emit = 0
        for item_id in self.slots.values():
            if item_id is not None:
                emit = max(emit, item_registry.get(item_id).light_emit)
        return emit

    def equip_from_inventory(self, inventory: Inventory, item_id: str) -> bool:
        """Moves one `item_id` from `inventory` into its equipment slot.
        Returns False (no change) if the item isn't armor, the inventory
        doesn't actually have one, or the slot is already occupied."""
        item_def = item_registry.get(item_id)
        slot = item_def.equip_slot
        if slot is None or slot not in self.slots:
            return False
        if self.slots[slot] is not None:
            return False
        if inventory.count_item(item_id) <= 0:
            return False

        inventory.remove_item(item_id, 1)
        self.slots[slot] = item_id
        return True

    def unequip_to_inventory(self, inventory: Inventory, slot: str) -> bool:
        """Moves the item in `slot` back into `inventory`. Returns False
        (no change) if the slot is empty or the inventory has no room."""
        item_id = self.slots.get(slot)
        if item_id is None:
            return False
        leftover = inventory.add_item(item_id, 1)
        if leftover > 0:
            inventory.remove_item(item_id, 1 - leftover)  # undo partial add
            return False
        self.slots[slot] = None
        return True
