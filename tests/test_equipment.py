"""Headless tests for the RPG-style equipment system: equip/unequip
transactions, the defense stat, and its integration with combat damage.
"""
import pygame  # noqa: F401

from game.settings import DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE, MIN_DAMAGE_AFTER_DEFENSE
from game.entities.player import Player
from game.entities.enemy import Enemy
from game.entities import enemy_registry
from game.combat import combat_system
from game.crafting import recipe_registry
from game.items import item_registry
from game.world.world import World


def test_equip_moves_item_out_of_inventory():
    player = Player(0, 0)
    player.inventory.add_item("wood_helmet", 1)

    equipped = player.equipment.equip_from_inventory(player.inventory, "wood_helmet")
    assert equipped is True
    assert player.equipment.get("head") == "wood_helmet"
    assert player.inventory.count_item("wood_helmet") == 0


def test_equip_fails_without_owning_the_item():
    player = Player(0, 0)
    equipped = player.equipment.equip_from_inventory(player.inventory, "wood_helmet")
    assert equipped is False
    assert player.equipment.get("head") is None


def test_equip_fails_when_slot_already_occupied():
    player = Player(0, 0)
    player.inventory.add_item("wood_helmet", 2)
    assert player.equipment.equip_from_inventory(player.inventory, "wood_helmet") is True
    # Second helmet: slot is full, so it should stay in the inventory.
    assert player.equipment.equip_from_inventory(player.inventory, "wood_helmet") is False
    assert player.inventory.count_item("wood_helmet") == 1


def test_equip_rejects_non_armor_items():
    player = Player(0, 0)
    player.inventory.add_item("wood", 5)
    equipped = player.equipment.equip_from_inventory(player.inventory, "wood")
    assert equipped is False
    assert player.inventory.count_item("wood") == 5  # untouched


def test_unequip_returns_item_to_inventory():
    player = Player(0, 0)
    player.inventory.add_item("wood_helmet", 1)
    player.equipment.equip_from_inventory(player.inventory, "wood_helmet")

    unequipped = player.equipment.unequip_to_inventory(player.inventory, "head")
    assert unequipped is True
    assert player.equipment.get("head") is None
    assert player.inventory.count_item("wood_helmet") == 1


def test_unequip_fails_and_keeps_item_if_inventory_is_full():
    player = Player(0, 0)
    player.inventory.add_item("wood_helmet", 1)
    player.equipment.equip_from_inventory(player.inventory, "wood_helmet")

    for slot in player.inventory.slots:
        if slot.is_empty:
            slot.item_id = "stone_block"
            slot.quantity = 99

    unequipped = player.equipment.unequip_to_inventory(player.inventory, "head")
    assert unequipped is False
    assert player.equipment.get("head") == "wood_helmet"  # still equipped, not lost


def test_total_defense_sums_all_equipped_slots():
    player = Player(0, 0)
    player.inventory.add_item("wood_helmet", 1)
    player.inventory.add_item("wood_armor", 1)
    player.equipment.equip_from_inventory(player.inventory, "wood_helmet")
    player.equipment.equip_from_inventory(player.inventory, "wood_armor")

    expected = item_registry.get("wood_helmet").defense + item_registry.get("wood_armor").defense
    assert player.equipment.total_defense() == expected
    assert expected > 0


