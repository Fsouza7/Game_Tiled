"""Headless tests for the second deferred-assets pass: playable character
select, a real pause menu, Checkpoints, and the remaining traps (Fan,
Sand/Mud/Ice, Falling Platform, Saw, Rock Head, Spike Head).
"""
import os

import pygame  # noqa: F401
import pytest

from game.settings import (
    DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE, CHUNK_WIDTH,
    PLAYER_MOVE_SPEED, FAN_UPDRAFT_VELOCITY,
    TRAP_MUD_SPEED_MULTIPLIER, TRAP_ICE_SPEED_MULTIPLIER,
    FALLING_PLATFORM_TRIGGER_S, FALLING_PLATFORM_RESPAWN_S,
    PARTICLE_DUST_LIFETIME_S,
)
from game.entities.player import Player
from game.entities import character_registry
from game.world.world import World
from game.world import checkpoints, hazard_feature
from game.world.world_generator import generate_hazard_anchor
from game.world.tile_registry import (
    AIR_ID, FAN_ID, TRAP_MUD_ID, TRAP_ICE_ID, CRUMBLE_PLATFORM_ID, CHECKPOINT_ID,
)
from game.items import item_registry
from game.crafting import recipe_registry
from game.combat import combat_system
from game.rendering.particles import ParticleSystem, DUST, CONFETTI


def _make_player(world=None):
    world = world or World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    return world, player


def _feet_tile(player):
    return int(player.center_x // TILE_SIZE), int((player.y + player.height) // TILE_SIZE)


# --- Character select ---

def test_every_character_has_a_real_asset_dir_with_all_animation_files():
    for character in character_registry.all_characters():
        assert os.path.isdir(character.asset_dir), character.asset_dir
        for filename in ("idle.png", "run.png", "jump.png", "fall.png"):
            assert os.path.isfile(os.path.join(character.asset_dir, filename))


def test_default_character_is_registered():
    default = character_registry.get(character_registry.DEFAULT_CHARACTER_ID)
    assert default.id == character_registry.DEFAULT_CHARACTER_ID


def test_player_defaults_to_the_default_character_and_accepts_another():
    _, player = _make_player()
    assert player.character_id == character_registry.DEFAULT_CHARACTER_ID

    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    other = character_registry.all_characters()[1].id
    player2 = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE, other)
    assert player2.character_id == other


# --- Fan (updraft) ---

def test_fan_pushes_the_player_upward_within_range():
    world, player = _make_player()
    tile_x, tile_y = _feet_tile(player)
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, FAN_ID)

    player.physics_step(world, dt=1 / 60)

    assert player.y_vel == pytest.approx(-FAN_UPDRAFT_VELOCITY)


def test_fan_has_no_effect_out_of_range():
    world, player = _make_player()
    tile_x, tile_y = _feet_tile(player)
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, FAN_ID)
    player.y = player.y - 20 * TILE_SIZE  # far above the fan

    player.physics_step(world, dt=1 / 60)

    assert player.y_vel > 0  # just falling under gravity, no updraft reached it


# --- Sand/Mud/Ice speed modifiers ---

def _settle_onto_ground(player, world) -> None:
    """`_make_player` spawns the player slightly embedded in the ground row
    (PLAYER_HEIGHT_TILES doesn't evenly divide a tile) -- one physics_step
    resolves that into a proper rest with on_ground actually True, the same
    way it would after falling in a real game. Needed before measuring
    horizontal movement, since a still-embedded rect can spuriously read as
    a horizontal collision on the very first step."""
    player.physics_step(world, dt=1 / 60)
    assert player.on_ground is True


def test_mud_slows_horizontal_movement():
    world, player = _make_player()
    tile_x, tile_y = _feet_tile(player)
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, TRAP_MUD_ID)
    _settle_onto_ground(player, world)

    player.x_vel = PLAYER_MOVE_SPEED
    start_x = player.x
    player.physics_step(world, dt=1 / 60)

    assert (player.x - start_x) == pytest.approx(PLAYER_MOVE_SPEED * TRAP_MUD_SPEED_MULTIPLIER, abs=0.05)


def test_ice_speeds_up_horizontal_movement():
    world, player = _make_player()
    tile_x, tile_y = _feet_tile(player)
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, TRAP_ICE_ID)
    _settle_onto_ground(player, world)

    player.x_vel = PLAYER_MOVE_SPEED
    start_x = player.x
    player.physics_step(world, dt=1 / 60)

    assert (player.x - start_x) == pytest.approx(PLAYER_MOVE_SPEED * TRAP_ICE_SPEED_MULTIPLIER, abs=0.05)


def test_speed_multiplier_not_applied_while_airborne():
    world, player = _make_player()
    tile_x, tile_y = _feet_tile(player)
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, TRAP_MUD_ID)
    player.y -= 5 * TILE_SIZE  # well clear of the ground -- genuinely airborne
    player.on_ground = False
    player.x_vel = PLAYER_MOVE_SPEED
    start_x = player.x

    player.physics_step(world, dt=1 / 60)

    assert (player.x - start_x) == pytest.approx(PLAYER_MOVE_SPEED, abs=0.05)


