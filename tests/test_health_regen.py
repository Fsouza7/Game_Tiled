"""Headless tests for passive health regeneration: rate, the post-damage
delay, the max-health cap, and interaction with respawn.
"""
import pygame  # noqa: F401

from game.settings import (
    DEFAULT_SEED, WORLD_WIDTH_TILES, TILE_SIZE,
    PLAYER_REGEN_RATE_HP_PER_S, PLAYER_REGEN_DELAY_AFTER_DAMAGE_S,
)
from game.entities.player import Player
from game.world.world import World


def _make_player():
    world = World(DEFAULT_SEED)
    x = WORLD_WIDTH_TILES // 2
    surface_y = world.surface_spawn_y(x) + 1
    player = Player(x * TILE_SIZE, (surface_y - 1) * TILE_SIZE)
    return world, player


def test_regen_heals_over_time_once_delay_clears():
    world, player = _make_player()
    player.health = player.max_health - 20
    player.regen_delay_remaining = 0.0

    for _ in range(60):  # 1 second at 1/60 dt
        player._regen_step(1 / 60)

    expected_gain = PLAYER_REGEN_RATE_HP_PER_S * 1.0
    assert abs(player.health - (player.max_health - 20 + expected_gain)) < 0.01


def test_regen_never_exceeds_max_health():
    world, player = _make_player()
    player.health = player.max_health - 1
    player.regen_delay_remaining = 0.0

    for _ in range(600):  # 10 seconds -- way more than enough to overshoot
        player._regen_step(1 / 60)

    assert player.health == player.max_health


def test_regen_is_paused_immediately_after_taking_damage():
    world, player = _make_player()
    player.health = player.max_health - 30
    player.regen_delay_remaining = 0.0
    player.take_damage(5.0)

    assert player.regen_delay_remaining == PLAYER_REGEN_DELAY_AFTER_DAMAGE_S
    assert player.is_regenerating() is False

    health_before = player.health
    player._regen_step(1 / 60)
    assert player.health == health_before  # no healing while delayed


def test_regen_resumes_once_the_delay_expires():
    world, player = _make_player()
    player.health = player.max_health - 30
    player.take_damage(5.0)  # starts the delay

    # Advance almost the whole delay -- still shouldn't regen.
    for _ in range(int((PLAYER_REGEN_DELAY_AFTER_DAMAGE_S - 0.1) * 60)):
        player._regen_step(1 / 60)
    assert player.is_regenerating() is False
    stalled_health = player.health

    # Cross the threshold -- regen should now be active.
    for _ in range(30):
        player._regen_step(1 / 60)
    assert player.health > stalled_health


def test_taking_damage_mid_regen_resets_the_delay():
    world, player = _make_player()
    player.health = player.max_health - 30
    player.regen_delay_remaining = 0.0
    player._regen_step(1 / 60)
    assert player.is_regenerating() is True

    player.take_damage(5.0)
    assert player.regen_delay_remaining == PLAYER_REGEN_DELAY_AFTER_DAMAGE_S
    assert player.is_regenerating() is False


def test_is_regenerating_false_at_full_health_even_without_delay():
    world, player = _make_player()
    player.regen_delay_remaining = 0.0
    assert player.health == player.max_health
    assert player.is_regenerating() is False


def test_respawn_clears_regen_delay():
    world, player = _make_player()
    player.take_damage(player.max_health + 50)  # kills and respawns
    assert player.regen_delay_remaining == 0.0
    assert player.health == player.max_health