def test_contact_damage_is_reduced_by_equipped_defense():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    enemy = Enemy(enemy_registry.get("crawler"), x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)

    starting_hp = player.health
    combat_system.resolve_contact_damage(player, [enemy])
    unarmored_damage = starting_hp - player.health

    player2 = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    player2.inventory.add_item("wood_helmet", 1)
    player2.inventory.add_item("wood_armor", 1)
    player2.equipment.equip_from_inventory(player2.inventory, "wood_helmet")
    player2.equipment.equip_from_inventory(player2.inventory, "wood_armor")
    enemy2 = Enemy(enemy_registry.get("crawler"), x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    hp_before = player2.health
    combat_system.resolve_contact_damage(player2, [enemy2])
    armored_damage = hp_before - player2.health

    assert armored_damage < unarmored_damage
    assert armored_damage >= MIN_DAMAGE_AFTER_DEFENSE  # defense never reduces damage to zero


def test_armor_recipes_are_registered_and_reference_real_items():
    helmet_recipe = recipe_registry.get("wood_helmet")
    armor_recipe = recipe_registry.get("wood_armor")
    for recipe in (helmet_recipe, armor_recipe):
        item_registry.get(recipe.result_item_id)
        for item_id, qty in recipe.ingredients:
            item_registry.get(item_id)
            assert qty > 0


def test_armor_items_have_equip_slot_and_defense():
    helmet = item_registry.get("wood_helmet")
    armor = item_registry.get("wood_armor")
    assert helmet.equip_slot == "head"
    assert armor.equip_slot == "body"
    assert helmet.defense > 0
    assert armor.defense > 0


# --- inventory screen layout (click hit-testing must match what's drawn) ---

def test_equipment_and_bag_slot_rects_do_not_overlap():
    from game.rendering.renderer import equipment_slot_rect, inventory_bag_slot_rect
    from game.inventory.equipment import SLOTS

    equipment_rects = [equipment_slot_rect(slot) for slot in SLOTS]
    bag_rects = [inventory_bag_slot_rect(i) for i in range(20)]

    for eq_rect in equipment_rects:
        for bag_rect in bag_rects:
            assert not eq_rect.colliderect(bag_rect)

    for i, rect_a in enumerate(equipment_rects):
        for rect_b in equipment_rects[i + 1:]:
            assert not rect_a.colliderect(rect_b)
    for i, rect_a in enumerate(bag_rects):
        for rect_b in bag_rects[i + 1:]:
            assert not rect_a.colliderect(rect_b)


def test_equipment_slot_at_screen_pos_matches_rect():
    from game.rendering.renderer import equipment_slot_rect, equipment_slot_at_screen_pos
    for slot_name in ("head", "body"):
        rect = equipment_slot_rect(slot_name)
        assert equipment_slot_at_screen_pos(rect.center) == slot_name
    assert equipment_slot_at_screen_pos((0, 0)) is None


# --- inventory right-click quick actions ---

def _bag_slot_center(index: int):
    from game.rendering.renderer import inventory_bag_slot_rect
    return inventory_bag_slot_rect(index).center


class _FakeGameApp:
    """Just enough surface for InputHandler._handle_inventory_right_click,
    which only ever touches game_app.player."""
    def __init__(self, player):
        self.player = player


def test_right_click_armor_equips_it_instead_of_moving_to_hotbar():
    from game.input.input_handler import InputHandler

    player = Player(0, 0)
    player.inventory.slots[0].item_id = "wood_helmet"
    player.inventory.slots[0].quantity = 1
    player.inventory.select_hotbar(4)

    InputHandler()._handle_inventory_right_click(_bag_slot_center(0), _FakeGameApp(player))

    assert player.equipment.get("head") == "wood_helmet"
    assert player.inventory.slots[0].is_empty
    assert player.inventory.slots[4].is_empty  # hotbar target untouched by the equip path


def test_right_click_non_armor_sends_it_to_the_selected_hotbar_slot():
    from game.input.input_handler import InputHandler

    player = Player(0, 0)
    player.inventory.slots[3].item_id = "wood"
    player.inventory.slots[3].quantity = 6
    player.inventory.select_hotbar(1)

    InputHandler()._handle_inventory_right_click(_bag_slot_center(3), _FakeGameApp(player))

    assert player.inventory.slots[1].item_id == "wood"
    assert player.inventory.slots[1].quantity == 6
    assert player.inventory.slots[3].is_empty  # swapped out (slot 1 started empty)


def test_right_click_on_an_empty_slot_does_nothing():
    from game.input.input_handler import InputHandler

    player = Player(0, 0)  # slot 0 starts with the default wood_pickaxe -- use an empty one
    player.inventory.select_hotbar(2)
    before = [(s.item_id, s.quantity) for s in player.inventory.slots]

    InputHandler()._handle_inventory_right_click(_bag_slot_center(5), _FakeGameApp(player))

    after = [(s.item_id, s.quantity) for s in player.inventory.slots]
    assert before == after


# --- item tooltip ---

def test_hovered_inventory_item_reads_bag_slot():
    from game.rendering.renderer import Renderer

    player = Player(0, 0)
    player.inventory.slots[2].item_id = "wood"
    player.inventory.slots[2].quantity = 9

    item_id, quantity = Renderer.__new__(Renderer)._hovered_inventory_item(player, _bag_slot_center(2))
    assert item_id == "wood"
    assert quantity == 9


def test_hovered_inventory_item_reads_equipment_slot_with_no_quantity():
    from game.rendering.renderer import Renderer, equipment_slot_rect

    player = Player(0, 0)
    player.equipment.slots["head"] = "wood_helmet"

    item_id, quantity = Renderer.__new__(Renderer)._hovered_inventory_item(player, equipment_slot_rect("head").center)
    assert item_id == "wood_helmet"
    assert quantity is None


def test_hovered_inventory_item_is_none_when_nothing_is_hovered():
    from game.rendering.renderer import Renderer

    player = Player(0, 0)
    item_id, quantity = Renderer.__new__(Renderer)._hovered_inventory_item(player, (0, 0))
    assert item_id is None and quantity is None


def test_item_tooltip_stat_lines_vary_by_category():
    from game.rendering.renderer import Renderer

    renderer = Renderer.__new__(Renderer)
    pickaxe_lines = dict(renderer._item_tooltip_stat_lines(item_registry.get("wood_pickaxe")))
    assert any(k.startswith("Mining Power") for k in pickaxe_lines)

    helmet_lines = dict(renderer._item_tooltip_stat_lines(item_registry.get("wood_helmet")))
    assert any(k.startswith("Defense") for k in helmet_lines)
    assert any(k.startswith("Slot") for k in helmet_lines)

    apple_lines = dict(renderer._item_tooltip_stat_lines(item_registry.get("apple")))
    assert any(k.startswith("Heals") for k in apple_lines)


def test_draw_item_tooltip_does_not_crash_and_stays_on_screen():
    import pygame as pg
    from game.rendering.renderer import Renderer
    from game.settings import WINDOW_WIDTH, WINDOW_HEIGHT

    pg.init()
    pg.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    renderer = Renderer()
    window = pg.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    # Near the bottom-right corner, where a naive tooltip would overflow
    # the window if it weren't clamped.
    renderer._draw_item_tooltip(window, "wood_sword", 1, (WINDOW_WIDTH - 5, WINDOW_HEIGHT - 5))
