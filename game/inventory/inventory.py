"""Slot-based inventory with stacking and a hotbar selection."""
from dataclasses import dataclass
from typing import List, Optional

from game.items import item_registry
from game.settings import INVENTORY_SLOTS, HOTBAR_SLOTS


@dataclass
class Slot:
    item_id: Optional[str] = None
    quantity: int = 0

    @property
    def is_empty(self) -> bool:
        return self.item_id is None or self.quantity <= 0


class Inventory:
    def __init__(self, size: int = INVENTORY_SLOTS):
        self.slots: List[Slot] = [Slot() for _ in range(size)]
        self.selected_hotbar_index = 0

    def select_hotbar(self, index: int) -> None:
        if 0 <= index < HOTBAR_SLOTS:
            self.selected_hotbar_index = index

    def get_selected_item(self) -> Optional[Slot]:
        slot = self.slots[self.selected_hotbar_index]
        return None if slot.is_empty else slot

    def add_item(self, item_id: str, quantity: int) -> int:
        """Adds up to `quantity` of item_id. Returns leftover that didn't fit."""
        item_def = item_registry.get(item_id)
        remaining = quantity

        for slot in self.slots:
            if remaining <= 0:
                break
            if slot.item_id == item_id and slot.quantity < item_def.max_stack:
                space = item_def.max_stack - slot.quantity
                added = min(space, remaining)
                slot.quantity += added
                remaining -= added

        for slot in self.slots:
            if remaining <= 0:
                break
            if slot.is_empty:
                added = min(item_def.max_stack, remaining)
                slot.item_id = item_id
                slot.quantity = added
                remaining -= added

        return remaining

    def remove_item(self, item_id: str, quantity: int) -> int:
        """Removes up to `quantity` of item_id. Returns how much was actually removed."""
        remaining = quantity
        for slot in self.slots:
            if remaining <= 0:
                break
            if slot.item_id == item_id:
                removed = min(slot.quantity, remaining)
                slot.quantity -= removed
                remaining -= removed
                if slot.quantity <= 0:
                    slot.item_id = None
                    slot.quantity = 0
        return quantity - remaining

    def count_item(self, item_id: str) -> int:
        return sum(slot.quantity for slot in self.slots if slot.item_id == item_id)

    def remove_from_selected(self, quantity: int = 1) -> int:
        slot = self.slots[self.selected_hotbar_index]
        if slot.is_empty:
            return 0
        return self.remove_item(slot.item_id, quantity)