# --- Falling Platform ---

def test_falling_platform_crumbles_after_continuous_standing_and_respawns():
    world, player = _make_player()
    tile_x, tile_y = _feet_tile(player)
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, CRUMBLE_PLATFORM_ID)

    steps = int(FALLING_PLATFORM_TRIGGER_S / (1 / 60)) + 3
    for _ in range(steps):
        world.notify_standing_on(tile_x, tile_y, dt=1 / 60)

    assert world.get_tile(tile_x, tile_y) == AIR_ID
    assert world.crumbling_tile_pos is None  # cleared once it actually crumbled

    world.update(FALLING_PLATFORM_RESPAWN_S + 0.1)
    assert world.get_tile(tile_x, tile_y) == CRUMBLE_PLATFORM_ID


def test_falling_platform_timer_resets_if_the_player_leaves():
    world, player = _make_player()
    tile_x, tile_y = _feet_tile(player)
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, CRUMBLE_PLATFORM_ID)

    half_steps = int(FALLING_PLATFORM_TRIGGER_S / (1 / 60) / 2)
    for _ in range(half_steps):
        world.notify_standing_on(tile_x, tile_y, dt=1 / 60)
    assert world.get_tile(tile_x, tile_y) == CRUMBLE_PLATFORM_ID  # not yet

    world.notify_standing_on(tile_x + 5, tile_y, dt=1 / 60)  # stepped onto a different tile

    for _ in range(half_steps + 2):
        world.notify_standing_on(tile_x, tile_y, dt=1 / 60)
    assert world.get_tile(tile_x, tile_y) == CRUMBLE_PLATFORM_ID  # timer had reset, still standing


# Falling Platform started out player-craftable here too, but was later
# redesigned into a world-generated environmental hazard (see
# world_generator._place_cave_hazard) -- it no longer has a recipe/item.

# --- Checkpoint ---

def test_checkpoint_recipe_and_item_are_registered():
    assert item_registry.get("checkpoint").places_tile_id == CHECKPOINT_ID
    assert recipe_registry.get("checkpoint").result_item_id == "checkpoint"


def _make_player_with_unrelated_spawn(world=None):
    """Like _make_player, but with spawn_x/spawn_y forced away from wherever
    a test places a Checkpoint tile (both are derived from the same world
    center column by default and would otherwise coincide, making
    activation a no-op for the wrong reason -- see try_activate's
    already-this-checkpoint short-circuit)."""
    world, player = _make_player(world)
    player.spawn_x, player.spawn_y = -9999.0, -9999.0
    return world, player


