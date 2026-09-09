"""Headless tests for the asset-driven pass that put unused art to work:
fruit consumables + a real "eat" action, a Berry Bush obtain path, and a
placeable interactive tile (Trampoline bounce). Spikes started out
player-placeable here too, but was later redesigned into a world-generated
environmental hazard (see world_generator._place_cave_hazard) -- its damage
hook is still covered below, just no longer via a craftable recipe.
"""
import pygame  # noqa: F401

from game.settings import (
    DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE,
    SPIKES_CONTACT_DAMAGE, TRAMPOLINE_BOUNCE_VELOCITY, PLAYER_HIT_INVULNERABILITY_S,
)
from game.entities.player import Player
from game.world.world import World
from game.world.world_generator import biome_at
from game.world.biome_registry import DESERT_ID
from game.world.tile_registry import BUSH_ID, SPIKES_ID, TRAMPOLINE_ID, AIR_ID
from game.items import item_registry
from game.crafting import recipe_registry
from game.combat import combat_system

_FRUIT_IDS = ("apple", "banana", "cherries", "kiwi", "melon", "orange", "pineapple", "strawberry")


def _make_player(world=None):
    world = world or World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    return world, player


# --- Eating ---

def test_eating_selected_food_heals_and_consumes_it():
    world, player = _make_player()
    player.health = 50.0
    player.inventory.slots[0].item_id = "apple"
    player.inventory.slots[0].quantity = 2
    player.inventory.select_hotbar(0)

    ate = player.eat_selected()

    assert ate is True
    assert player.health == 50.0 + item_registry.get("apple").heal_amount
    assert player.inventory.slots[0].quantity == 1


def test_eating_caps_at_max_health():
    world, player = _make_player()
    player.health = player.max_health - 5
    player.inventory.slots[0].item_id = "melon"  # heals 25, more than the deficit
    player.inventory.slots[0].quantity = 1
    player.inventory.select_hotbar(0)

    assert player.eat_selected() is True
    assert player.health == player.max_health
    assert player.inventory.slots[0].quantity == 0


def test_eating_at_full_health_does_nothing():
    world, player = _make_player()
    assert player.health == player.max_health
    player.inventory.slots[0].item_id = "apple"
    player.inventory.slots[0].quantity = 1
    player.inventory.select_hotbar(0)

    assert player.eat_selected() is False
    assert player.inventory.slots[0].quantity == 1  # not consumed


def test_eating_a_non_food_item_does_nothing():
    world, player = _make_player()
    player.health = 50.0
    player.inventory.slots[0].item_id = "arrow"  # CONSUMABLE, but heal_amount == 0
    player.inventory.slots[0].quantity = 5
    player.inventory.select_hotbar(0)

    assert player.eat_selected() is False
    assert player.health == 50.0
    assert player.inventory.slots[0].quantity == 5


def test_all_fruits_are_edible_and_have_real_icons():
    for item_id in _FRUIT_IDS:
        item_def = item_registry.get(item_id)
        assert item_def.heal_amount > 0.0
        assert item_def.icon_key == item_id


# --- Berry bush obtain path ---

def test_bush_spawns_somewhere_outside_the_desert():
    world = World(DEFAULT_SEED)
    for x in range(0, WORLD_WIDTH_TILES, 2):
        if biome_at(DEFAULT_SEED, x).id == DESERT_ID:
            continue
        surface_y = world.surface_spawn_y(x) + 1
        if world.get_tile(x, surface_y - 1) == BUSH_ID:
            return
    raise AssertionError("no berry bush spawned anywhere -- check BUSH_SPAWN_CHANCE/seed")


def test_desert_never_spawns_a_bush():
    world = World(DEFAULT_SEED)
    for x in range(0, WORLD_WIDTH_TILES, 2):
        if biome_at(DEFAULT_SEED, x).id != DESERT_ID:
            continue
        surface_y = world.surface_spawn_y(x) + 1
        assert world.get_tile(x, surface_y - 1) != BUSH_ID


def test_mining_a_bush_drops_one_of_the_fruits():
    world = World(DEFAULT_SEED)
    bush_x = bush_y = None
    for x in range(0, WORLD_WIDTH_TILES, 2):
        if biome_at(DEFAULT_SEED, x).id == DESERT_ID:
            continue
        surface_y = world.surface_spawn_y(x) + 1
        if world.get_tile(x, surface_y - 1) == BUSH_ID:
            bush_x, bush_y = x, surface_y - 1
            break
    assert bush_x is not None, "no bush found to test mining"

    _, player = _make_player(world)
    player.x, player.y = bush_x * TILE_SIZE, bush_y * TILE_SIZE
    drop = None
    for _ in range(50):
        drop = player.try_mine(world, bush_x, bush_y, dt=0.1)
        if drop is not None:
            break
    assert drop in _FRUIT_IDS
    assert world.get_tile(bush_x, bush_y) == AIR_ID


# --- Spikes: environmental hazard (world-generated, not craftable) ---

def test_standing_on_spikes_damages_the_player():
    world, player = _make_player()
    tile_x = int(player.center_x // TILE_SIZE)
    tile_y = int(player.center_y // TILE_SIZE)
    # Set the tile directly rather than through try_place_tile -- placement
    # adjacency rules are already covered elsewhere; this test only cares
    # about the damage hook once a Spikes tile exists under the player.
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % 32, tile_y, SPIKES_ID)

    health_before = player.health
    combat_system.resolve_hazard_damage(player, world)

    assert player.health == health_before - SPIKES_CONTACT_DAMAGE
    assert player.is_invulnerable()


def test_spikes_respect_invulnerability_no_double_hit():
    world, player = _make_player()
    tile_x = int(player.center_x // TILE_SIZE)
    tile_y = int(player.center_y // TILE_SIZE)
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % 32, tile_y, SPIKES_ID)

    combat_system.resolve_hazard_damage(player, world)
    health_after_first_hit = player.health
    combat_system.resolve_hazard_damage(player, world)  # still invulnerable
    assert player.health == health_after_first_hit


# --- Trampoline: placeable bounce ---

def test_trampoline_recipe_and_item_are_registered():
    assert item_registry.get("trampoline").places_tile_id == TRAMPOLINE_ID
    recipe = recipe_registry.get("trampoline")
    assert recipe.result_item_id == "trampoline"


def test_landing_on_a_trampoline_bounces_instead_of_resting():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1  # first solid ground row

    # Place a trampoline one tile above the ground and drop the player onto it.
    tramp_y = surface_y - 1
    chunk = world.get_or_create_chunk(world.chunk_index_for(x))
    chunk.set_tile(x % 32, tramp_y, TRAMPOLINE_ID)

    player = Player(x * TILE_SIZE, (tramp_y - 3) * TILE_SIZE)
    player.y_vel = 5.0  # falling

    for _ in range(30):
        player.physics_step(world, dt=1 / 60)
        if player.y_vel < 0:
            break

    assert player.y_vel == -TRAMPOLINE_BOUNCE_VELOCITY
    assert player.on_ground is False
