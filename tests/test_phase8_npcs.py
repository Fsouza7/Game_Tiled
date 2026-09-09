"""Headless tests for Phase 8 NPCs: registry, spawn conditions, house
assignment, dialogue, shop buy/sell (including inventory-full refund),
and a full GameApp path through T-to-talk + the shop click.
"""
import pygame  # noqa: F401

from game.settings import (
    DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE,
    NPC_MERCHANT_MIN_WEALTH, NPC_WIDTH_TILES, NPC_HEIGHT_TILES,
)
from game.entities.player import Player
from game.world.world import World
from game.world.tile_registry import AIR_ID
from game.world import tile_registry
from game.items import item_registry
from game.npcs import npc_registry, shop as npc_shop
from game.npcs.npc import Npc
from game.npcs.npc_def import ShopOffer
from game.npcs.npc_spawner import (
    NpcSpawner, condition_met, homes_for_world, nearest_in_range, position_in_house,
    iter_houses_nearest_first,
)
from game.rendering.renderer import (
    npc_button_at_screen_pos, npc_button_rects,
    npc_shop_offer_at_screen_pos, npc_shop_offer_rect,
    npc_shop_bag_index_at_screen_pos, npc_shop_bag_slot_rect,
)
from game.input.input_handler import InputHandler
from game.core.notifications import NotificationQueue


def _make_world_and_player():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x)
    player = Player(x * TILE_SIZE, surface_y * TILE_SIZE)
    return world, player


# --- registry sanity ---

def test_npc_registry_has_the_three_roles():
    npcs = {n.id: n for n in npc_registry.all_npcs()}
    assert set(npcs) == {"guide", "merchant", "blacksmith"}
    assert npcs["guide"].shop_stock == ()
    assert npcs["guide"].spawn_condition == "always"
    assert npcs["merchant"].spawn_condition == "wealth"
    assert npcs["blacksmith"].spawn_condition == "discovered_item"
    assert npcs["blacksmith"].spawn_item_id == "iron_bar"
    assert npcs["guide"].dialogue
    assert npcs["merchant"].shop_stock
    assert npcs["blacksmith"].shop_stock


def test_shop_stock_references_real_items_priced_above_value():
    for npc in npc_registry.all_npcs():
        for offer in npc.shop_stock:
            item_def = item_registry.get(offer.item_id)
            assert offer.price > item_def.value, \
                f"{npc.id} sells {offer.item_id} at {offer.price} which isn't above value {item_def.value}"


def test_coin_item_is_registered():
    coin = item_registry.get("coin")
    assert coin.icon_key == "coin"
    assert coin.max_stack >= 99


# --- spawn conditions ---

def test_guide_always_qualifies_on_a_fresh_player():
    _, player = _make_world_and_player()
    assert condition_met(npc_registry.get("guide"), player)
    assert not condition_met(npc_registry.get("merchant"), player)
    assert not condition_met(npc_registry.get("blacksmith"), player)


def test_merchant_unlocks_at_wealth_threshold_not_from_starter_gear_alone():
    _, player = _make_world_and_player()
    assert npc_shop.wealth(player.inventory) < NPC_MERCHANT_MIN_WEALTH
    player.inventory.add_item("wood", 20)
    assert npc_shop.wealth(player.inventory) >= NPC_MERCHANT_MIN_WEALTH
    assert condition_met(npc_registry.get("merchant"), player)


def test_blacksmith_unlocks_when_iron_bar_is_discovered():
    _, player = _make_world_and_player()
    player.discovered_item_ids.add("iron_bar")
    assert condition_met(npc_registry.get("blacksmith"), player)
    # holding it without discovering doesn't count -- discovered_item_ids is the gate
    _, player2 = _make_world_and_player()
    player2.inventory.add_item("iron_bar", 1)  # add_item does not mark discovered
    assert "iron_bar" not in player2.discovered_item_ids
    assert not condition_met(npc_registry.get("blacksmith"), player2)


def test_spawner_adds_guide_immediately_and_others_when_conditions_met():
    world, player = _make_world_and_player()
    npcs = []
    spawner = NpcSpawner()
    newly = spawner.update(world, player, npcs)
    assert [n.npc_def.id for n in npcs] == ["guide"]
    assert newly == ["guide"]

    player.inventory.add_item("wood", 20)
    newly = spawner.update(world, player, npcs)
    assert "merchant" in {n.npc_def.id for n in npcs}
    assert newly == ["merchant"]

    player.discovered_item_ids.add("iron_bar")
    newly = spawner.update(world, player, npcs)
    assert {n.npc_def.id for n in npcs} == {"guide", "merchant", "blacksmith"}
    assert newly == ["blacksmith"]

    # Once present they stay even if wealth drops.
    player.inventory.remove_item("wood", 20)
    spawner.update(world, player, npcs)
    assert "merchant" in {n.npc_def.id for n in npcs}