def test_touching_a_checkpoint_sets_it_as_the_new_spawn_point():
    world, player = _make_player_with_unrelated_spawn()
    tile_x = int(player.center_x // TILE_SIZE)
    tile_y = int(player.center_y // TILE_SIZE)
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, CHECKPOINT_ID)

    activated = checkpoints.try_activate(player, world)

    assert activated is True
    assert player.spawn_x == tile_x * TILE_SIZE
    assert player.spawn_y == tile_y * TILE_SIZE


def test_re_touching_the_same_active_checkpoint_does_not_re_activate():
    world, player = _make_player_with_unrelated_spawn()
    tile_x = int(player.center_x // TILE_SIZE)
    tile_y = int(player.center_y // TILE_SIZE)
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, CHECKPOINT_ID)

    assert checkpoints.try_activate(player, world) is True
    assert checkpoints.try_activate(player, world) is False  # already this checkpoint


def test_dying_after_a_checkpoint_respawns_there():
    world, player = _make_player_with_unrelated_spawn()
    tile_x = int(player.center_x // TILE_SIZE)
    tile_y = int(player.center_y // TILE_SIZE)
    chunk = world.get_or_create_chunk(world.chunk_index_for(tile_x))
    chunk.set_tile(tile_x % CHUNK_WIDTH, tile_y, CHECKPOINT_ID)
    assert checkpoints.try_activate(player, world) is True

    player.x, player.y = 0.0, 0.0  # wander off
    player.take_damage(player.max_health + 10)  # lethal

    assert player.x == tile_x * TILE_SIZE
    assert player.y == tile_y * TILE_SIZE


# --- Moving hazards (Saw, Rock Head, Spike Head) ---

def test_hazard_anchor_spawns_somewhere_in_a_wide_scan():
    found = [
        generate_hazard_anchor(DEFAULT_SEED, x)
        for x in range(0, WORLD_WIDTH_TILES, 3)
    ]
    found = [a for a in found if a is not None]
    assert len(found) > 0, "no hazard anchor spawned anywhere -- check HAZARD_SPAWN_CHANCE_PER_COLUMN/seed"
    assert all(a.kind in hazard_feature.ALL_KINDS for a in found)


def test_hazard_anchor_oscillates_around_its_anchor_point():
    anchor = hazard_feature.HazardAnchor(kind=hazard_feature.SAW, anchor_x=1000.0, anchor_y=2000.0, phase=0.0)
    center_at_0 = anchor.current_center(0.0)
    assert center_at_0 == pytest.approx((1000.0, 2000.0), abs=0.01)  # sin(0) == 0

    # a quarter period later it should be near its extreme, i.e. far from the anchor
    from game.settings import SAW_PERIOD_S, SAW_AMPLITUDE_TILES
    _, y_quarter = anchor.current_center(SAW_PERIOD_S / 4)
    assert abs(y_quarter - 2000.0) == pytest.approx(SAW_AMPLITUDE_TILES * TILE_SIZE, abs=0.5)


def test_hazard_feature_damages_and_knocks_back_the_player_on_overlap():
    world, player = _make_player()
    anchor = hazard_feature.HazardAnchor(
        kind=hazard_feature.SAW, anchor_x=player.center_x, anchor_y=player.center_y, phase=0.0,
    )
    chunk = world.get_or_create_chunk(world.chunk_index_for(int(player.center_x // TILE_SIZE)))
    chunk.hazards.append(anchor)

    health_before = player.health
    combat_system.resolve_hazard_feature_damage(player, world)

    assert player.health < health_before
    assert player.is_invulnerable()


def test_hazard_textures_cover_every_hazard_kind():
    # Regression test: SPIKED_BALL was added to hazard_feature.ALL_KINDS
    # (spawned in world gen, damages the player) without a matching entry
    # in assets.load_hazard_textures, so Renderer._draw_hazard_sprite
    # crashed with a KeyError the first time one was ever drawn.
    pygame.display.set_mode((1, 1))
    from game.rendering import assets
    textures = assets.load_hazard_textures(TILE_SIZE)
    for kind in hazard_feature.ALL_KINDS:
        assert kind in textures, f"no texture registered for hazard kind {kind!r}"
        assert len(textures[kind]) >= 1


def test_hazard_feature_respects_invulnerability_no_double_hit():
    world, player = _make_player()
    anchor = hazard_feature.HazardAnchor(
        kind=hazard_feature.ROCK_HEAD, anchor_x=player.center_x, anchor_y=player.center_y, phase=0.0,
    )
    chunk = world.get_or_create_chunk(world.chunk_index_for(int(player.center_x // TILE_SIZE)))
    chunk.hazards.append(anchor)

    combat_system.resolve_hazard_feature_damage(player, world)
    health_after_first_hit = player.health
    combat_system.resolve_hazard_feature_damage(player, world)  # still invulnerable
    assert player.health == health_after_first_hit


def test_world_only_iterates_hazards_from_loaded_chunks():
    world = World(DEFAULT_SEED)
    assert list(world.iter_hazard_anchors()) == []  # nothing loaded yet
    world.get_or_create_chunk(0)
    # whatever chunk 0 rolled (possibly nothing) is now reflected -- the
    # important property is it never scans unloaded chunks.
    assert set(world.chunks.keys()) == {0}


# --- Particles ---

def test_particles_expire_after_their_lifetime():
    system = ParticleSystem()
    system.spawn_dust(0.0, 0.0, count=2)
    assert len(system.particles) == 2
    assert all(p.kind == DUST for p in system.particles)

    system.update(PARTICLE_DUST_LIFETIME_S + 0.1)
    assert system.particles == []


def test_confetti_burst_spawns_the_requested_count():
    system = ParticleSystem()
    system.spawn_confetti(0.0, 0.0, count=10)
    assert len(system.particles) == 10
    assert all(p.kind == CONFETTI for p in system.particles)
    assert all(0 <= p.frame_index < 6 for p in system.particles)


def test_hit_spark_burst_spawns_the_requested_count_and_color():
    from game.rendering.particles import HIT_SPARK

    system = ParticleSystem()
    system.spawn_hit_spark(0.0, 0.0, color=(1, 2, 3), count=5)
    assert len(system.particles) == 5
    assert all(p.kind == HIT_SPARK for p in system.particles)
    assert all(p.color == (1, 2, 3) for p in system.particles)
    # A real radial burst, not every particle flying the same direction.
    directions = {(round(p.x_vel, 2), round(p.y_vel, 2)) for p in system.particles}
    assert len(directions) > 1


def test_hit_spark_ignores_gravity_unlike_dust_and_confetti():
    system = ParticleSystem()
    system.spawn_hit_spark(0.0, 0.0, color=(255, 255, 255), count=1)
    spark = system.particles[0]
    y_vel_before = spark.y_vel
    system.update(dt=0.05)
    assert system.particles[0].y_vel == y_vel_before  # no gravity accel applied


# Fan, Sand/Mud/Ice started out player-craftable here too, but were later
# redesigned into world-generated environmental features (see
# world_generator._place_fan_shaft / _surface_tile_for) -- none of them
# have a recipe/item anymore; see test_world_generator_second_pass_traps.py
# for coverage of the actual world-gen placement.
