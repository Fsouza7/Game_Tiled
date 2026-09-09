"""Shop buy/sell transactions. No UI code -- renderer/input call these.

Currency is the `coin` item. Selling grants `ItemDef.value` coins per
item (one from the clicked stack, or the whole stack if coins have
nowhere to go); buying costs `ShopOffer.price`. Offers are priced
above value so buying then selling can't print money. Infinite
stock: shops don't deplete (placing more of the same NPC isn't a thing,
and a finite stock would need a restock-timer we don't have).
"""
from typing import List, Optional, Tuple

from game.crafting import crafting_system
from game.crafting.recipe import RecipeDef
from game.inventory.inventory import Inventory
from game.items import item_registry
from game.npcs.npc_def import ShopOffer

COIN_ITEM_ID = "coin"


def wealth(inventory: Inventory) -> int:
    """Sum of item.value * quantity across the bag -- not equipment.
    Drives the Merchant's spawn condition (see npc_spawner.condition_met)."""
    total = 0
    for slot in inventory.slots:
        if slot.is_empty:
            continue
        total += item_registry.get(slot.item_id).value * slot.quantity
    return total


def buy(player, offer: ShopOffer) -> Tuple[bool, List[RecipeDef]]:
    """Spends `offer.price` coins and grants one of `offer.item_id`.
    Refunds the coins (and grants nothing) if the item can't fit -- same
    all-or-nothing rule as crafting_system.craft. On success, the bought
    item is marked discovered and any newly-unlocked recipes are returned
    for the caller to toast.
    """
    if player.inventory.count_item(COIN_ITEM_ID) < offer.price:
        return False, []

    player.inventory.remove_item(COIN_ITEM_ID, offer.price)
    leftover = player.inventory.add_item(offer.item_id, 1)
    if leftover > 0:
        player.inventory.remove_item(offer.item_id, 1 - leftover)
        player.inventory.add_item(COIN_ITEM_ID, offer.price)
        return False, []

    return True, crafting_system.mark_discovered(player, offer.item_id)


def _coin_space(inventory: Inventory) -> int:
    """How many coins still fit (existing stacks + empty slots)."""
    coin_def = item_registry.get(COIN_ITEM_ID)
    space = 0
    for slot in inventory.slots:
        if slot.is_empty:
            space += coin_def.max_stack
        elif slot.item_id == COIN_ITEM_ID:
            space += coin_def.max_stack - slot.quantity
    return space


def sell(player, bag_index: int) -> bool:
    """Sells from inventory.slots[bag_index] for ItemDef.value coins each.

    Normally one item. If the bag is full and there's no coin stack with
    room, selling one wouldn't free a slot for the payment -- so the rest
    of that clicked stack is sold too, and the coins occupy the freed slot.
    Always takes from the clicked slot (not the first matching stack).
    Refuses coins themselves and empty/zero-value slots.
    """
    if bag_index < 0 or bag_index >= len(player.inventory.slots):
        return False
    slot = player.inventory.slots[bag_index]
    if slot.is_empty:
        return False
    item_id = slot.item_id
    if item_id == COIN_ITEM_ID:
        return False
    item_def = item_registry.get(item_id)
    if item_def.value <= 0:
        return False

    coin_max = item_registry.get(COIN_ITEM_ID).max_stack
    space = _coin_space(player.inventory)
    qty_available = slot.quantity
    space_if_this_slot_empties = space + coin_max
    can_pay_one = (
        item_def.value <= space
        or (qty_available == 1 and item_def.value <= space_if_this_slot_empties)
    )
    if can_pay_one:
        qty_to_sell = 1
        coins_due = item_def.value
    else:
        qty_to_sell = qty_available
        coins_due = item_def.value * qty_to_sell
        if coins_due > space_if_this_slot_empties:
            return False

    slot.quantity -= qty_to_sell
    if slot.quantity <= 0:
        slot.item_id = None
        slot.quantity = 0

    leftover = player.inventory.add_item(COIN_ITEM_ID, coins_due)
    if leftover > 0:
        player.inventory.remove_item(COIN_ITEM_ID, coins_due - leftover)
        player.inventory.add_item(item_id, qty_to_sell)
        return False
    player.discovered_item_ids.add(COIN_ITEM_ID)
    return True


def buy_fail_reason(player, offer: ShopOffer) -> Optional[str]:
    """Why buy() would fail right now, or None if it should succeed.
    Used for the blocked-action toast (mirrors Player.blocked_mining_reason)."""
    if player.inventory.count_item(COIN_ITEM_ID) < offer.price:
        return "Not enough coins"
    return None  # remaining failure mode is inventory-full, which buy() itself detects