def test_quiet_until_synced_suppresses_arrival_ids_but_still_spawns():
    world, player = _make_world_and_player()
    player.inventory.add_item("wood", 20)
    npcs = []
    spawner = NpcSpawner()
    spawner.quiet_until_synced = True
    newly = spawner.update(world, player, npcs)
    assert newly == []
    assert {n.npc_def.id for n in npcs} == {"guide", "merchant"}


def test_homes_put_npcs_standing_on_solid_floor_with_air_above():
    world, _ = _make_world_and_player()
    for x_px, y_px in homes_for_world(world):
        feet_x = x_px + (NPC_WIDTH_TILES * TILE_SIZE) / 2
        feet_y = y_px + NPC_HEIGHT_TILES * TILE_SIZE
        tile_x = int(feet_x // TILE_SIZE)
        floor_y = int(feet_y // TILE_SIZE)
        floor_def = tile_registry.get(world.get_tile(tile_x, floor_y))
        assert floor_def.solid, f"NPC feet at ({tile_x},{floor_y}) are not on solid ground"
        assert world.get_tile(tile_x, floor_y - 1) == AIR_ID


def test_house_home_is_inside_a_real_house_when_one_is_nearby():
    world, _ = _make_world_and_player()
    houses = iter_houses_nearest_first(world.seed)
    if not houses:
        return  # seed with no houses at all -- fallback path is covered above
    spawn_x = WORLD_WIDTH_TILES // 2
    nearest = houses[0]
    if abs(nearest.anchor_x - spawn_x) > 80:
        return  # Guide used a fallback; still a valid outcome
    expected = position_in_house(nearest)
    assert homes_for_world(world)[0] == expected


# --- dialogue / interact range ---

def test_dialogue_advances_and_wraps():
    npc = Npc(npc_registry.get("guide"), 0, 0)
    first = npc.current_line
    npc.advance_dialogue()
    assert npc.current_line != first or len(npc.npc_def.dialogue) == 1
    for _ in range(len(npc.npc_def.dialogue) - 1):
        npc.advance_dialogue()
    assert npc.current_line == first


def test_nearest_in_range_ignores_far_npcs():
    _, player = _make_world_and_player()
    close = Npc(npc_registry.get("guide"), player.x, player.y)
    far = Npc(npc_registry.get("merchant"), player.x + 80 * TILE_SIZE, player.y)
    assert nearest_in_range(player, [close, far]) is close
    assert nearest_in_range(player, [far]) is None


# --- shop transactions ---

def test_buy_spends_coins_and_grants_the_item():
    _, player = _make_world_and_player()
    player.collect_item("coin", 20)
    offer = ShopOffer(item_id="torch", price=8)
    success, newly = npc_shop.buy(player, offer)
    assert success
    assert player.inventory.count_item("coin") == 12
    assert player.inventory.count_item("torch") == 1
    assert "torch" in player.discovered_item_ids
    # torch is an ingredient of nothing that isn't already unlocked by
    # starting items, but the return type must still be a list
    assert isinstance(newly, list)


def test_buy_fails_without_enough_coins_and_does_not_grant_the_item():
    _, player = _make_world_and_player()
    player.collect_item("coin", 3)
    offer = ShopOffer(item_id="torch", price=8)
    success, _ = npc_shop.buy(player, offer)
    assert not success
    assert player.inventory.count_item("torch") == 0
    assert player.inventory.count_item("coin") == 3
    assert npc_shop.buy_fail_reason(player, offer) == "Not enough coins"


def test_buy_refunds_coins_when_inventory_is_full():
    _, player = _make_world_and_player()
    # Fill every slot with a unique non-stacking item so a torch can't fit.
    # Tools/weapons/armor are max_stack=1; wood_pickaxe already occupies slot 0.
    fillers = ["stone_pickaxe", "iron_pickaxe", "wood_sword", "wood_bow",
               "wood_helmet", "wood_armor", "summon_rod_wood", "summon_rod_iron",
               "grapple_hook"]
    # Remaining slots: fill with unstackable-against-torch stacks of distinct blocks.
    # Easier: dump max stacks of dirt into every empty slot.
    while any(s.is_empty for s in player.inventory.slots):
        leftover = player.inventory.add_item("dirt_block", 99)
        assert leftover == 0
    player.collect_item("coin", 20)
    # collect_item may have failed to add coins if full -- make a hole for coins only
    # by converting one dirt stack into coins via direct slot write.
    player.inventory.slots[-1].item_id = "coin"
    player.inventory.slots[-1].quantity = 20

    offer = ShopOffer(item_id="torch", price=8)
    success, _ = npc_shop.buy(player, offer)
    assert not success
    assert player.inventory.count_item("torch") == 0
    assert player.inventory.count_item("coin") == 20


def test_sell_grants_coins_equal_to_item_value_and_refuses_coins():
    _, player = _make_world_and_player()
    player.inventory.slots[2].item_id = "wood"
    player.inventory.slots[2].quantity = 5
    assert npc_shop.sell(player, 2)
    assert player.inventory.count_item("wood") == 4
    assert player.inventory.count_item("coin") == item_registry.get("wood").value
    assert "coin" in player.discovered_item_ids

    coin_index = next(i for i, s in enumerate(player.inventory.slots) if s.item_id == "coin")
    assert not npc_shop.sell(player, coin_index)
    assert player.inventory.count_item("coin") == item_registry.get("wood").value


def test_sell_empty_slot_is_a_noop():
    _, player = _make_world_and_player()
    empty = next(i for i, s in enumerate(player.inventory.slots) if s.is_empty)
    assert not npc_shop.sell(player, empty)


def test_sell_with_full_inventory_and_no_coins_dumps_the_clicked_stack():
    """The usual 'I walked up to the merchant stuffed' case: no empty
    slot, no coin pile, every slot is a stack. Selling one wouldn't free
    room for coins -- the clicked stack is sold so payment can land."""
    _, player = _make_world_and_player()
    while any(s.is_empty for s in player.inventory.slots):
        assert player.inventory.add_item("dirt_block", 99) == 0
    assert player.inventory.count_item("coin") == 0
    dirt_index = next(i for i, s in enumerate(player.inventory.slots) if s.item_id == "dirt_block")
    dirt_value = item_registry.get("dirt_block").value
    sold_qty = player.inventory.slots[dirt_index].quantity
    dirt_before = player.inventory.count_item("dirt_block")

    assert npc_shop.sell(player, dirt_index)
    assert player.inventory.count_item("dirt_block") == dirt_before - sold_qty
    assert player.inventory.count_item("coin") == dirt_value * sold_qty
    assert player.inventory.slots[dirt_index].item_id == "coin"


def test_sell_last_item_in_slot_with_full_inventory_grants_coins():
    _, player = _make_world_and_player()
    while any(s.is_empty for s in player.inventory.slots):
        assert player.inventory.add_item("dirt_block", 99) == 0
    pick_index = next(i for i, s in enumerate(player.inventory.slots) if s.item_id == "wood_pickaxe")
    pick_value = item_registry.get("wood_pickaxe").value
    assert npc_shop.sell(player, pick_index)
    assert player.inventory.count_item("wood_pickaxe") == 0
    assert player.inventory.count_item("coin") == pick_value


def test_sell_one_from_a_stack_when_coins_already_have_room():
    _, player = _make_world_and_player()
    player.inventory.slots[2].item_id = "wood"
    player.inventory.slots[2].quantity = 8
    player.collect_item("coin", 5)
    assert npc_shop.sell(player, 2)
    assert player.inventory.count_item("wood") == 7
    assert player.inventory.count_item("coin") == 5 + item_registry.get("wood").value


def test_sell_takes_from_the_clicked_slot_not_the_first_matching_stack():
    _, player = _make_world_and_player()
    player.inventory.slots[1].item_id = "wood"
    player.inventory.slots[1].quantity = 10
    player.inventory.slots[5].item_id = "wood"
    player.inventory.slots[5].quantity = 3
    assert npc_shop.sell(player, 5)
    assert player.inventory.slots[1].quantity == 10
    assert player.inventory.slots[5].quantity == 2


# --- input / UI hit-testing ---

class _FakeTalkGameApp:
    def __init__(self, player, npcs):
        self.player = player
        self.npcs = npcs
        self.paused = False
        self.inventory_open = False
        self.crafting_open = False
        self.skills_open = False
        self.talking_to = None
        self.npc_shop_open = False
        self.notifications = NotificationQueue()

    def close_npc_panel(self):
        self.talking_to = None
        self.npc_shop_open = False


def test_t_opens_and_closes_dialogue_with_a_nearby_npc():
    _, player = _make_world_and_player()
    npc = Npc(npc_registry.get("guide"), player.x, player.y)
    app = _FakeTalkGameApp(player, [npc])
    handler = InputHandler()
    handler._handle_talk(app)
    assert app.talking_to is npc
    handler._handle_talk(app)
    assert app.talking_to is None


def test_shop_button_opens_shop_and_offer_click_buys():
    _, player = _make_world_and_player()
    player.collect_item("coin", 20)
    npc = Npc(npc_registry.get("merchant"), player.x, player.y)
    app = _FakeTalkGameApp(player, [npc])
    app.talking_to = npc
    handler = InputHandler()

    shop_pos = npc_button_rects(npc.npc_def, False)["shop"].center
    handler._handle_npc_click(shop_pos, app)
    assert app.npc_shop_open is True

    offer_pos = npc_shop_offer_rect(0).center
    assert npc_shop_offer_at_screen_pos(offer_pos, npc.npc_def) == 0
    handler._handle_npc_click(offer_pos, app)
    assert player.inventory.count_item("torch") == 1


def test_shop_bag_click_sells_the_item():
    _, player = _make_world_and_player()
    player.inventory.slots[4].item_id = "wood"
    player.inventory.slots[4].quantity = 3
    npc = Npc(npc_registry.get("merchant"), player.x, player.y)
    app = _FakeTalkGameApp(player, [npc])
    app.talking_to = npc
    app.npc_shop_open = True
    handler = InputHandler()
    pos = npc_shop_bag_slot_rect(4).center
    assert npc_shop_bag_index_at_screen_pos(pos, len(player.inventory.slots)) == 4
    handler._handle_npc_click(pos, app)
    assert player.inventory.count_item("wood") == 2
    assert player.inventory.count_item("coin") == item_registry.get("wood").value


def test_npc_button_hit_testing_matches_shop_and_talk_modes():
    merchant = npc_registry.get("merchant")
    assert npc_button_at_screen_pos(npc_button_rects(merchant, False)["shop"].center, merchant, False) == "shop"
    assert npc_button_at_screen_pos(npc_button_rects(merchant, True)["talk"].center, merchant, True) == "talk"
    guide = npc_registry.get("guide")
    assert npc_button_at_screen_pos(npc_button_rects(guide, False)["next"].center, guide, False) == "next"


def _notification_texts(notifications):
    texts = []
    if notifications.current_text is not None:
        texts.append(notifications.current_text)
    texts.extend(n.text for n in notifications._queue)
    return texts


def test_game_app_spawns_guide_and_talking_works_end_to_end():
    from game.core.game_app import GameApp

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False
        for _ in range(5):
            app.step(dt=1 / 60)

        assert any(n.npc_def.id == "guide" for n in app.npcs)
        assert not any(n.npc_def.id == "merchant" for n in app.npcs)

        guide = next(n for n in app.npcs if n.npc_def.id == "guide")
        app.player.x = guide.x
        app.player.y = guide.y
        for _ in range(2):
            app.step(dt=1 / 60)

        app.input_handler._handle_talk(app)
        assert app.talking_to is guide

        app.player.inventory.add_item("wood", 20)
        for _ in range(2):
            app.step(dt=1 / 60)
        assert any(n.npc_def.id == "merchant" for n in app.npcs)
        assert "Merchant has arrived!" in _notification_texts(app.notifications)

        app.player.discovered_item_ids.add("iron_bar")
        for _ in range(2):
            app.step(dt=1 / 60)
        assert {n.npc_def.id for n in app.npcs} == {"guide", "merchant", "blacksmith"}
        assert "Blacksmith has arrived!" in _notification_texts(app.notifications)
    finally:
        pygame.quit()


def test_save_load_respawns_qualified_npcs_without_reannouncing(tmp_path, monkeypatch):
    from game.core.game_app import GameApp
    from game.core import save_system

    monkeypatch.setattr(save_system, "SAVE_FILE_PATH", str(tmp_path / "save.json"))

    app = GameApp(seed=DEFAULT_SEED)
    try:
        app.title_open = False
        app.character_select_open = False
        app.class_select_open = False

        app.player.inventory.add_item("wood", 20)
        app.player.discovered_item_ids.add("iron_bar")
        for _ in range(3):
            app.step(dt=1 / 60)
        assert {n.npc_def.id for n in app.npcs} == {"guide", "merchant", "blacksmith"}

        app.save_game()
        app.load_game()
        for _ in range(3):
            app.step(dt=1 / 60)
        assert {n.npc_def.id for n in app.npcs} == {"guide", "merchant", "blacksmith"}
        assert "Merchant has arrived!" not in _notification_texts(app.notifications)
        assert "Blacksmith has arrived!" not in _notification_texts(app.notifications)
    finally:
        pygame.quit()
